"""Seal a baseline directory and verify it later.

This replaces the manual `sha256sum ./scout_report/*.csv` step. Not
because the manual step is wrong — it is the right instinct — but because
a check you have to remember is a check you eventually skip, and because
the tool needs the seal in machine-readable form to stamp it onto the
export log.

Format is deliberately `sha256sum -c` compatible, so you can always
verify without this tool:

    cd baseline && sha256sum -c MANIFEST.sha256
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAME = "MANIFEST.sha256"
_HEADER = "# drift-gate baseline seal — verify with: sha256sum -c " + MANIFEST_NAME
_CHUNK = 1024 * 1024


class SealError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _sealable_files(root: Path) -> list[Path]:
    files = [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != MANIFEST_NAME and not p.name.startswith(".")
    ]
    return files


@dataclass
class Seal:
    root: Path
    entries: dict[str, str]

    @property
    def digest(self) -> str:
        """One hash standing for the whole baseline.

        This is the value stamped into the signed export log, so a CSV on a
        USB stick can be tied back to the exact schema snapshot it was
        produced against.
        """
        h = hashlib.sha256()
        for name in sorted(self.entries):
            h.update(name.encode("utf-8"))
            h.update(b"\0")
            h.update(self.entries[name].encode("ascii"))
            h.update(b"\n")
        return h.hexdigest()

    @property
    def short(self) -> str:
        return self.digest[:16]


def seal(root: str | Path) -> Seal:
    """Hash every file under `root` and write MANIFEST.sha256."""
    r = Path(root)
    if not r.is_dir():
        raise SealError(f"Baseline directory not found: {r}")
    files = _sealable_files(r)
    if not files:
        raise SealError(f"Nothing to seal in {r} — the directory is empty.")

    entries = {str(p.relative_to(r)): sha256_file(p) for p in files}

    lines = [_HEADER]
    lines += [f"{entries[name]}  {name}" for name in sorted(entries)]
    (r / MANIFEST_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return Seal(root=r, entries=entries)


def read_manifest(root: str | Path) -> Seal:
    r = Path(root)
    mf = r / MANIFEST_NAME
    if not mf.exists():
        raise SealError(
            f"No {MANIFEST_NAME} in {r}. This baseline has never been sealed — "
            f"run `drift-gate seal --baseline {r}` and record the digest somewhere "
            f"outside this directory."
        )
    entries: dict[str, str] = {}
    for line in mf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, name = line.partition("  ")
        if not name:
            raise SealError(f"Malformed manifest line in {mf}: {line!r}")
        entries[name] = digest
    if not entries:
        raise SealError(f"{mf} contains no entries.")
    return Seal(root=r, entries=entries)


@dataclass
class VerifyResult:
    ok: bool
    seal: Seal
    modified: list[str]
    missing: list[str]
    unlisted: list[str]

    def describe(self) -> str:
        if self.ok:
            return f"baseline seal intact ({len(self.seal.entries)} files, {self.seal.short})"
        bits = []
        if self.modified:
            bits.append(f"modified: {', '.join(self.modified)}")
        if self.missing:
            bits.append(f"missing: {', '.join(self.missing)}")
        if self.unlisted:
            bits.append(f"not in manifest: {', '.join(self.unlisted)}")
        return "; ".join(bits)


def verify(root: str | Path, expect_digest: str | None = None) -> VerifyResult:
    """Re-hash the baseline and compare against its manifest.

    `expect_digest` is the out-of-band check: the manifest lives next to the
    files it protects, so anyone who can rewrite the files can rewrite the
    manifest. Keeping the digest somewhere else — a signed note, a password
    manager, an env var — is what makes the seal mean anything.
    """
    r = Path(root)
    recorded = read_manifest(r)

    modified: list[str] = []
    missing: list[str] = []
    for name, expected in sorted(recorded.entries.items()):
        p = r / name
        if not p.exists():
            missing.append(name)
        elif sha256_file(p) != expected:
            modified.append(name)

    on_disk = {str(p.relative_to(r)) for p in _sealable_files(r)}
    unlisted = sorted(on_disk - set(recorded.entries))

    ok = not (modified or missing or unlisted)

    if ok and expect_digest and recorded.digest != expect_digest.strip().lower():
        ok = False
        modified.append(
            f"(manifest digest {recorded.short} does not match the expected "
            f"{expect_digest.strip()[:16]})"
        )

    return VerifyResult(ok=ok, seal=recorded, modified=modified,
                        missing=missing, unlisted=unlisted)
