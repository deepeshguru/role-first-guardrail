#!/usr/bin/env python3
"""
Generate Role-First Guardrail architecture diagrams (High-level & Low-level)
Outputs PNG and SVG images to the chosen directory.

Usage:
  python scripts/make_diagrams.py --outdir figs
"""
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import patheffects as pe


# ----------------------- drawing helpers -----------------------
def draw_box(
    ax,
    center,
    width,
    height,
    text,
    fontsize=11,
    fc="#FFFFFF",
    ec="#000000",
    lw=1.3,
    rounding=0.02,
):
    x = center[0] - width / 2
    y = center[1] - height / 2
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.015,rounding_size={rounding}",
        linewidth=lw,
        facecolor=fc,
        edgecolor=ec,
    )
    ax.add_patch(box)
    txt = ax.text(
        center[0],
        center[1],
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        wrap=True,
    )
    # slight white halo for legibility
    txt.set_path_effects([pe.withStroke(linewidth=3, foreground="white")])
    return box


def draw_arrow(ax, start, end, connectionstyle="arc3,rad=0.0", lw=1.2):
    arr = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=lw,
        connectionstyle=connectionstyle,
        color="black",
    )
    ax.add_patch(arr)
    return arr


def save_fig(fig, out_png: Path, out_svg: Path, dpi_png=220):
    fig.savefig(out_png, dpi=dpi_png, bbox_inches="tight")
    fig.savefig(out_svg, dpi=300, bbox_inches="tight", format="svg")
    plt.close(fig)


# ----------------------- high-level diagram -----------------------
def make_high_level(outdir: Path):
    fig = plt.figure(figsize=(10, 12))
    ax = plt.gca()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.5,
        0.98,
        "Role-First Guardrail — High-Level Architecture",
        ha="center",
        va="top",
        fontsize=14,
        weight="bold",
    )

    # Main flow
    y = [0.92, 0.83, 0.74, 0.65, 0.56]  # Client -> Headers -> Gate0 -> Gate1 -> Gate2
    x = 0.5
    w = 0.56
    h = 0.09

    draw_box(ax, (x, y[0]), w * 0.6, h, "Client", fontsize=12)
    draw_box(
        ax, (x, y[1]), w, h, "Headers\n(role, org_unit, geo,\nticket_id, justification)"
    )
    draw_box(
        ax,
        (x, y[2]),
        w,
        h,
        "[ Gate 0 ] Identity / Role Context\n(dev: headers; prod: JWT claims)",
    )
    draw_box(
        ax,
        (x, y[3]),
        w,
        h,
        "[ Gate 1 ] Intent Classifier\n(zero-shot SBERT) → intent + confidence)",
    )
    draw_box(
        ax,
        (x, y[4]),
        w,
        h,
        "[ Gate 2 ] Policy Check\n(YAML RBAC/ABAC) → allow/deny + reason)",
    )

    for i in range(len(y) - 1):
        draw_arrow(ax, (x, y[i] - h / 2), (x, y[i + 1] + h / 2))

    # Branches
    xL, xR = 0.25, 0.75
    y1, y2 = 0.44, 0.34
    draw_box(ax, (xL, y1), 0.50, h, "ALLOW → (optional) Retrieval ACLs / Redaction")
    draw_box(ax, (xL, y2), 0.30, h, "LLM call")
    draw_box(ax, (xR, y1), 0.50, h, "DENY → return refusal with reason")

    draw_arrow(ax, (x - w / 2, y[4] - h / 2), (xL, y1 + h / 2))
    draw_arrow(ax, (x + w / 2, y[4] - h / 2), (xR, y1 + h / 2))
    draw_arrow(ax, (xL, y1 - h / 2), (xL, y2 + h / 2))

    draw_box(
        ax,
        (0.5, 0.18),
        0.78,
        h,
        "[ Audit ] JSONL with role/attrs/intent/decision/latency",
    )
    draw_arrow(ax, (xL, y2 - h / 2), (0.40, 0.22), connectionstyle="arc3,rad=0.2")
    draw_arrow(ax, (xR, y1 - h / 2), (0.60, 0.22), connectionstyle="arc3,rad=-0.2")

    save_fig(
        fig,
        outdir / "architecture_high_level.png",
        outdir / "architecture_high_level.svg",
    )


# ----------------------- low-level diagram -----------------------
def make_low_level(outdir: Path):
    fig = plt.figure(figsize=(12, 12))
    ax = plt.gca()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.5,
        0.98,
        "Role-First Guardrail — Low-Level Architecture",
        ha="center",
        va="top",
        fontsize=14,
        weight="bold",
    )

    # Central pipeline
    w, h = 0.52, 0.085
    xc = 0.5
    ys = [0.92, 0.83, 0.735, 0.64, 0.545, 0.45]
    draw_box(ax, (xc, ys[0]), w * 0.55, h, "Client / Swagger / curl", fontsize=12)
    draw_box(ax, (xc, ys[1]), w, h, "FastAPI app.main → POST /chat\n(GET /whoami)")
    draw_box(
        ax,
        (xc, ys[2]),
        w,
        h,
        "Gate 0: role_context.get_user_role\n(Dev: headers | Prod: verify JWT claims)",
    )
    draw_box(
        ax,
        (xc, ys[3]),
        w,
        h,
        "Gate 1: ZeroShotIntent (SBERT + prototypes)\n→ intent, confidence",
    )
    draw_box(
        ax, (xc, ys[4]), w, h, "Gate 2: RoleGate (YAML policy)\n→ allow/deny, reason"
    )
    draw_box(
        ax,
        (xc, ys[5]),
        w,
        h,
        "ALLOW → upstream LLM (call_upstream_llm)\nDENY → refusal payload",
    )

    for i in range(len(ys) - 1):
        draw_arrow(ax, (xc, ys[i] - h / 2), (xc, ys[i + 1] + h / 2))

    # Side elements
    draw_box(ax, (0.15, ys[2]), 0.26, h, "Security headers\n(APIKeyHeader in /docs)")
    draw_arrow(ax, (0.28, ys[2]), (xc - w / 2, ys[2]))

    draw_box(ax, (0.17, ys[4]), 0.30, h, "Policy file\nconfig/role_intent_policy.yml")
    draw_arrow(ax, (0.32, ys[4]), (xc - w / 2, ys[4]))

    draw_box(
        ax,
        (0.85, ys[5] + 0.07),
        0.28,
        h,
        "(Optional) Redaction\n(per-role profiles / Presidio)",
    )
    draw_arrow(ax, (xc + w / 2, ys[5]), (0.71, ys[5] + 0.07))

    draw_box(
        ax,
        (xc, 0.28),
        0.78,
        h,
        "Audit: app.audit.log_event → logs/audit.jsonl\n"
        "{role, attrs, intent, decision, reason, latency_ms, t_intent_ms, t_policy_ms}",
    )
    draw_arrow(ax, (xc, ys[5] - h / 2), (xc, 0.28 + h / 2))

    draw_box(
        ax,
        (0.3, 0.18),
        0.38,
        h,
        "scripts/metrics_from_audit.py\nLatency P50/P95, allow rates, reasons",
    )
    draw_box(
        ax,
        (0.70, 0.18),
        0.38,
        h,
        "scripts/eval_cases.py + tests/cases.csv\nFAR/FDR on labeled prompts",
    )
    draw_arrow(
        ax, (0.45, 0.28 - h / 2), (0.30, 0.18 + h / 2), connectionstyle="arc3,rad=0.1"
    )
    draw_arrow(
        ax, (0.55, 0.28 - h / 2), (0.70, 0.18 + h / 2), connectionstyle="arc3,rad=-0.1"
    )

    draw_box(
        ax,
        (xc, 0.06),
        0.90,
        0.09,
        "Notes:\n• Deny on unknown intent by default.  • Admin override requires ticket_id + justification.\n"
        "• Replace header stub with verified JWT in production.  • Add Retrieval ACLs before LLM call.",
        fontsize=9,
    )

    save_fig(
        fig,
        outdir / "architecture_low_level.png",
        outdir / "architecture_low_level.svg",
    )


# ----------------------- CLI -----------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="figs", help="Output directory for diagrams")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    make_high_level(outdir)
    make_low_level(outdir)

    print(f"[ok] Diagrams written to: {outdir.resolve()}")
    print(" - architecture_high_level.png / .svg")
    print(" - architecture_low_level.png / .svg")


if __name__ == "__main__":
    main()
