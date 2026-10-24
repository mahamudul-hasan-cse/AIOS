# AIOS - AgentOS paper workspace (IEEE COMPSAC 2027)

Experiment harness, results, and LaTeX draft for the paper on **AgentOS**, an OS-inspired syscall
kernel for multi-agent LLM systems (code: https://github.com/mahamudul-hasan-cse/AgentOS).

| Folder | Contents |
|---|---|
| `paper_experiments/` | Baseline vs. AgentOS comparison, deadlock-injection experiment, analysis scripts |
| `results/` | First results (qwen2.5:1.5b, 12 tasks x 3 seeds), charts, CSVs, repo benchmarks |
| `paper/` | `main.tex` (IEEEtran) and `refs.bib` - draft, not yet compiled |
| `CLAUDE.md` | Step-by-step run instructions for Claude Code |

## Quick start
```
git clone https://github.com/mahamudul-hasan-cse/AIOS
cd AIOS
```
Open Claude Code in this folder and say: **"Read CLAUDE.md and run all the steps."**
It produces `results_laptop.zip`. See `paper_experiments/README.md` for metric definitions and caveats.
