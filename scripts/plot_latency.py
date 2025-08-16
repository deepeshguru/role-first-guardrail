#!/usr/bin/env python3
import json
from pathlib import Path
import matplotlib.pyplot as plt

log = Path("logs/audit.jsonl")
rows = [
    json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()
]
lat = [float(r.get("latency_ms", 0)) for r in rows if "latency_ms" in r]
if not lat:
    print("no latency data in logs/audit.jsonl")
    exit(0)

# Histogram
plt.figure(figsize=(6, 4))
plt.hist(lat, bins=20)
plt.xlabel("End-to-end latency (ms)")
plt.ylabel("Count")
plt.title("Latency histogram")
Path("figs").mkdir(exist_ok=True, parents=True)
plt.tight_layout()
plt.savefig("figs/latency_hist.png", dpi=160)

# ECDF
lat_sorted = sorted(lat)
y = [i / len(lat_sorted) for i in range(1, len(lat_sorted) + 1)]
plt.figure(figsize=(6, 4))
plt.plot(lat_sorted, y)
plt.xlabel("End-to-end latency (ms)")
plt.ylabel("ECDF")
plt.title("Latency ECDF")
plt.tight_layout()
plt.savefig("figs/latency_ecdf.png", dpi=160)

print("Wrote figs/latency_hist.png and figs/latency_ecdf.png")
