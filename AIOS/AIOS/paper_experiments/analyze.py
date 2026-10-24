"""Summary tables (markdown) + plots from results/*.csv."""
import glob, os, sys
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
out = []
ORDER = ["baseline", "agentos_relaxed", "agentos_default"]
for path in sorted(glob.glob(f"{R}/comparison_*.csv")):
    df = pd.read_csv(path); tag = df.backend.iloc[0]
    g = df.groupby("condition")
    t = pd.DataFrame({
        "runs": g.size(),
        "success_%": g.success.mean() * 100,
        "wall_s_mean": g.wall_ms.mean() / 1000, "wall_s_sd": g.wall_ms.std() / 1000,
        "llm_calls_mean": g.llm_calls.mean(),
        "llm_latency_ms_mean": g.per_call_latency_ms_mean.mean(),
        "tokens_mean": (g.prompt_tokens.mean() + g.completion_tokens.mean()),
        "kernel_overhead_ms_mean": g.kernel_overhead_ms.mean(), "kernel_overhead_ms_sd": g.kernel_overhead_ms.std(),
    }).reindex([c for c in ORDER if c in g.groups])
    if "syscalls" in df: t["syscalls_mean"] = g.syscalls.mean()
    if "quota_exceeded" in df: t["quota_exceeded_mean"] = g.quota_exceeded.mean()
    if "deadlocks_found" in df: t["deadlocks"] = g.deadlocks_found.sum()
    # per-seed success to show variance
    ps = df.groupby(["condition", "seed"]).success.mean().unstack() * 100
    out += [f"## Pipeline comparison - {tag}", t.round(2).to_markdown(), "", "Success % per seed:", ps.round(1).to_markdown(), ""]
    ag = df[df.condition != "baseline"]
    if len(ag):
        ag = ag.assign(overhead_pct=100 * ag.kernel_overhead_ms / ag.wall_ms)
        out += [f"Kernel overhead as % of wall time: mean {ag.overhead_pct.mean():.2f}%, max {ag.overhead_pct.max():.2f}%", ""]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    conds = list(t.index)
    ax[0].bar(conds, t.wall_s_mean, yerr=t.wall_s_sd, capsize=4); ax[0].set_ylabel("wall time per task (s)")
    ax[1].bar(conds, t.success_pct if "success_pct" in t else t["success_%"]); ax[1].set_ylabel("task success (%)"); ax[1].set_ylim(0, 105)
    ax[2].boxplot([df[df.condition == c].kernel_overhead_ms for c in conds if c != "baseline"], tick_labels=[c for c in conds if c != "baseline"])
    ax[2].set_ylabel("kernel overhead per task (ms)")
    for a in ax: a.tick_params(axis="x", rotation=15)
    fig.suptitle(f"AgentOS vs no-kernel baseline ({tag}, {df.seed.nunique()} seeds x {df.task.nunique()} tasks)")
    fig.tight_layout(); fig.savefig(f"{R}/comparison_{tag}.png", dpi=150); plt.close(fig)
lat = sorted(glob.glob(f"{R}/syscall_latency_*.csv"))
for p in lat:
    d = pd.read_csv(p); d = d[d.condition == "agentos_relaxed"].sort_values("mean_latency_ms", ascending=False)
    out += [f"## Mean dispatcher latency per syscall type (agentos_relaxed) - {os.path.basename(p)}", d.round(3).to_markdown(index=False), ""]
p = f"{R}/deadlock_injection.csv"
if os.path.exists(p):
    d = pd.read_csv(p); g = d.groupby(["n_agents", "mode"])
    t = pd.DataFrame({"trials": g.size(), "stalled": g.stalled.sum(), "completed_%": 100 * g.completed_rounds.sum() / g.expected_rounds.sum(),
                      "makespan_ms_mean": g.makespan_ms.mean(), "makespan_ms_sd": g.makespan_ms.std(),
                      "deadlocks_detected_mean": g.deadlocks_detected.mean(), "restarts_mean": g.restarts.mean(),
                      "refused_grants_mean": g.refused_grants.mean()})
    out += ["## Deadlock / contention injection (capacity=%d, claim K=%d)" % (d.capacity.iloc[0], d.k_claim.iloc[0]), t.round(1).to_markdown(), ""]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for mode, sub in d.groupby("mode"):
        m = sub.groupby("n_agents")
        ax[0].errorbar(m.makespan_ms.mean().index, m.makespan_ms.mean(), yerr=m.makespan_ms.std(), marker="o", capsize=3, label=mode)
        ax[1].plot(m.size().index, 100 * m.completed_rounds.sum() / m.expected_rounds.sum(), marker="o", label=mode)
    ax[0].set_xlabel("agents"); ax[0].set_ylabel("makespan (ms)"); ax[1].set_xlabel("agents"); ax[1].set_ylabel("rounds completed (%)")
    ax[0].legend(fontsize=8); fig.suptitle("Banker's avoidance vs detection+recovery vs none"); fig.tight_layout()
    fig.savefig(f"{R}/deadlock_injection.png", dpi=150); plt.close(fig)
open(f"{R}/summary.md", "w").write("\n".join(out)); print("\n".join(out))
