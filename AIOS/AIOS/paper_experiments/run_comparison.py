"""AgentOS vs. no-kernel baseline on a fixed, seeded task set.

Conditions
  baseline         - direct LLM calls, no kernel (baseline.py); 5 LLM calls/task
  agentos_relaxed  - stock PipelineRunner, quotas raised to 10 calls/min so the
                     call count matches the baseline -> isolates kernel overhead
  agentos_default  - stock PipelineRunner with the repo's DEFAULT_STAGE_QUOTAS
                     (coder 1 call/min -> refine call is QUOTA_EXCEEDED)

Usage
  python run_comparison.py --backend mock   --seeds 3
  python run_comparison.py --backend ollama --model qwen2.5:1.5b --seeds 3 [--tasks 4]
"""
import argparse, asyncio, csv, json, os, platform, statistics as st, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("AGENTOS_REPO", os.path.join(HERE, "..", "AgentOS")))
sys.path.insert(0, HERE)

from kernel.memory.embeddings import HashingEmbedder, set_embedder
from kernel.access_control import AccessControl, QuotaManager
from kernel.filesystem import SemanticFS
from kernel.memory import PageManager
from kernel.syscalls import SyscallDispatcher
from agents.pipeline import PipelineRunner, DEFAULT_STAGE_QUOTAS
import llm
from tasks import TASKS, check
from baseline import run_baseline

RELAXED = {k: {"max_pages": v["max_pages"], "max_calls_per_minute": 10} for k, v in DEFAULT_STAGE_QUOTAS.items()}


def make_dispatcher(tmp, driver_cls):
    acl = AccessControl()
    return SyscallDispatcher(
        access_control=acl,
        filesystem=SemanticFS(access_control=acl, fs_root=f"{tmp}/fs_root", chroma_path=f"{tmp}/fs_chroma"),
        page_manager=PageManager(chroma_path=f"{tmp}/mem_chroma"),
        quota_manager=QuotaManager(window_seconds=60),
        driver_registry={"ollama": driver_cls}, record_state=False)


def summarize_calls(calls):
    return {"llm_calls": len(calls), "driver_ms_total": sum(c["driver_ms"] for c in calls),
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "completion_tokens": sum(c["completion_tokens"] for c in calls),
            "per_call_latency_ms_mean": st.mean([c["driver_ms"] for c in calls]) if calls else 0}


async def run_agentos(task, driver_cls, quotas, tmp):
    disp = make_dispatcher(tmp, driver_cls)
    res = await PipelineRunner(disp).run(task["topic"], driver="ollama", quotas=quotas)
    log = disp.log
    by_type = {}
    for s in log:
        by_type.setdefault(s.type.value, []).append(s.latency_ms)
    total_syscall_ms = sum(s.latency_ms for s in log)
    sandbox_ms = sum((s.result or {}).get("duration_ms") or 0 for s in log if s.type.value == "TOOL_CALL" and isinstance(s.result, dict))
    status_counts = {}
    for s in log:
        status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1
    tester = res.get("tester") or {}
    pm = disp.page_manager
    return {"status": res["status"], "stdout": tester.get("stdout", ""), "passed_exec": bool(tester.get("passed")),
            "syscalls": len(log), "syscall_ms_total": total_syscall_ms, "sandbox_ms": sandbox_ms,
            "quota_exceeded": status_counts.get("quota_exceeded", 0),
            "syscall_errors": sum(v for k, v in status_counts.items() if k not in ("success", "quota_exceeded")),
            "deadlock_scans": len(by_type.get("DEADLOCK_DETECT", [])),
            "deadlocks_found": len(disp.deadlock_detector.recoveries),
            "mem_hits": getattr(pm, "hits", 0) if hasattr(pm, "hits") else 0,
            "by_type": {k: (len(v), st.mean(v)) for k, v in by_type.items()}}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["mock", "ollama"], default="mock")
    ap.add_argument("--model", default=llm.CONFIG["model"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--tasks", type=int, default=len(TASKS))
    ap.add_argument("--conditions", default="baseline,agentos_relaxed,agentos_default")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results"))
    a = ap.parse_args()
    llm.CONFIG["model"] = a.model
    set_embedder(HashingEmbedder())  # offline embeddings for SemanticFS, same as the test suite
    driver_cls = llm.get_driver(a.backend)
    if a.backend == "ollama" and not driver_cls().is_available():
        sys.exit("Ollama not reachable at " + llm.CONFIG["host"])
    tag = a.backend if a.backend == "mock" else f"ollama_{a.model.replace(':', '-')}"
    os.makedirs(a.out, exist_ok=True)
    rows, typestats = [], {}
    conds = a.conditions.split(",")
    for seed in range(a.seeds):
        llm.CONFIG["seed"] = seed
        for task in TASKS[: a.tasks]:
            # rotate condition order per (seed, task) to avoid warm-cache bias
            order = conds[(seed + int(task["id"][1:])) % len(conds):] + conds[: (seed + int(task["id"][1:])) % len(conds)]
            for cond in order:
                llm.CALLS.clear()
                t0 = time.perf_counter()
                with tempfile.TemporaryDirectory() as tmp:
                    try:
                        if cond == "baseline":
                            r = await run_baseline(task["topic"], driver_cls)
                        else:
                            r = await run_agentos(task, driver_cls, RELAXED if cond == "agentos_relaxed" else DEFAULT_STAGE_QUOTAS, tmp)
                    except Exception as e:  # record, don't crash the sweep
                        r = {"status": f"crash:{type(e).__name__}", "stdout": ""}
                wall = (time.perf_counter() - t0) * 1000
                c = summarize_calls(llm.CALLS)
                for k, v in r.pop("by_type", {}).items():
                    typestats.setdefault((cond, k), []).append(v[1])
                kern = r.get("syscall_ms_total", 0) - c["driver_ms_total"] - r.get("sandbox_ms", 0) if cond != "baseline" else 0
                row = {"backend": tag, "condition": cond, "seed": seed, "task": task["id"], "wall_ms": round(wall, 2),
                       **{k: round(v, 3) if isinstance(v, float) else v for k, v in c.items()},
                       "kernel_overhead_ms": round(kern, 3), "success": check(task, r.get("stdout", "")),
                       **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ("stdout", "llm_calls")}, "stdout_head": (r.get("stdout") or "")[:80].replace("\n", " | ")}
                rows.append(row)
                print(f"[{tag}] s{seed} {task['id']} {cond:16s} wall={wall:8.1f}ms calls={c['llm_calls']} ok={row['success']} kern={kern:.1f}ms", flush=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    csv_path = os.path.join(a.out, f"comparison_{tag}.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    with open(os.path.join(a.out, f"syscall_latency_{tag}.csv"), "w") as f:
        f.write("condition,syscall,mean_latency_ms,n_runs\n")
        for (cond, k), v in sorted(typestats.items()):
            f.write(f"{cond},{k},{st.mean(v):.4f},{len(v)}\n")
    meta = {"backend": tag, "model": a.model if a.backend == "ollama" else "DETERMINISTIC MOCK (not an LLM)",
            "seeds": a.seeds, "tasks": a.tasks, "python": platform.python_version(), "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "finished": time.strftime("%Y-%m-%d %H:%M:%S %z")}
    json.dump(meta, open(os.path.join(a.out, f"meta_{tag}.json"), "w"), indent=2)
    print("wrote", csv_path)


if __name__ == "__main__":
    asyncio.run(main())
