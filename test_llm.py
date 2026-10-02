from concurrent.futures import ThreadPoolExecutor

from llm import ask_llm, LLMError

try:
    text, model = ask_llm("You are a concise assistant.", "Say hello in 5 words")
    print("Reply:", text)
    print("Model used:", model)
except LLMError as e:
    print("FAILED:", e)
    raise SystemExit(1)

# Thread-safety check: 4 calls at once.
print("\n4 parallel calls...")
try:
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: ask_llm("Be concise.", f"Reply with only the number {i}"), range(4)))
    for i, (t, m) in enumerate(results):
        print(f"  {i}: {t!r} ({m})")
except LLMError as e:
    print("FAILED (parallel):", e)
    raise SystemExit(1)
