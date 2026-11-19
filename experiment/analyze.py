"""Experiment readout for the Cookie Cats gate test.

Reads the dbt mart fct_player_experiment from the local DuckDB file, runs the checks
and tests, writes experiment/results.md and two PNG charts. Run after `dbt build`.
"""
import sys
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
ALPHA, POWER = 0.05, 0.80
Z_A, Z_B = stats.norm.ppf(1 - ALPHA / 2), stats.norm.ppf(POWER)

df = duckdb.connect(str(ROOT / "ab_test.duckdb"), read_only=True).sql(
    "select variant, game_rounds_14d, retained_d1, retained_d7 from fct_player_experiment"
).df()
ctl, trt = df[df.variant == "gate_30"], df[df.variant == "gate_40"]
n_c, n_t = len(ctl), len(trt)
out = []
p = out.append


def pct(x, d=2):
    return f"{100 * x:.{d}f}%"


def two_prop(metric):
    """Difference in proportions (treatment minus control), Wald 95% CI, pooled z test."""
    x_c, x_t = ctl[metric].sum(), trt[metric].sum()
    p_c, p_t = x_c / n_c, x_t / n_t
    diff = p_t - p_c
    se = np.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    p_pool = (x_c + x_t) / (n_c + n_t)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
    pval = 2 * stats.norm.sf(abs(diff / se_pool))
    return dict(p_c=p_c, p_t=p_t, diff=diff, lo=diff - Z_A * se, hi=diff + Z_A * se,
                rel=diff / p_c, pval=pval, se=se)


def mde(p_base):
    """Smallest absolute difference detectable at the actual arm sizes (not observed power)."""
    return (Z_A + Z_B) * np.sqrt(p_base * (1 - p_base) * (1 / n_c + 1 / n_t))


def n_per_arm(p_base, delta):
    return int(np.ceil(2 * (Z_A + Z_B) ** 2 * p_base * (1 - p_base) / delta ** 2))


# 1. Sample ratio mismatch: the design intends a 50/50 split.
chi2, srm_p = stats.chisquare([n_c, n_t])
p("## 1. Sample ratio check")
p(f"- gate_30: {n_c:,} players, gate_40: {n_t:,} players (total {n_c + n_t:,}).")
p(f"- Share in gate_40: {pct(n_t / (n_c + n_t))}. Chi-square vs 50/50: {chi2:.2f}, p = {srm_p:.4f}.")
# Worst case for the SRM: every extra gate_40 player was a non-retained player. Drop them all.
excess = n_t - n_c
s_c, s_t = ctl.retained_d7.mean(), trt.retained_d7.sum() / n_c
s_diff = s_t - s_c
s_se = np.sqrt(s_c * (1 - s_c) / n_c + s_t * (1 - s_t) / n_c)
s_pool = (s_c + s_t) / 2   # equal arm sizes after the removal
s_p = 2 * stats.norm.sf(abs(s_diff) / np.sqrt(s_pool * (1 - s_pool) * 2 / n_c))
p(f"- Stress test: if all {excess:,} extra gate_40 players were never retained and are removed, "
  f"gate_40 7-day retention becomes {pct(s_t)} vs {pct(s_c)} in gate_30: difference {100 * s_diff:+.2f} pp, "
  f"95% CI [{100 * (s_diff - Z_A * s_se):+.2f}, {100 * (s_diff + Z_A * s_se):+.2f}], p = {s_p:.4f}.")

# 2. Power / minimum detectable effect, using the control baseline.
p("\n## 2. Power check (alpha 0.05 two-sided, power 0.80)")
for m, label in [("retained_d7", "7-day retention"), ("retained_d1", "1-day retention")]:
    base = ctl[m].mean()
    p(f"- {label}: baseline {pct(base)}; minimum detectable difference at these arm sizes "
      f"= {100 * mde(base):.2f} pp; players per arm needed to detect 1.0 pp = {n_per_arm(base, 0.01):,}.")

# 3. Primary and secondary metric.
res = {}
p("\n## 3. Retention (treatment gate_40 minus control gate_30)")
p("| Metric | gate_30 | gate_40 | Difference (pp) | 95% CI (pp) | Relative | p-value |")
p("|---|---|---|---|---|---|---|")
for m, label in [("retained_d7", "7-day retention (primary)"), ("retained_d1", "1-day retention (secondary)")]:
    r = res[m] = two_prop(m)
    p(f"| {label} | {pct(r['p_c'])} | {pct(r['p_t'])} | {100 * r['diff']:+.2f} | "
      f"[{100 * r['lo']:+.2f}, {100 * r['hi']:+.2f}] | {100 * r['rel']:+.1f}% | {r['pval']:.4f} |")

# 4. Guardrail: engagement (game rounds in 14 days). Heavily skewed, one extreme value.
g_c, g_t = ctl.game_rounds_14d, trt.game_rounds_14d
top = df.game_rounds_14d.nlargest(2).tolist()
cap = df.game_rounds_14d.quantile(0.999)
w_c, w_t = g_c.clip(upper=cap), g_t.clip(upper=cap)
welch = stats.ttest_ind(w_t, w_c, equal_var=False)
se_w = np.sqrt(w_c.var() / n_c + w_t.var() / n_t)
d_w = w_t.mean() - w_c.mean()
mw = stats.mannwhitneyu(g_t, g_c, alternative="two-sided")
p("\n## 4. Guardrail: game rounds in first 14 days")
p(f"- Distribution is very skewed: median {g_c.median():.0f} (gate_30) vs {g_t.median():.0f} (gate_40); "
  f"largest single value {top[0]:,} rounds (next largest {top[1]:,}).")
p(f"- Raw means: {g_c.mean():.2f} vs {g_t.mean():.2f}. The raw gate_30 mean is pulled up by the one extreme player.")
p(f"- Means after capping at the pooled 99.9th percentile ({cap:.0f} rounds): {w_c.mean():.2f} vs {w_t.mean():.2f}; "
  f"difference {d_w:+.2f} rounds, 95% CI [{d_w - Z_A * se_w:+.2f}, {d_w + Z_A * se_w:+.2f}], Welch p = {welch.pvalue:.4f}.")
p(f"- Mann-Whitney U (no capping needed): p = {mw.pvalue:.4f}.")
p(f"- Share of players with zero rounds: {pct((g_c == 0).mean())} vs {pct((g_t == 0).mean())}.")

(ROOT / "experiment" / "results.md").write_text(
    "# Experiment results (generated by experiment/analyze.py, do not edit by hand)\n\n" + "\n".join(out) + "\n")
print("\n".join(out))

# Charts.
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(7, 4.2))
labels = ["1-day retention", "7-day retention"]
x = np.arange(2)
for i, (arm, color) in enumerate([("gate_30", "#4C72B0"), ("gate_40", "#DD8452")]):
    rates, errs = [], []
    for m in ["retained_d1", "retained_d7"]:
        s = df[df.variant == arm][m]
        rates.append(100 * s.mean())
        errs.append(100 * Z_A * np.sqrt(s.mean() * (1 - s.mean()) / len(s)))
    ax.bar(x + (i - 0.5) * 0.38, rates, 0.38, yerr=errs, capsize=4, color=color, label=arm)
    for xi, r in zip(x + (i - 0.5) * 0.38, rates):
        ax.text(xi, r + 1.2, f"{r:.1f}%", ha="center", fontsize=10)
ax.set_xticks(x, labels)
ax.set_ylabel("Players retained (%)")
ax.set_ylim(0, 52)
ax.set_title("Retention by arm, with 95% confidence intervals")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(ROOT / "charts" / "retention_by_arm.png", dpi=150)

fig, ax = plt.subplots(figsize=(7, 4.2))
grid = np.arange(0, 201)
for arm, g, color in [("gate_30", g_c, "#4C72B0"), ("gate_40", g_t, "#DD8452")]:
    ax.plot(grid, [(g <= v).mean() * 100 for v in grid], color=color, label=arm)
ax.axvline(30, color="grey", ls=":", lw=1)
ax.axvline(40, color="grey", ls=":", lw=1)
ax.set_xlabel("Game rounds in first 14 days (axis cut at 200)")
ax.set_ylabel("Players at or below (%)")
ax.set_title("Engagement guardrail: cumulative distribution of game rounds")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(ROOT / "charts" / "game_rounds_cdf.png", dpi=150)
sys.exit(0)
