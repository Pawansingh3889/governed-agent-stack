import json
import sys

import pytest
from typer.testing import CliRunner

from drift_gate.cli import app
from drift_gate.manifest import MANIFEST_NAME, SealError, read_manifest, seal, verify

runner = CliRunner()


@pytest.fixture
def baseline(tmp_path):
    d = tmp_path / "baseline"
    d.mkdir()
    (d / "catalog.json").write_text(json.dumps({
        "tables": {
            "dbo.ProductionRuns": {
                "row_count": 100,
                "primary_key": ["RunID"],
                "columns": [
                    {"name": "RunID", "type": "int", "is_nullable": "NO"},
                    {"name": "YieldKg", "type": "decimal(10,2)", "is_nullable": "NO"},
                ],
            }
        }
    }), encoding="utf-8")
    (d / "notes.txt").write_text("captured read-only", encoding="utf-8")
    return d


class TestSeal:
    def test_seal_then_verify_ok(self, baseline):
        s = seal(baseline)
        assert (baseline / MANIFEST_NAME).exists()
        assert len(s.entries) == 2
        assert verify(baseline).ok

    def test_manifest_is_sha256sum_compatible(self, baseline):
        seal(baseline)
        lines = (baseline / MANIFEST_NAME).read_text().splitlines()
        body = [x for x in lines if not x.startswith("#")]
        assert all(len(x.split("  ")[0]) == 64 for x in body)

    def test_digest_is_stable_and_order_independent(self, baseline):
        assert seal(baseline).digest == seal(baseline).digest

    def test_modified_file_breaks_the_seal(self, baseline):
        seal(baseline)
        (baseline / "notes.txt").write_text("tampered", encoding="utf-8")
        r = verify(baseline)
        assert not r.ok and "notes.txt" in r.modified

    def test_deleted_file_breaks_the_seal(self, baseline):
        seal(baseline)
        (baseline / "notes.txt").unlink()
        r = verify(baseline)
        assert not r.ok and "notes.txt" in r.missing

    def test_added_file_breaks_the_seal(self, baseline):
        seal(baseline)
        (baseline / "extra.json").write_text("{}", encoding="utf-8")
        r = verify(baseline)
        assert not r.ok and "extra.json" in r.unlisted

    def test_expected_digest_mismatch_fails_even_if_manifest_is_consistent(self, baseline):
        """The attack the manifest alone cannot stop: rewrite files AND manifest."""
        seal(baseline)
        original = read_manifest(baseline).digest
        (baseline / "notes.txt").write_text("rewritten", encoding="utf-8")
        seal(baseline)  # attacker re-seals
        assert verify(baseline).ok  # internally consistent...
        assert not verify(baseline, expect_digest=original).ok  # ...but not the one you trust

    def test_unsealed_baseline_is_an_error(self, baseline):
        with pytest.raises(SealError, match="never been sealed"):
            verify(baseline)

    def test_empty_directory_refuses_to_seal(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        with pytest.raises(SealError, match="empty"):
            seal(d)


class TestCli:
    def _policy(self, tmp_path, extra=""):
        p = tmp_path / "drift-policy.yml"
        p.write_text(
            "fail_on: [column_dropped, type_narrowed, type_family_changed]\n"
            "warn_on: [column_added, type_widened, nullable_added, "
            "nullable_removed, table_added, table_dropped, pk_changed, "
            "pii_added, type_changed_unknown, {row_count_shift: 40%}]\n" + extra,
            encoding="utf-8",
        )
        return p

    def _live(self, tmp_path, mutate=None):
        payload = json.loads((tmp_path / "baseline" / "catalog.json").read_text())
        if mutate:
            mutate(payload)
        p = tmp_path / "live.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_clean_run_exits_zero_and_is_quiet(self, baseline, tmp_path):
        seal(baseline)
        r = runner.invoke(app, ["check", "-b", str(baseline),
                                "-l", str(self._live(tmp_path)),
                                "-p", str(self._policy(tmp_path))])
        assert r.exit_code == 0
        assert r.stdout.strip() == ""

    def test_narrowing_exits_one(self, baseline, tmp_path):
        seal(baseline)

        def narrow(p):
            p["tables"]["dbo.ProductionRuns"]["columns"][1]["type"] = "int"

        r = runner.invoke(app, ["check", "-b", str(baseline),
                                "-l", str(self._live(tmp_path, narrow)),
                                "-p", str(self._policy(tmp_path)), "--json"])
        assert r.exit_code == 1
        assert json.loads(r.stdout)["status"] == "FAIL"

    def test_broken_seal_exits_two_not_one(self, baseline, tmp_path):
        """'I cannot tell you' must not look like 'nothing changed'."""
        seal(baseline)
        (baseline / "notes.txt").write_text("tampered", encoding="utf-8")
        r = runner.invoke(app, ["check", "-b", str(baseline),
                                "-l", str(self._live(tmp_path)),
                                "-p", str(self._policy(tmp_path))])
        assert r.exit_code == 2

    def test_unsealed_baseline_exits_two(self, baseline, tmp_path):
        r = runner.invoke(app, ["check", "-b", str(baseline),
                                "-l", str(self._live(tmp_path)),
                                "-p", str(self._policy(tmp_path))])
        assert r.exit_code == 2

    def test_watched_column_fails_on_a_widening(self, baseline, tmp_path):
        seal(baseline)
        pol = self._policy(tmp_path, "watch:\n  dbo.ProductionRuns: [YieldKg]\n")

        def widen(p):
            p["tables"]["dbo.ProductionRuns"]["columns"][1]["type"] = "decimal(12,2)"

        r = runner.invoke(app, ["check", "-b", str(baseline),
                                "-l", str(self._live(tmp_path, widen)),
                                "-p", str(pol), "--json"])
        assert r.exit_code == 1
        assert json.loads(r.stdout)["changes"][0]["watched"] is True

    def test_strict_turns_warnings_into_failures(self, baseline, tmp_path):
        seal(baseline)

        def widen(p):
            p["tables"]["dbo.ProductionRuns"]["columns"][1]["type"] = "decimal(12,2)"

        args = ["check", "-b", str(baseline), "-l", str(self._live(tmp_path, widen)),
                "-p", str(self._policy(tmp_path))]
        assert runner.invoke(app, args).exit_code == 0
        assert runner.invoke(app, [*args, "--strict"]).exit_code == 1

    def test_report_is_self_contained(self, baseline, tmp_path):
        seal(baseline)

        def narrow(p):
            p["tables"]["dbo.ProductionRuns"]["columns"][1]["type"] = "int"

        out = tmp_path / "drift.html"
        runner.invoke(app, ["check", "-b", str(baseline),
                            "-l", str(self._live(tmp_path, narrow)),
                            "-p", str(self._policy(tmp_path)), "--report", str(out)])
        html = out.read_text()
        assert "FAIL" in html
        for forbidden in ("http://", "https://", "//cdn", "<script"):
            assert forbidden not in html, f"report reached for {forbidden}"

    def test_audit_requested_but_unavailable_refuses_to_run(self, baseline, tmp_path,
                                                            monkeypatch):
        """The rule that makes optional auditing safe.

        Unavailability is simulated rather than inherited from the environment.
        This test used to pass only because agent-blackbox happened not to be
        installed, so it quietly became a no-op wherever it was — including any
        checkout that installs the whole stack together. Blocking the import
        makes the invariant hold regardless of what else is present.
        """
        seal(baseline)
        monkeypatch.setitem(sys.modules, "agent_blackbox", None)
        monkeypatch.setenv("DRIFT_GATE_AUDIT_DB", str(tmp_path / "audit.db"))
        r = runner.invoke(app, ["check", "-b", str(baseline),
                                "-l", str(self._live(tmp_path)),
                                "-p", str(self._policy(tmp_path))])
        assert r.exit_code == 2
        assert "AUDIT UNAVAILABLE" in r.stderr

    def test_explain_policy_lists_the_watch_list(self, tmp_path):
        pol = self._policy(tmp_path, "watch:\n  dbo.ProductionRuns: [YieldKg]\n")
        r = runner.invoke(app, ["explain-policy", "-p", str(pol)])
        assert r.exit_code == 0
        assert "YieldKg".lower() in r.stdout.lower()
