"""Headline evidence chart for research/MORNING_REPORT.md (dev split, 48 calls). Numbers copied from
runs/experiments/{llm_models,champion}/summary.md (see journal). Output: research/report/headline.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
V1, FACTS, ORACLE = "#eb6834", "#2a78d6", "#1baf7a"   # reference palette slots 2, 1, 3 (all-pairs validated)
rows = [  # label, AUC, lo, hi, CV FAR, colour, champion?
    ("v1: keywords + patterns + free LLM judge + G-Eval · turbo ASR · 7B", .68, .53, .84, 86, V1, False),
    ("facts (tuned table) · turbo ASR · 7B", .84, .70, .95, 18, FACTS, False),
    ("facts (blind table) · turbo ASR · 7B", .73, .57, .88, 14, FACTS, False),
    ("facts (paraphrased questions) · large-v3 · 7B", .72, .52, .88, 23, FACTS, False),
    ("CHAMPION: facts + light keywords · large-v3 · 7B", .87, .72, .99, 14, FACTS, True),
    ("facts (tuned) · large-v3 · 14B", .85, .73, .96, 18, FACTS, False),
    ("facts (paraphrased) · large-v3 · 14B", .88, .76, .98, 9, FACTS, False),
    ("facts (blind) · large-v3 · 14B", .85, .72, .96, 27, FACTS, False),
    ("ORACLE: facts on dialect reference scripts · 14B", .90, .79, 1.00, 0, ORACLE, False),
]
rows = rows[::-1]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True, gridspec_kw={"width_ratios": [3, 1.3]},
                             facecolor=SURF)
y = range(len(rows))
for ax in (a1, a2):
    ax.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
for i, (lab, auc, lo, hi, far, col, champ) in enumerate(rows):
    a1.plot([lo, hi], [i, i], color=col, linewidth=2, solid_capstyle="round", alpha=0.55)
    a1.plot(auc, i, "o", color=col, markersize=10 if champ else 8, markeredgecolor=SURF, markeredgewidth=2)
    a1.text(hi + 0.01, i, f"{auc:.2f}", va="center", fontsize=9, color=INK if champ else INK2,
            fontweight="bold" if champ else "normal")
    a2.barh(i, far, height=0.55, color=col, alpha=0.9)
    a2.text(far + 2, i, f"{far}%", va="center", fontsize=9, color=INK2)
a1.axvline(0.5, color=MUTED, linewidth=1, linestyle=(0, (2, 2)))
a1.text(0.505, len(rows) - 0.4, "chance", color=MUTED, fontsize=8)
a1.set_yticks(list(y))
a1.set_yticklabels([r[0] for r in rows], fontsize=9, color=INK)
for t, r in zip(a1.get_yticklabels(), rows):
    if r[6]:
        t.set_fontweight("bold")
a1.set_xlim(0.45, 1.06)
a1.set_xlabel("flag AUC (needs a human vs harmless), 95% bootstrap CI", color=INK2, fontsize=9)
a2.set_xlim(0, 100)
a2.set_xlabel("false-alarm rate, CV (%)", color=INK2, fontsize=9)
a2.axvline(20, color=MUTED, linewidth=1, linestyle=(0, (2, 2)))
a2.text(21, len(rows) - 0.4, "20% cap", color=MUTED, fontsize=8)
fig.suptitle("Fact questions + policy table beat the free LLM judge; on dev the 7B's result depends on the question wording, the 14B's barely",
             x=0.01, ha="left", fontsize=11.5, color=INK, fontweight="bold")
fig.text(0.01, 0.005, "Dev split, 48 calls / 24 dialogues, CIs over 18 twin-group units. Orange = v1, blue = facts systems, "
         "green = ORACLE (no ASR, never a submission). Source: runs/experiments/llm_models, champion.", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig("research/report/headline.png", dpi=150, facecolor=SURF)
print("research/report/headline.png")
