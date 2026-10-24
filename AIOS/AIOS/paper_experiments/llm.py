"""LLM drivers shared by AgentOS and the baseline, with per-call instrumentation.

Both drivers register under the name "ollama" so the AgentOS dispatcher never
falls back to another provider. Every generate() call appends a record to
CALLS: driver wall time (ms), prompt/completion tokens, and the seed.

- OllamaInstrumented: real local model via Ollama's /api/generate.
- MockDriver: deterministic, offline, clearly labelled. Returns correct code
  for the known task set, simulates latency, and counts whitespace tokens.
  Use it ONLY for harness development / kernel-overhead isolation, never as
  evidence about LLM quality.
"""
import asyncio, hashlib, os, re, time
import requests
from kernel.drivers.base import LLMDriver, DriverConnectionError, DriverError

CALLS = []          # appended per generate()
CONFIG = {"model": os.environ.get("AGENTOS_EXP_MODEL", "qwen2.5:1.5b"),
          "host": os.environ.get("AGENTOS_OLLAMA_HOST", "http://localhost:11434"),
          "seed": 0, "num_predict": 384, "mock_latency_ms": 40.0}


class OllamaInstrumented(LLMDriver):
    name = "ollama"

    def is_available(self):
        try:
            return requests.get(f"{CONFIG['host']}/api/tags", timeout=2).ok
        except requests.RequestException:
            return False

    async def generate(self, prompt, **kw):
        t0 = time.perf_counter()
        body = {"model": CONFIG["model"], "prompt": prompt, "stream": False,
                "options": {"seed": CONFIG["seed"], "temperature": 0.7,
                            "num_predict": CONFIG["num_predict"]}}
        try:
            r = await asyncio.to_thread(requests.post, f"{CONFIG['host']}/api/generate", json=body, timeout=300)
        except requests.RequestException as e:
            raise DriverConnectionError(str(e)) from e
        if not r.ok:
            raise DriverError(f"ollama {r.status_code}: {r.text[:200]}")
        j = r.json()
        CALLS.append({"driver_ms": (time.perf_counter() - t0) * 1000, "prompt_tokens": j.get("prompt_eval_count", 0),
                      "completion_tokens": j.get("eval_count", 0), "seed": CONFIG["seed"]})
        return j["response"]


_SOLUTIONS = {
    "sum of the integers from 1 to 100": "print(sum(range(1, 101)))",
    "20th Fibonacci": "a, b = 1, 1\nfor _ in range(18):\n    a, b = b, a + b\nprint(b)",
    "factorial of 10": "import math\nprint(math.factorial(10))",
    "prime numbers are below 100": "print(sum(1 for n in range(2, 100) if all(n % d for d in range(2, int(n**0.5) + 1))))",
    "reverses the string": "print('agentos'[::-1])",
    "greatest common divisor": "import math\nprint(math.gcd(462, 1071))",
    "counts the vowels": "print(sum(c in 'aeiou' for c in 'operating systems govern agents'))",
    "sorted in ascending": "print(sorted([5, 3, 9, 1, 7]))",
    "sum of the squares": "print(sum(i * i for i in range(1, 11)))",
    "binary representation of 37": "print(bin(37)[2:])",
    "palindrome": "s = 'racecar'\nprint(s == s[::-1])",
    "largest number": "print(max([12, 45, 7, 89, 23]))",
}


class MockDriver(LLMDriver):
    """DETERMINISTIC MOCK - not a language model."""
    name = "ollama"

    def is_available(self):
        return True

    async def generate(self, prompt, **kw):
        t0 = time.perf_counter()
        h = int(hashlib.sha256(f"{CONFIG['seed']}|{prompt}".encode()).hexdigest()[:8], 16)
        await asyncio.sleep(CONFIG["mock_latency_ms"] * (0.75 + 0.5 * (h % 1000) / 1000) / 1000)
        if "Generate a complete, runnable Python 3 script" in prompt or "Review the generated Python" in prompt:
            code = next((c for k, c in _SOLUTIONS.items() if k in prompt), None)
            if code is None:  # refine call: echo the code it was given
                m = re.search(r"```python\n(.*?)```", prompt, re.S)
                code = m.group(1).strip() if m else "print('ok')"
            out = f"```python\n{code}\n```"
        elif "Research this implementation task" in prompt:
            out = "- Use the standard library only.\n- Print exactly one result line.\n- Keep it deterministic."
        else:
            out = "Pipeline report: research done, code generated, test executed."
        CALLS.append({"driver_ms": (time.perf_counter() - t0) * 1000, "prompt_tokens": len(prompt.split()),
                      "completion_tokens": len(out.split()), "seed": CONFIG["seed"]})
        return out


def get_driver(backend):
    return {"ollama": OllamaInstrumented, "mock": MockDriver}[backend]
