"""
Pre-styled chart helpers, injected into the sandbox execution namespace so the
Coder calls these instead of hand-writing matplotlib styling every time.

Why this exists: asking a 7B model to correctly apply ~8 styling rules (colors,
zero-line, spines, data labels, layout...) in raw matplotlib every single
generation is unreliable — it tends to get some right and skip others. Moving
the styling into deterministic, tested Python here means the model only has to
pick the right chart type and hand it data, which is a much easier ask.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PASTEL_PALETTE = ["#A1C9F4", "#FFB482", "#8DE5A1", "#FF9F9B", "#D0BBFF",
                  "#DEBB9B", "#FAB0E4", "#B9F2F0", "#FFD6A5", "#CFCFCF"]


def _finish(fig, ax, chart_path):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150)
    plt.close(fig)


def plot_bar(categories, values, title, xlabel, ylabel, chart_path):
    """Bar chart comparing a metric across categories. Bars are colored green/red
    automatically if any value is negative (e.g. a change or difference);
    otherwise each category gets a distinct color from a pastel palette."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9, 5.5))

    signed = any(v < 0 for v in values)
    if signed:
        colors = ["#8DE5A1" if v >= 0 else "#FF9F9B" for v in values]
    else:
        colors = [PASTEL_PALETTE[i % len(PASTEL_PALETTE)] for i in range(len(values))]

    bars = ax.bar(categories, values, color=colors, edgecolor="#555555", linewidth=0.6)
    if signed:
        ax.axhline(0, color="#333333", linewidth=0.8, zorder=1)
    ax.bar_label(bars, fmt="%.0f")
    ax.set_title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)

    if len(categories) > 5 or max(len(str(c)) for c in categories) > 8:
        plt.xticks(rotation=35, ha="right")

    _finish(fig, ax, chart_path)


def plot_line(x, y, title, xlabel, ylabel, chart_path):
    """Line chart for a trend over time or any ordered sequence."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9, 5.5))

    ax.plot(x, y, marker="o", color="#7C83FD", linewidth=2.5, markersize=7,
            markerfacecolor="#FFB482", markeredgecolor="#7C83FD", markeredgewidth=1.5)
    ax.set_title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)

    if len(x) > 6:
        plt.xticks(rotation=35, ha="right")

    _finish(fig, ax, chart_path)


def plot_pie(labels, values, title, chart_path):
    """Pie chart for parts of a whole. Best with 5 or fewer slices."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(7, 7))

    colors = [PASTEL_PALETTE[i % len(PASTEL_PALETTE)] for i in range(len(values))]

    ax.pie(values, labels=labels, colors=colors, autopct="%1.0f%%", startangle=90,
           wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.set_title(title, fontsize=14)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=150)
    plt.close(fig)


def plot_scatter(x, y, title, xlabel, ylabel, chart_path):
    """Scatter plot for the relationship between two numeric variables."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.scatter(x, y, color="#7C83FD", alpha=0.8, edgecolors="white", linewidth=0.8, s=75)
    ax.set_title(title, fontsize=14)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)

    _finish(fig, ax, chart_path)
