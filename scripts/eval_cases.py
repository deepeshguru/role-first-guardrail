#!/usr/bin/env python3
import csv, json, argparse
from urllib import request, error

HEADER_MAP = {
    "org_unit": "x-user-orgunit",
    "geo": "x-user-geo",
    "ticket_id": "x-ticket-id",
    "justification": "x-justification",
}

def post_chat(base_url: str, role: str, attrs: dict, prompt: str, timeout: float = 20.0):
    """Return (status, json_dict) even for 4xx (403 deny)."""
    url = base_url.rstrip("/") + "/chat"
    headers = {"Content-Type": "application/json", "x-user-role": role}
    for k, v in attrs.items():
        hdr = HEADER_MAP.get(k)
        if hdr and v is not None:
            headers[hdr] = str(v)

    payload = {"messages": [{"role": "user", "content": prompt}]}
    data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            status = resp.getcode()
    except error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None, {"_transport_error": str(e)}

    try:
        js = json.loads(body) if body.strip().startswith("{") else {}
    except Exception:
        js = {"_parse_error": body[:200]}
    return status, js

def infer_allowed(status: int, js: dict):
    """
    Normalize outcome:
      - If JSON has response.blocked, use that.
      - Else: treat 2xx as allowed, 403 as deny, others as error/unknown.
    """
    resp = js.get("response") if isinstance(js, dict) else None
    if isinstance(resp, dict) and "blocked" in resp:
        return not bool(resp.get("blocked")), None
    if status is None:
        return None, js.get("_transport_error")
    if status == 403:
        return False, None
    if 200 <= status < 300:
        return True, None
    return None, js.get("error") or js.get("_parse_error")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="tests/cases.csv")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args()

    rows = []
    with open(args.csv, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f, skipinitialspace=True)
        for r in rdr:
            role = (r.get("role") or "").strip()
            prompt = (r.get("prompt") or "").strip().strip('"')
            if not role or role.startswith("#") or not prompt:
                # skip comment/blank lines
                continue
            try:
                attrs = json.loads(r.get("attrs_json") or "{}")
            except Exception:
                attrs = {}
            exp_allow = str(r.get("expected_allow") or "").strip().lower() in ("1","true","yes")
            rows.append({"role": role, "attrs": attrs, "prompt": prompt, "expected": exp_allow})

    total = len(rows)
    exp_allow = sum(1 for r in rows if r["expected"])
    exp_deny  = total - exp_allow
    tp = tn = fp = fn = 0
    results = []

    for i, r in enumerate(rows, 1):
        status, js = post_chat(args.base_url, r["role"], r["attrs"], r["prompt"], timeout=args.timeout)
        allowed, err = infer_allowed(status, js)
        intent = (js.get("response") or {}).get("intent") if isinstance(js, dict) else None
        reason = (js.get("response") or {}).get("reason") if isinstance(js, dict) else None

        if allowed is None:
            results.append({
                "case": i, "role": r["role"], "prompt": r["prompt"],
                "expected_allow": r["expected"], "error": err or f"HTTP {status}"
            })
            continue

        if r["expected"] and allowed: tp += 1
        elif r["expected"] and not allowed: fn += 1
        elif not r["expected"] and allowed: fp += 1
        else: tn += 1

        results.append({
            "case": i,
            "role": r["role"],
            "prompt": r["prompt"],
            "expected_allow": r["expected"],
            "got_allow": allowed,
            "intent": intent,
            "reason": reason,
            "http_status": status,
        })

    far = (fp / exp_deny) if exp_deny else 0.0
    fdr = (fn / exp_allow) if exp_allow else 0.0
    summary = {
        "total_cases": total,
        "expected_allow": exp_allow,
        "expected_deny": exp_deny,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "FAR": round(far, 4),
        "FDR": round(fdr, 4),
        "results": results,
    }
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
