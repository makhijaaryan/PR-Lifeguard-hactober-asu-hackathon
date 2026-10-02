from llm import ask_llm, LLMError

try:
    text, model = ask_llm("You are a concise assistant.", "Say hello in 5 words")
    print("Reply:", text)
    print("Model used:", model)
except LLMError as e:
    print("FAILED:", e)
    raise SystemExit(1)
