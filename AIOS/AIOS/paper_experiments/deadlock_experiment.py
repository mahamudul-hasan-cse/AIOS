"""Controlled contention / deadlock-injection experiment on AgentOS's real
ResourceManager (Banker's Algorithm) and DeadlockDetector.

Workload: N agents share one provider pool of capacity C. Each agent needs K
slots at once (max_claim=K) to make an LLM "call", and acquires them one at a
time (hold-and-wait), with seeded random jitter. After holding K slots it
"works" for W ms, releases everything, and repeats for R rounds.
N*K > C, so greedy allocation can deadlock.

Modes
  bankers_on            avoidance enabled (unsafe grants refused), no detector
  bankers_off_detect    greedy grants; DeadlockDetector scans every SCAN ms and
                        kills a victim (release_all) - victim restarts its round
  bankers_off_none      greedy grants, no detection -> measures stalls

Per trial: makespan, completed rounds, deadlocks detected, victims, refused
grant attempts, whether the trial stalled (no progress before TIMEOUT).
Only the agent loop is synthetic; the allocator and detector are AgentOS code.
"""
import argparse, asyncio, csv, os, random, statistics as st, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("AGENTOS_REPO", os.path.join(HERE, "..", "AgentOS")))
from kernel.access_control.resource_manager import ResourceManager
from kernel.access_control.deadlock_detector import DeadlockDetector

POOL = "llm_pool"


async def trial(mode, seed, n, k, cap, rounds, work_ms, scan_ms, timeout_s):
    rng = random.Random(seed)
    rm = ResourceManager(capacities={POOL: cap}, avoidance_enabled=(mode == "bankers_on"))
    killed = set()

    async def terminate(pid):
        killed.add(pid)

    det = DeadlockDetector(rm, scheduler=None, terminate=terminate, interval=scan_ms / 1000)
    stats = {"refused": 0, "victims": 0, "deadlocks": 0, "completed": 0, "restarts": 0}
    last_progress = [time.perf_counter()]

    async def agent(i):
        aid = f"agent{i}"
        done = 0
        while done < rounds:
            held = 0
            while held < k:
                if aid in killed:            # we were chosen as a deadlock victim
                    killed.discard(aid); held = 0; stats["restarts"] += 1
                    await asyncio.sleep(rng.uniform(0, 0.01)); continue
                if await rm.request(aid, POOL, units=1, max_claim=k):
                    held += 1; last_progress[0] = time.perf_counter()
                    await asyncio.sleep(rng.uniform(0, 0.004))
                else:
                    stats["refused"] += 1
                    await asyncio.sleep(0.002)
            await asyncio.sleep(work_ms / 1000 * rng.uniform(0.5, 1.5))
            if aid in killed:   # killed while working: work lost, retry the round
                killed.discard(aid); stats["restarts"] += 1; continue
            await rm.release(aid, POOL, units=held)
            done += 1; stats["completed"] += 1; last_progress[0] = time.perf_counter()

    async def scanner():
        while True:
            await asyncio.sleep(scan_ms / 1000)
            r = det.detect()
            if r.deadlocked:
                stats["deadlocks"] += 1
                rec = await det.recover(r.cycle)
                if rec.get("victim"):
                    stats["victims"] += 1

    t0 = time.perf_counter()
    tasks = [asyncio.create_task(agent(i)) for i in range(n)]
    scan = asyncio.create_task(scanner()) if mode == "bankers_off_detect" else None
    stalled = False
    while not all(t.done() for t in tasks):
        await asyncio.sleep(0.01)
        if time.perf_counter() - last_progress[0] > timeout_s:
            stalled = True; break
    for t in tasks + ([scan] if scan else []):
        t.cancel()
    await asyncio.gather(*tasks, *( [scan] if scan else []), return_exceptions=True)
    makespan = (time.perf_counter() - t0) * 1000
    return {"mode": mode, "seed": seed, "n_agents": n, "k_claim": k, "capacity": cap, "rounds": rounds,
            "makespan_ms": round(makespan, 1), "completed_rounds": stats["completed"],
            "expected_rounds": n * rounds, "stalled": stalled, "deadlocks_detected": stats["deadlocks"],
            "victims_killed": stats["victims"], "restarts": stats["restarts"], "refused_grants": stats["refused"],
            "throughput_rounds_per_s": round(stats["completed"] / (makespan / 1000), 2)}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--agents", default="4,6,8")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--capacity", type=int, default=6)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--work-ms", type=float, default=20)
    ap.add_argument("--scan-ms", type=float, default=50)
    ap.add_argument("--timeout-s", type=float, default=2.0)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results"))
    a = ap.parse_args()
    rows = []
    for n in map(int, a.agents.split(",")):
        for mode in ["bankers_on", "bankers_off_detect", "bankers_off_none"]:
            for s in range(a.seeds):
                r = await trial(mode, s, n, a.k, a.capacity, a.rounds, a.work_ms, a.scan_ms, a.timeout_s)
                rows.append(r)
            sub = [r for r in rows if r["mode"] == mode and r["n_agents"] == n]
            print(f"N={n} {mode:20s} makespan={st.mean(r['makespan_ms'] for r in sub):8.1f}ms "
                  f"stalled={sum(r['stalled'] for r in sub)}/{len(sub)} deadlocks={sum(r['deadlocks_detected'] for r in sub)} "
                  f"refused={st.mean(r['refused_grants'] for r in sub):.0f}", flush=True)
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, "deadlock_injection.csv")
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("wrote", p)


if __name__ == "__main__":
    asyncio.run(main())
