"""
evaluation.py
Weighted scoring/prioritization logic (Pandas + NumPy) and Matplotlib
chart generation for idea-level and dashboard-level analytics.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless rendering, safe for a web server
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(BASE_DIR, "static", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Weighted criteria (sum to 1.0)
WEIGHTS = {
    "business_value": 0.25,
    "feasibility": 0.20,
    "strategic_alignment": 0.20,
    "potential_impact": 0.15,
    "novelty": 0.10,
    "cost_score": 0.10,
}

PALETTE = {
    "ink": "#3D4A34", "amber": "#A3B18A", "teal": "#8A9B6E",
    "red": "#C1666B", "bg": "#F5F0E6", "card": "#E2ECE9",
    "text": "#1E2E27", "muted": "#718078", "border": "#CBD9D3",
}
CHART_COLORS = [PALETTE["teal"], PALETTE["amber"], PALETTE["ink"], PALETTE["red"], PALETTE["muted"], "#B7A17A"]


def cost_to_score(cost, max_cost=500000):
    """Lower cost => higher score (0-10 scale)."""
    try:
        cost = float(cost)
    except (TypeError, ValueError):
        return 5.0
    cost = max(0, min(cost, max_cost))
    return round(10 * (1 - cost / max_cost), 2)


def score_idea(idea_id, business_value, feasibility, cost, strategic_alignment, novelty, potential_impact):
    """
    All criteria except cost are entered on a 0-10 scale by the reviewer.
    Returns dict with cost_score and the weighted final_score (0-100), plus
    saves a per-idea evaluation chart.
    """
    cost_score = cost_to_score(cost)
    values = {
        "business_value": float(business_value),
        "feasibility": float(feasibility),
        "strategic_alignment": float(strategic_alignment),
        "potential_impact": float(potential_impact),
        "novelty": float(novelty),
        "cost_score": cost_score,
    }
    weighted = np.array([values[k] * WEIGHTS[k] for k in WEIGHTS])
    final_score = round(float(np.sum(weighted)) * 10, 2)  # scale 0-100

    create_evaluation_chart(idea_id, values)

    return {
        "cost_score": cost_score,
        "final_score": final_score,
        **values,
    }


def create_evaluation_chart(idea_id, values: dict):
    labels = list(values.keys())
    scores = [values[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6, 3.2), facecolor=PALETTE["bg"])
    ax.set_facecolor(PALETTE["card"])
    y_pos = np.arange(len(labels))
    ax.barh(y_pos, scores, color=CHART_COLORS[: len(labels)])
    ax.set_yticks(y_pos)
    ax.set_yticklabels([l.replace("_", " ").title() for l in labels], color=PALETTE["text"], fontsize=9)
    ax.set_xlim(0, 10)
    ax.set_xlabel("Score (0-10)", color=PALETTE["text"])
    ax.tick_params(colors=PALETTE["text"])
    ax.grid(axis="x", linestyle="--", alpha=0.4, color=PALETTE["muted"])
    for spine in ax.spines.values():
        spine.set_color(PALETTE["border"])
    ax.set_title(f"Evaluation Breakdown - Idea #{idea_id}", color=PALETTE["ink"], fontsize=11, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, f"idea_{idea_id}.png")
    fig.savefig(path, dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)
    return f"charts/idea_{idea_id}.png"


def _save(fig, filename):
    path = os.path.join(CHARTS_DIR, filename)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)
    return f"charts/{filename}"


def status_distribution_chart(df: pd.DataFrame):
    counts = df["status"].value_counts()
    fig, ax = plt.subplots(figsize=(5, 4), facecolor=PALETTE["bg"])
    if counts.empty:
        ax.text(0.5, 0.5, "No ideas yet", ha="center", color=PALETTE["muted"])
    else:
        ax.pie(
            counts.values, labels=counts.index, autopct="%1.0f%%",
            colors=CHART_COLORS[: len(counts)],
            textprops={"color": PALETTE["text"], "fontsize": 9},
            wedgeprops={"edgecolor": PALETTE["bg"]},
        )
    ax.set_title("Ideas by Status", color=PALETTE["ink"], fontweight="bold")
    return _save(fig, "status_distribution.png")


def department_contribution_chart(df: pd.DataFrame):
    counts = df["department"].value_counts()
    fig, ax = plt.subplots(figsize=(6, 3.5), facecolor=PALETTE["bg"])
    ax.set_facecolor(PALETTE["card"])
    if counts.empty:
        ax.text(0.5, 0.5, "No ideas yet", ha="center", color=PALETTE["muted"])
    else:
        ax.bar(counts.index, counts.values, color=CHART_COLORS[: len(counts)])
        ax.tick_params(axis="x", rotation=30, colors=PALETTE["text"])
        ax.tick_params(axis="y", colors=PALETTE["text"])
    ax.set_ylabel("Ideas Submitted", color=PALETTE["text"])
    ax.set_title("Department Contribution", color=PALETTE["ink"], fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color=PALETTE["muted"])
    for spine in ax.spines.values():
        spine.set_color(PALETTE["border"])
    return _save(fig, "department_contribution.png")


def implementation_progress_chart(df: pd.DataFrame):
    stages = ["Submitted", "Under Review", "Pending Approval", "Approved", "Implemented", "Rejected"]
    counts = [len(df[df["status"] == s]) for s in stages]
    fig, ax = plt.subplots(figsize=(6.5, 3.5), facecolor=PALETTE["bg"])
    ax.set_facecolor(PALETTE["card"])
    ax.bar(stages, counts, color=CHART_COLORS)
    ax.set_ylabel("Number of Ideas", color=PALETTE["text"])
    ax.set_title("Lifecycle / Implementation Progress", color=PALETTE["ink"], fontweight="bold")
    ax.tick_params(axis="x", rotation=20, colors=PALETTE["text"])
    ax.tick_params(axis="y", colors=PALETTE["text"])
    ax.grid(axis="y", linestyle="--", alpha=0.4, color=PALETTE["muted"])
    for spine in ax.spines.values():
        spine.set_color(PALETTE["border"])
    return _save(fig, "implementation_progress.png")


def roi_chart(df: pd.DataFrame):
    d = df.copy()
    d["roi_estimate"] = pd.to_numeric(d["roi_estimate"], errors="coerce").fillna(0)
    d = d[d["roi_estimate"] > 0].sort_values("roi_estimate", ascending=False).head(8)
    fig, ax = plt.subplots(figsize=(6.5, 3.5), facecolor=PALETTE["bg"])
    ax.set_facecolor(PALETTE["card"])
    if d.empty:
        ax.text(0.5, 0.5, "No ROI data yet (set on approval)", ha="center", color=PALETTE["muted"])
    else:
        labels = [f"#{i}" for i in d["id"]]
        ax.bar(labels, d["roi_estimate"], color=PALETTE["teal"])
        ax.tick_params(colors=PALETTE["text"])
        ax.grid(axis="y", linestyle="--", alpha=0.4, color=PALETTE["muted"])
    ax.set_ylabel("Estimated ROI (%)", color=PALETTE["text"])
    ax.set_title("Top ROI Ideas", color=PALETTE["ink"], fontweight="bold")
    for spine in ax.spines.values():
        spine.set_color(PALETTE["border"])
    return _save(fig, "roi_chart.png")


def top_priority_ideas(df: pd.DataFrame, n=5):
    d = df.copy()
    d["final_score"] = pd.to_numeric(d["final_score"], errors="coerce").fillna(0)
    d = d[d["status"].isin(["Under Review", "Pending Approval", "Approved"])]
    return d.sort_values("final_score", ascending=False).head(n)


def department_resource_recommendation(df: pd.DataFrame):
    """Simple AI-style recommendation: departments generating the most
    high-scoring ideas should get more innovation resourcing."""
    d = df.copy()
    d["final_score"] = pd.to_numeric(d["final_score"], errors="coerce").fillna(0)
    if d.empty:
        return []
    grouped = d.groupby("department")["final_score"].agg(["mean", "count"]).reset_index()
    grouped = grouped[grouped["count"] > 0].sort_values("mean", ascending=False)
    out = []
    for _, row in grouped.head(3).iterrows():
        out.append(
            f"{row['department']}: avg score {row['mean']:.1f} across {int(row['count'])} idea(s) "
            f"-- recommend prioritizing innovation budget/time here."
        )
    return out


def trend_recommendation(df: pd.DataFrame):
    if df.empty:
        return "Not enough data yet to detect trends."
    top_cat = df["ai_category"].value_counts()
    if top_cat.empty:
        return "Not enough data yet to detect trends."
    cat, count = top_cat.index[0], int(top_cat.iloc[0])
    return f"'{cat}' is the most common innovation theme right now ({count} idea(s)) -- consider a themed innovation sprint."
