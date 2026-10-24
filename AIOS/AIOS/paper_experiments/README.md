# AgentOS paper experiments (COMPSAC 2027)

Harness for RQ1 (overhead vs. a no-kernel baseline) and RQ2 (safety under
contention). Lives OUTSIDE the AgentOS repo and does not modify it; it imports
the repo's real `kernel/` and `agents/` code.

## Files
| file | what it does |
|---|---|
| `tasks.py` | 12 fixed coding tasks, each with a checkable expected stdout (success = generated script prints it) |
| `llm.py` | Instrumented drivers: `OllamaInstrumented` (real model, logs driver ms + prompt/completion tokens) and `MockDriver` (DETERMINISTIC MOCK, not an LLM - for harness dev / overhead isolation only) |
| `baseline.py` | No-kernel baseline: same researcher -> coder(+refine) -> tester -> writer pipeline, same prompts, direct LLM calls, plain dict/files, same sandbox function |
| `run_comparison.py` | Runs `baseline`, `agentos_relaxed` (quotas 10/min, same call count as baseline) and `agentos_default` (repo's default quotas) over tasks x seeds; writes CSVs |
| `deadlock_experiment.py` | Contention injection on the real `ResourceManager` + `DeadlockDetector`: Banker's on / off + detection / off + nothing |
| `analyze.py` | `results/summary.md` tables and PNG plots |

## Reproduce on your laptop
```bash
git clone https://github.com/mahamudul-hasan-cse/AgentOS
cd AgentOS && python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest pandas tabulate
cd ..   # put paper_experiments/ next to AgentOS/  (or set AGENTOS_REPO=/path/to/AgentOS)
ollama pull qwen2.5:1.5b        # also try qwen2.5:3b and llama3.2:3b for a 2nd/3rd model
cd paper_experiments
python run_comparison.py --backend mock --seeds 3                                   # 1 min smoke test
python run_comparison.py --backend ollama --model qwen2.5:1.5b --seeds 5            # real run (~1.5 h on CPU)
python run_comparison.py --backend ollama --model qwen2.5:3b   --seeds 5
python deadlock_experiment.py --seeds 10
python analyze.py               # -> ../results/summary.md + *.png
```
Record your CPU, RAM, OS, GPU (if any), Ollama version and model quantization
(`ollama show qwen2.5:1.5b`) in the paper's setup section.

## Metric definitions
* `wall_ms` - end-to-end time for one task through the 4-agent pipeline.
* `per_call_latency_ms_mean` - mean driver time per LLM call (measured inside the driver).
* `prompt_tokens` / `completion_tokens` - from Ollama's `prompt_eval_count` / `eval_count` (mock: whitespace tokens).
* `kernel_overhead_ms` - sum of dispatcher `latency_ms` over all syscalls in the run, minus LLM driver time, minus sandbox execution time. Baseline = 0 by construction.
* `quota_exceeded` - syscalls that returned QUOTA_EXCEEDED (the default quota denies the coder's refine call).
* `success` - generated script's stdout contains the task's expected value.
* Deadlock experiment: N agents, pool capacity C=6, each needs K=3 slots acquired one at a time (hold-and-wait). `stalled` = no progress for 2 s.

## Honest caveats (put these in Threats to Validity)
* Pipeline stages are sequential, so pipeline-level runs never deadlock; RQ2 uses the injection harness on the real allocator/detector with a synthetic agent loop.
* The pipeline does not use MEM_* syscalls, so memory hits are not reported here (RQ3 uses memory_bench).
* Temperature is 0.7 with a fixed Ollama seed per run; LLM output is still nondeterministic across hardware.
* SemanticFS uses the offline hashing embedder (as in the test suite); real Ollama embeddings would add FILE_WRITE latency.
