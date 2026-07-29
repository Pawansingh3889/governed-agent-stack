"""Render a verdict as one self-contained HTML file.

Constraints, in priority order:
  1. No network. No CDN, no webfont, no analytics, no external image.
     The file must render identically on an air-gapped box.
  2. One file. It gets copied around and emailed; it must not break.
  3. It never says "proceed". It states what changed and whose decision
     it is. The tool does not get a vote on whether you ship.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from .policy import Severity, Verdict, overall, summarise

_CSS = """
:root{color-scheme:light dark;
--bg:#fbfbfa;--fg:#1a1a19;--muted:#6b6b68;--line:#e3e3e0;--card:#fff;
--fail:#b3261e;--failbg:#fdeceb;--warn:#8a6100;--warnbg:#fdf4e3;
--ok:#1f6f43;--okbg:#eaf5ee;--code:#f4f4f2}
@media(prefers-color-scheme:dark){:root{
--bg:#16161a;--fg:#e8e8e6;--muted:#9a9a96;--line:#2c2c31;--card:#1d1d21;
--fail:#f2837c;--failbg:#3a1d1c;--warn:#e0b155;--warnbg:#382c14;
--ok:#7bc99b;--okbg:#14301f;--code:#232329}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:60rem;margin:0 auto}
h1{font-size:1.35rem;margin:0 0 .25rem}
h2{font-size:1rem;margin:2rem 0 .6rem;font-weight:600}
.sub{color:var(--muted);font-size:.85rem;margin:0 0 1.5rem}
.banner{border-radius:10px;padding:1rem 1.15rem;margin:0 0 1.5rem;
border:1px solid var(--line)}
.banner .verdict{font-size:1.5rem;font-weight:700;letter-spacing:.02em}
.banner.FAIL{background:var(--failbg);border-color:var(--fail)}
.banner.FAIL .verdict{color:var(--fail)}
.banner.WARN{background:var(--warnbg);border-color:var(--warn)}
.banner.WARN .verdict{color:var(--warn)}
.banner.CLEAN{background:var(--okbg);border-color:var(--ok)}
.banner.CLEAN .verdict{color:var(--ok)}
.meta{display:flex;flex-wrap:wrap;gap:1.25rem;font-size:.82rem;
color:var(--muted);margin:.6rem 0 0}
.meta b{color:var(--fg);font-weight:600}
table{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:.88rem}
th{text-align:left;font-weight:600;font-size:.72rem;letter-spacing:.06em;
text-transform:uppercase;color:var(--muted);padding:.6rem .8rem;
border-bottom:1px solid var(--line)}
td{padding:.6rem .8rem;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
font-size:.85em;background:var(--code);padding:.1rem .3rem;border-radius:4px}
.pill{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.05em;
padding:.15rem .45rem;border-radius:4px;text-transform:uppercase}
.pill.fail{background:var(--failbg);color:var(--fail)}
.pill.warn{background:var(--warnbg);color:var(--warn)}
.pill.ignore{background:var(--code);color:var(--muted)}
.watch{color:var(--fail);font-weight:700}
.before{color:var(--fail)}.after{color:var(--ok)}
.reason{color:var(--muted);font-size:.8rem}
.decide{margin-top:2.5rem;border:1px solid var(--line);border-left:3px solid var(--fg);
border-radius:8px;padding:1rem 1.15rem;background:var(--card)}
.decide h2{margin-top:0}
.decide ol{margin:.4rem 0 0;padding-left:1.2rem}
.decide li{margin:.35rem 0}
footer{margin-top:2.5rem;color:var(--muted);font-size:.76rem}
.empty{color:var(--muted);padding:1rem;text-align:center;background:var(--card);
border:1px solid var(--line);border-radius:10px}
"""

_DECISION = {
    "FAIL": [
        "Confirm whether each failing change is intentional. Ask the DBA; "
        "do not infer it.",
        "If it is intentional and safe: re-run the baseline capture, re-seal "
        "it, record the new digest out of band, and update the semantic layer "
        "or exporter to match.",
        "If it is not intentional: stop. Nothing downstream should run "
        "against this schema.",
        "Either way, this file is not the record. The record is the ledger "
        "entry and your signature.",
    ],
    "WARN": [
        "Read each warning and decide whether it affects the columns your "
        "export actually reads.",
        "If none do, proceed with the normal ritual.",
        "If any do, treat it as a failure and re-baseline.",
    ],
    "CLEAN": [
        "No change was observed against the sealed baseline.",
        "That is not the same as 'the data is correct'. It means the shape "
        "has not moved.",
        "Continue with the normal verification ritual: inspect the output, "
        "sign the log, transfer the CSV.",
    ],
}


def _row(v: Verdict) -> str:
    ch = v.change
    target = escape(ch.target)
    if v.watched:
        target = f'<span class="watch">{target}</span>'
    before = f'<span class="before">{escape(ch.before)}</span>' if ch.before else ""
    after = f'<span class="after">{escape(ch.after)}</span>' if ch.after else ""
    arrow = " &rarr; " if before and after else ""
    detail = escape(ch.detail) if ch.detail else ""
    return (
        "<tr>"
        f'<td><span class="pill {v.severity.value}">{v.severity.value}</span></td>'
        f"<td class='mono'>{target}</td>"
        f"<td><code>{escape(ch.kind)}</code></td>"
        f"<td class='mono'>{before}{arrow}{after}{(' ' + detail) if detail else ''}</td>"
        f'<td class="reason">{escape(v.reason)}</td>'
        "</tr>"
    )


def render(
    verdicts: list[Verdict],
    *,
    baseline_digest: str,
    baseline_path: str,
    live_path: str,
    generated_at: str,
    ledger_note: str = "",
) -> str:
    status = overall(verdicts)
    counts = summarise(verdicts)

    shown = [v for v in verdicts if v.severity is not Severity.IGNORE]
    order = {Severity.FAIL: 0, Severity.WARN: 1, Severity.IGNORE: 2}
    shown.sort(key=lambda v: (not v.watched, order[v.severity], v.change.target))

    if shown:
        body = (
            "<table><thead><tr><th></th><th>Target</th><th>Change</th>"
            "<th>Before / after</th><th>Why</th></tr></thead><tbody>"
            + "".join(_row(v) for v in shown)
            + "</tbody></table>"
        )
    else:
        body = '<p class="empty">No changes above the ignore threshold.</p>'

    ignored = counts[Severity.IGNORE.value]
    ignored_note = (
        f"<p class='sub' style='margin-top:.75rem'>{ignored} further "
        f"change{'s' if ignored != 1 else ''} matched an ignore rule or fell below "
        f"a threshold and {'are' if ignored != 1 else 'is'} not listed. "
        f"Ignore rules are in your policy file — read them if this number surprises you.</p>"
        if ignored
        else ""
    )

    steps = "".join(f"<li>{escape(s)}</li>" for s in _DECISION[status])

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>drift-gate — {status}</title>
<style>{_CSS}</style></head>
<body><main>

<h1>Schema drift report</h1>
<p class="sub">Generated {escape(generated_at)} &middot; no network access was
used to produce or render this file.</p>

<div class="banner {status}">
  <div class="verdict">{status}</div>
  <div class="meta">
    <span>baseline seal <b class="mono">{escape(baseline_digest[:16])}</b></span>
    <span>fail <b>{counts['fail']}</b></span>
    <span>warn <b>{counts['warn']}</b></span>
    <span>ignored <b>{counts['ignore']}</b></span>
  </div>
</div>

<h2>Changes</h2>
{body}
{ignored_note}

<div class="decide">
<h2>This is your decision, not the tool's</h2>
<ol>{steps}</ol>
</div>

<footer>
baseline: <span class="mono">{escape(baseline_path)}</span><br>
live: <span class="mono">{escape(live_path)}</span><br>
{escape(ledger_note)}<br>
drift-gate &middot; part of the Governed Agent Stack &middot; MIT
</footer>

</main></body></html>
"""


def write(path: str | Path, html: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p
