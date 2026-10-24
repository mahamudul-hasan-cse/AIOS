# Instructions for Claude Code

Goal: run the AgentOS paper experiments on this laptop and produce `results_laptop.zip`.
Work from the root of this repository. Do NOT edit files in `paper_experiments/` or in `AgentOS/`, and do NOT push to any git remote.
If a step fails, stop, show the full error to the user, and ask before changing code.
Use the macOS/Linux commands or the Windows (PowerShell) commands, depending on the OS you detect.

## Step 1 - Check prerequisites
```
python --version        # must be 3.10 or newer (on macOS/Linux try python3 if python is missing)
ollama --version        # if missing: install it from https://ollama.com/download and start the Ollama app
git --version
```

## Step 2 - Pull the models
```
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
ollama list             # both models must appear
```

## Step 3 - Clone AgentOS next to the harness and install
The harness expects `AgentOS/` inside this repo's root (it is git-ignored).
macOS/Linux:
```
git clone https://github.com/mahamudul-hasan-cse/AgentOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r AgentOS/requirements.txt -r requirements.txt
```
Windows (PowerShell):
```
git clone https://github.com/mahamudul-hasan-cse/AgentOS
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r AgentOS\requirements.txt -r requirements.txt
```
Keep the venv active for all later steps.

## Step 4 - Run the experiments (output goes to results_laptop/)
Smoke test first (about 1 minute, mock LLM - not real data):
```
python paper_experiments/run_comparison.py --backend mock --seeds 1 --out results_laptop/smoke
```
Real runs (about 1-2 h each on CPU; let them finish):
```
python paper_experiments/run_comparison.py --backend ollama --model qwen2.5:1.5b --seeds 5 --out results_laptop
python paper_experiments/run_comparison.py --backend ollama --model qwen2.5:3b --seeds 5 --out results_laptop
python paper_experiments/deadlock_experiment.py --seeds 10 --out results_laptop
python paper_experiments/analyze.py results_laptop
```
`analyze.py` writes `results_laptop/summary.md` and PNG charts.

## Step 5 - Record hardware into results_laptop/hardware.txt
macOS:
```
{ sw_vers; sysctl -n machdep.cpu.brand_string; sysctl -n hw.memsize; system_profiler SPDisplaysDataType | grep -E "Chipset|VRAM"; ollama --version; python3 --version; ollama show qwen2.5:1.5b; ollama show qwen2.5:3b; } > results_laptop/hardware.txt 2>&1
```
Linux:
```
{ uname -a; cat /etc/os-release; lscpu | grep -E "Model name|^CPU\(s\)"; free -h; nvidia-smi || lspci | grep -iE "vga|3d"; ollama --version; python3 --version; ollama show qwen2.5:1.5b; ollama show qwen2.5:3b; } > results_laptop/hardware.txt 2>&1
```
Windows (PowerShell):
```
& { Get-CimInstance Win32_OperatingSystem | Select Caption,Version; Get-CimInstance Win32_Processor | Select Name,NumberOfCores,NumberOfLogicalProcessors; "RAM GB: " + [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1); Get-CimInstance Win32_VideoController | Select Name,AdapterRAM; ollama --version; python --version; ollama show qwen2.5:1.5b; ollama show qwen2.5:3b } *> results_laptop\hardware.txt
```

## Step 6 - Capture 5 live AgentOS sessions (real memory/scheduler data)
AgentOS has a built-in capture tool: `benchmarks/real_data_export.py --capture`. It runs the real
pipeline + assistant against a live kernel and writes a JSON workload of real syscalls.
First give the kernel an Ollama config (this file is git-ignored in AgentOS):
macOS/Linux:
```
cp AgentOS/kernel/config.yaml.example AgentOS/kernel/config.yaml
```
Windows:
```
Copy-Item AgentOS\kernel\config.yaml.example AgentOS\kernel\config.yaml
```
Then edit `AgentOS/kernel/config.yaml`: under `ollama:` set `model: "qwen2.5:1.5b"`, and under
`embeddings:` set `backend: "hashing"` (or run `ollama pull nomic-embed-text` and keep `ollama`).
Run 5 captures from inside `AgentOS/` (3 sequential, 2 concurrent):
macOS/Linux:
```
cd AgentOS
mkdir -p ../results_laptop/sessions
python -m benchmarks.real_data_export --capture --driver ollama --output ../results_laptop/sessions/session_1.json
python -m benchmarks.real_data_export --capture --driver ollama --output ../results_laptop/sessions/session_2.json
python -m benchmarks.real_data_export --capture --driver ollama --output ../results_laptop/sessions/session_3.json
python -m benchmarks.real_data_export --capture --driver ollama --concurrent --output ../results_laptop/sessions/session_4_concurrent.json
python -m benchmarks.real_data_export --capture --driver ollama --concurrent --output ../results_laptop/sessions/session_5_concurrent.json
cd ..
```
Windows: same commands, but create the folder with `New-Item -ItemType Directory -Force ..\results_laptop\sessions` and use `..\results_laptop\sessions\...` paths.
Each run prints a summary; save the terminal output too if possible.

## Step 7 - Zip and hand back
macOS/Linux:
```
zip -r results_laptop.zip results_laptop
```
Windows:
```
Compress-Archive -Path results_laptop -DestinationPath results_laptop.zip -Force
```
Tell the user: "Done. Send results_laptop.zip to Grok Bot in chat." Never commit or push the results.
