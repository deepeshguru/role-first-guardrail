#!/usr/bin/env python3
"""
Generate a Markdown metrics report from logs/audit.jsonl.

Adds:
- Robust parsing (skips malformed lines)
- Optional --last N rows
- Percentiles with interpolation
- Allow rate by role AND by intent
- Top deny reasons
- Role × Intent allow-rate matrix

Usage:
  python scripts/make_tables.py
  python scripts/make_tables.py --last 50
  python scripts/make_tables.py --audit logs/audit.jsonl --out reports/metrics.md
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List


def pctl(xs: List[float], q: float) -> float | None:
    """Percentile with linear interpolation; returns rounded to 2 decimals."""
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return round(xs[f], 2)
    v = xs[f] + (xs[c] - xs[f]) * (k - f)
    return round(v, 2)


def read_jsonl(path: Path, last: int = 0) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Audit log not found: {path}")
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if last > 0:
        lines = lines[-last:]
    rows: List[Dict[str, Any]] = []
    for l in lines:
        try:
            rows.append(json.loads(l))
        except Exception:
            # Skip malformed lines silently
            pass
    return rows


def get_role(r: Dict[str, Any]) -> str:
    # Try multiple locations to be resilient
    return (
        r.get("role")
        or r.get("user_role")
        or (r.get("context") or {}).get("role")
        or "?"
    )


def get_intent_label(r: Dict[str, Any]) -> str:
    it = r.get("intent")
    if isinstance(it, dict):
        return it.get("intent", "?")
    if isinstance(it, str):
        return it
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default="logs/audit.jsonl", help="Path to audit JSONL")
    ap.add_argument("--out", default="reports/metrics.md", help="Output markdown file")
    ap.add_argument("--last", type=int, default=0, help="Only include the last N rows")
    args = ap.parse_args()

    audit_path = Path(args.audit)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        rows = read_jsonl(audit_path, last=args.last)
    except FileNotFoundError as e:
        print(str(e))
        return

    n = len(rows)
    allow = sum(1 for r in rows if r.get("allowed") is True)
    deny = n - allow

    lat = [float(r.get("latency_ms", 0)) for r in rows if "latency_ms" in r]
    p50 = pctl(lat, 0.5)
    p95 = pctl(lat, 0.95)

    # Collect breakdowns
    by_role: Dict[str, Dict[str, int]] = defaultdict(lambda: {"n": 0, "allow": 0})
    by_intent: Dict[str, Dict[str, int]] = defaultdict(lambda: {"n": 0, "allow": 0})
    deny_reasons: Dict[str, int] = defaultdict(int)
    role_intent_counts: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"n": 0, "allow": 0})
    )

    policy_versions = set()

    for r in rows:
        role = get_role(r)
        intent = get_intent_label(r)
        is_allowed = bool(r.get("allowed"))
        by_role[role]["n"] += 1
        by_role[role]["allow"] += 1 if is_allowed else 0

        by_intent[intent]["n"] += 1
        by_intent[intent]["allow"] += 1 if is_allowed else 0

        role_intent_counts[role][intent]["n"] += 1
        role_intent_counts[role][intent]["allow"] += 1 if is_allowed else 0

        if not is_allowed:
            deny_reasons[r.get("reason", "unknown")] += 1

        pv = r.get("policy_version")
        if pv:
            policy_versions.add(str(pv))

    # Build Markdown
    md: List[str] = []
    md.append("# Guardrail Metrics\n")
    if args.last > 0:
        md.append(f"_Using the last **{args.last}** rows from `{args.audit}`._\n")
    md.append(f"- Total requests: **{n}**")
    md.append(f"- Allow: **{allow}**, Deny: **{deny}**")
    md.append(f"- Latency p50: **{p50} ms**, p95: **{p95} ms**")
    if policy_versions:
        md.append(f"- Policy version(s): `{', '.join(sorted(policy_versions))}`")
    md.append("")

    # Allow rate by role
    md.append("## Allow rate by role\n")
    md.append("| Role | Samples | Allow rate |")
    md.append("|---|---:|---:|")
    for role, d in sorted(by_role.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        rate = (d["allow"] / d["n"]) if d["n"] else 0.0
        md.append(f"| {role} | {d['n']} | {rate:.2f} |")
    md.append("")

    # Allow rate by intent
    md.append("## Allow rate by intent\n")
    md.append("| Intent | Samples | Allow rate |")
    md.append("|---|---:|---:|")
    for intent, d in sorted(by_intent.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        rate = (d["allow"] / d["n"]) if d["n"] else 0.0
        md.append(f"| {intent} | {d['n']} | {rate:.2f} |")
    md.append("")

    # Top deny reasons
    if deny_reasons:
        md.append("## Top deny reasons\n")
        md.append("| Reason | Count |")
        md.append("|---|---:|")
        for reason, cnt in sorted(deny_reasons.items(), key=lambda kv: -kv[1]):
            md.append(f"| {reason} | {cnt} |")
        md.append("")

    # Role × Intent matrix
    intents_sorted = sorted(by_intent.keys())
    md.append("## Role × Intent (allow rate)\n")
    header = "| Role | " + " | ".join(intents_sorted) + " |"
    sep = "|---|" + "|".join(["---" for _ in intents_sorted]) + "|"
    md.append(header)
    md.append(sep)
    for role in sorted(role_intent_counts.keys()):
        cells = []
        for intent in intents_sorted:
            c = role_intent_counts[role].get(intent, {"n": 0, "allow": 0})
            if c["n"] == 0:
                cells.append("—")
            else:
                cells.append(f"{(c['allow']/c['n']):.2f} ({c['allow']}/{c['n']})")
        md.append(f"| {role} | " + " | ".join(cells) + " |")
    md.append("")

    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
