import json

import pytest

from drift_gate.catalog import (
    COLUMN_DROPPED,
    NULLABLE_ADDED,
    PII_ADDED,
    PK_CHANGED,
    ROW_COUNT_SHIFT,
    TABLE_DROPPED,
    CatalogError,
    diff_catalogs,
    load_catalog,
)
from drift_gate.policy import Policy, PolicyError, Severity, overall
from drift_gate.types import TypeChange


def _catalog(tables):
    return {"tables": tables}


BASE = _catalog({
    "dbo.ProductionRuns": {
        "row_count": 1000,
        "primary_key": ["RunID"],
        "columns": [
            {"name": "RunID", "type": "int", "is_nullable": "NO"},
            {"name": "YieldKg", "type": "decimal(10,2)", "is_nullable": "NO"},
            {"name": "QCStatus", "type": "varchar(10)", "is_nullable": "NO"},
            {"name": "Operator", "type": "nvarchar(100)", "is_nullable": "YES"},
        ],
    },
    "dbo.staging_tmp": {
        "columns": [{"name": "junk", "type": "int"}],
    },
})


def write(tmp_path, name, payload):
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_load_rejects_empty_catalog(tmp_path):
    p = write(tmp_path, "empty.json", {"tables": {}})
    with pytest.raises(CatalogError, match="zero columns"):
        load_catalog(p)


def test_load_handles_list_form(tmp_path):
    p = write(tmp_path, "c.json", [
        {"schema": "dbo", "name": "T", "columns": [{"column_name": "a", "data_type": "int"}]}
    ])
    cat = load_catalog(p)
    assert ("dbo.t", "a") in cat.columns


def test_load_reads_readiness_score(tmp_path):
    payload = dict(BASE)
    payload["readiness_score"] = {"score": 34}
    cat = load_catalog(write(tmp_path, "c.json", payload))
    assert cat.readiness == 34


class TestDiff:
    def _diff(self, tmp_path, live):
        return diff_catalogs(
            load_catalog(write(tmp_path, "b.json", BASE)),
            load_catalog(write(tmp_path, "l.json", live)),
        )

    def test_no_change(self, tmp_path):
        assert self._diff(tmp_path, BASE) == []

    def test_type_narrowing_detected(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["columns"][1]["type"] = "int"
        kinds = {c.kind for c in self._diff(tmp_path, live)}
        assert TypeChange.FAMILY_CHANGED.value in kinds

    def test_column_dropped(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        del live["tables"]["dbo.ProductionRuns"]["columns"][1]
        changes = self._diff(tmp_path, live)
        assert any(c.kind == COLUMN_DROPPED and c.column == "YieldKg" for c in changes)

    def test_table_dropped(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        del live["tables"]["dbo.ProductionRuns"]
        assert any(c.kind == TABLE_DROPPED for c in self._diff(tmp_path, live))

    def test_nullable_added(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["columns"][2]["is_nullable"] = "YES"
        assert any(c.kind == NULLABLE_ADDED for c in self._diff(tmp_path, live))

    def test_pk_changed(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["primary_key"] = ["RunID", "QCStatus"]
        assert any(c.kind == PK_CHANGED for c in self._diff(tmp_path, live))

    def test_pii_newly_flagged(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["columns"][3]["is_pii"] = True
        assert any(c.kind == PII_ADDED for c in self._diff(tmp_path, live))

    def test_row_count_shift_carries_percentage(self, tmp_path):
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["row_count"] = 1500
        ch = [c for c in self._diff(tmp_path, live) if c.kind == ROW_COUNT_SHIFT]
        assert ch and ch[0].detail == "50.0%"


POLICY = {
    "fail_on": ["column_dropped", "type_narrowed", "type_family_changed"],
    "warn_on": ["column_added", "type_widened", {"row_count_shift": "40%"}],
    "ignore": {"tables": ["staging_*"], "columns": ["modifieddate"]},
    "watch": {"dbo.ProductionRuns": ["YieldKg", "QCStatus"]},
}


class TestPolicy:
    def test_rejects_contradictory_policy(self):
        with pytest.raises(PolicyError, match="both fail_on and warn_on"):
            Policy.from_dict({"fail_on": ["column_added"], "warn_on": ["column_added"]})

    def test_unclassified_kind_defaults_to_fail(self, tmp_path):
        pol = Policy.from_dict(POLICY)
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["primary_key"] = ["QCStatus"]
        changes = diff_catalogs(
            load_catalog(write(tmp_path, "b.json", BASE)),
            load_catalog(write(tmp_path, "l.json", live)),
        )
        v = [x for x in pol.evaluate(changes) if x.change.kind == PK_CHANGED][0]
        assert v.severity is Severity.FAIL
        assert "not classified" in v.reason

    def test_watch_list_overrides_warn(self, tmp_path):
        """A widening is normally a warning — but not on a watched column."""
        pol = Policy.from_dict(POLICY)
        live = json.loads(json.dumps(BASE))
        live["tables"]["dbo.ProductionRuns"]["columns"][1]["type"] = "decimal(12,2)"
        changes = diff_catalogs(
            load_catalog(write(tmp_path, "b.json", BASE)),
            load_catalog(write(tmp_path, "l.json", live)),
        )
        verdicts = pol.evaluate(changes)
        v = [x for x in verdicts if x.change.column == "YieldKg"][0]
        assert v.severity is Severity.FAIL
        assert v.watched
        assert overall(verdicts) == "FAIL"

    def test_watch_list_overrides_ignore(self):
        """An ignore wildcard must never silence a column you declared load-bearing."""
        pol = Policy.from_dict({
            "fail_on": ["column_dropped"],
            "ignore": {"columns": ["yieldkg"]},
            "watch": {"dbo.ProductionRuns": ["YieldKg"]},
        })
        from drift_gate.catalog import Change
        ch = Change(kind=COLUMN_DROPPED, table="dbo.ProductionRuns", column="YieldKg")
        v = pol.evaluate([ch])[0]
        assert v.severity is Severity.FAIL
        assert v.watched

    def test_ignored_table_is_dropped_from_verdict(self):
        from drift_gate.catalog import Change
        pol = Policy.from_dict(POLICY)
        ch = Change(kind=COLUMN_DROPPED, table="dbo.staging_tmp", column="junk")
        assert pol.evaluate([ch])[0].severity is Severity.IGNORE

    def test_row_count_below_threshold_is_ignored(self):
        from drift_gate.catalog import Change
        pol = Policy.from_dict(POLICY)
        ch = Change(kind=ROW_COUNT_SHIFT, table="dbo.ProductionRuns", detail="12.0%")
        assert pol.evaluate([ch])[0].severity is Severity.IGNORE

    def test_row_count_above_threshold_warns(self):
        from drift_gate.catalog import Change
        pol = Policy.from_dict(POLICY)
        ch = Change(kind=ROW_COUNT_SHIFT, table="dbo.ProductionRuns", detail="55.0%")
        assert pol.evaluate([ch])[0].severity is Severity.WARN

    def test_clean_when_nothing_moved(self, tmp_path):
        pol = Policy.from_dict(POLICY)
        changes = diff_catalogs(
            load_catalog(write(tmp_path, "b.json", BASE)),
            load_catalog(write(tmp_path, "l.json", BASE)),
        )
        assert overall(pol.evaluate(changes)) == "CLEAN"
