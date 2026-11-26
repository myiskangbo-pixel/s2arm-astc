#!/usr/bin/env python3
"""Summarize preserved tools/gate.sh per-step diagnostics after CI interruption."""
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: contrib_diag.py <step-log-dir> <markdown-output>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    output = Path(sys.argv[2])
    manifest = root / "steps.tsv"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.is_file():
        output.write_text("# Contributor self-check diagnostics\n\nNo preserved step manifest was produced.\n", encoding="utf-8")
        return 0

    rows = []
    for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t", 2)
        if len(fields) != 3 or fields[0] == "index":
            continue
        index, name, limit = fields
        prefix = root / index
        rc_file = Path(str(prefix) + ".rc")
        started = Path(str(prefix) + ".started")
        queued = Path(str(prefix) + ".tk")
        log_file = Path(str(prefix) + ".log")
        wait_file = Path(str(prefix) + ".wait")
        if rc_file.is_file():
            values = rc_file.read_text(encoding="utf-8", errors="replace").split()
            rc = values[0] if values else "?"
            seconds = values[1] if len(values) > 1 else "?"
            status = f"completed (rc={rc}, {seconds}s)"
        elif started.is_file():
            status = "running when interrupted"
        elif queued.is_file():
            status = "waiting for a gate token"
        else:
            status = "not started before interruption"
        wait = wait_file.read_text(encoding="utf-8", errors="replace").strip() if wait_file.is_file() else "-"
        rows.append((index, name, limit, status, wait, log_file))

    pending = [row for row in rows if not row[3].startswith("completed")]
    lines = [
        "# Contributor self-check diagnostics",
        "",
        f"- Steps in manifest: **{len(rows)}**",
        f"- Steps with exit codes: **{len(rows) - len(pending)}**",
        f"- Steps pending at interruption: **{len(pending)}**",
        "",
        "| # | Step | Limit | State | Token wait (s) |",
        "|---:|---|---:|---|---:|",
    ]
    for index, name, limit, status, wait, _ in rows:
        safe = name.replace("|", "\\|")
        lines.append(f"| {index} | {safe} | {limit}s | {status} | {wait} |")
    for index, name, limit, status, wait, log_file in pending:
        lines.extend(["", f"## Pending step {index}: {name}", "", f"State: {status}; declared limit: {limit}s; token wait: {wait}s", ""])
        if log_file.is_file():
            excerpt = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            lines.extend(["```text", *excerpt, "```"])
        else:
            lines.append("No step log was created.")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Contributor diagnostics: {len(rows) - len(pending)}/{len(rows)} completed; {len(pending)} pending")
    for index, name, _, status, _, _ in pending:
        print(f"PENDING {index}: {name} — {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
