#!/usr/bin/env python3
import json, sys
from pathlib import Path
from collections import defaultdict

LOG = Path("logs/audit.jsonl")


def pctile(xs, p: float):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load_rows(path: Path):
    if not path.exists():
        print(json.dumps({"error": f"not found: {path}"}))
        sys.exit(0)
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                # skip malformed lines
                pass
    return rows


def main():
    rows = load_rows(LOG)
    n = len(rows)
    lat = [float(r.get("latency_ms", 0)) for r in rows if "latency_ms" in r]
    ti = [float(r.get("t_intent_ms", 0)) for r in rows if "t_intent_ms" in r]
    tp = [float(r.get("t_policy_ms", 0)) for r in rows if "t_policy_ms" in r]

    unknown = sum(1 for r in rows if r.get("intent", {}).get("intent") == "unknown")
    allowed = sum(1 for r in rows if r.get("allowed") is True)
    deny = n - allowed

    role_counts = defaultdict(int)
    role_allow = defaultdict(int)
    intent_counts = defaultdict(int)
    deny_reasons = defaultdict(int)
    break_glass_uses = 0

    for r in rows:
        role = r.get("role", "?")
        role_counts[role] += 1
        if r.get("allowed"):
            role_allow[role] += 1
        intent = r.get("intent", {}).get("intent", "?")
        intent_counts[intent] += 1
        if not r.get("allowed"):
            deny_reasons[r.get("reason", "?")] += 1
        if intent == "admin_override" and r.get("allowed"):
            break_glass_uses += 1

    out = {
        "total": n,
        "allow": allowed,
        "deny": deny,
        "unknown_intent_rate": round(unknown / n, 4) if n else 0.0,
        "allow_rate": round(allowed / n, 4) if n else 0.0,
        "latency_ms": {"p50": pctile(lat, 0.5), "p95": pctile(lat, 0.95)},
        "t_intent_ms": {"p50": pctile(ti, 0.5), "p95": pctile(ti, 0.95)},
        "t_policy_ms": {"p50": pctile(tp, 0.5), "p95": pctile(tp, 0.95)},
        "by_role_allow_rate": {
            k: round(role_allow[k] / v, 4) for k, v in role_counts.items()
        },
        "by_intent_count": dict(
            sorted(intent_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "top_deny_reasons": sorted(deny_reasons.items(), key=lambda x: -x[1])[:5],
        "admin_break_glass_allowed": break_glass_uses,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
