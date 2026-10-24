"""NO-KERNEL BASELINE: the same researcher -> coder -> tester -> writer pipeline,
with the same prompts (copied verbatim from agents/pipeline.py), calling the
LLM driver directly. No dispatcher, no syscalls, no ACL, no quotas, no Banker's
resource pools, no deadlock detection, no paging, no semantic FS: hand-offs are
a plain dict and plain files. Code is executed with the same
kernel.sandbox.run_python_sandbox function so execution cost is identical.
"""
import asyncio, os, tempfile, time, uuid
from agents.pipeline import extract_python_code
from kernel.sandbox import run_python_sandbox


async def run_baseline(topic, driver_cls, refine=True):
    d = driver_cls()
    board, out_dir = {}, tempfile.mkdtemp(prefix="baseline_")
    run_id = "baseline_" + uuid.uuid4().hex[:8]
    llm_calls = 0

    async def llm(p):
        nonlocal llm_calls
        llm_calls += 1
        return await d.generate(p)

    board["research"] = await llm(
        f"Research this implementation task and return concise findings that a coder "
        f"can act on.\n\nTask:\n{topic}\n\nReturn 4-6 bullets.")
    code_text = await llm(
        "Generate a complete, runnable Python 3 script for the task below. "
        "Keep it self-contained, deterministic, and safe for an offline subprocess. "
        "Return only the code or one fenced python code block.\n\n"
        f"Task:\n{topic}\n\nResearch findings:\n{board['research']}")
    if refine:
        code_text = await llm(
            "Review the generated Python once for obvious syntax/runtime issues. "
            "If changes are needed, return the full corrected code; otherwise return the same code.\n\n"
            f"{code_text}")
    code = extract_python_code(code_text)
    path = os.path.join(out_dir, f"{run_id}_generated.py")
    open(path, "w").write(code)
    t0 = time.perf_counter()
    test = await asyncio.to_thread(run_python_sandbox, open(path).read(), 3.0)
    sandbox_ms = (time.perf_counter() - t0) * 1000
    board["test"] = test
    report = await llm(
        "Write a final human-readable summary report for this multi-agent pipeline run. "
        "Be concise and include research, generated code artifact, test pass/fail, and any quota events.\n\n"
        f"Task: {topic}\n\nResearch:\n{board['research']}\n\nCode artifact:\n{ {'filename': path, 'code': code} }\n\nTest result:\n{test}")
    open(os.path.join(out_dir, f"{run_id}_report.md"), "w").write(report)
    return {"status": "completed", "stdout": test.get("stdout", ""), "passed_exec": bool(test.get("passed")),
            "llm_calls": llm_calls, "sandbox_ms": sandbox_ms}
