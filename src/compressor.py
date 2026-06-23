import re


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def compress_conversation(messages: list[dict], max_tokens: int = 4000) -> list[dict]:
    if not messages:
        return messages

    total_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
    if total_tokens <= max_tokens:
        return messages

    compressed = []
    kept_tokens = 0

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    for sm in system_messages:
        compressed.append(sm)
        kept_tokens += estimate_tokens(sm.get("content", ""))

    last_few = non_system[-4:] if len(non_system) > 4 else non_system
    last_tokens = sum(estimate_tokens(m.get("content", "")) for m in last_few)

    remaining_budget = max_tokens - kept_tokens - last_tokens

    if remaining_budget <= 0:
        return system_messages + last_few

    earlier = non_system[:-4] if len(non_system) > 4 else []
    compressed_earlier = _compress_messages(earlier, remaining_budget)

    return compressed + compressed_earlier + last_few


def _compress_messages(messages: list[dict], budget: int) -> list[dict]:
    if not messages or budget <= 0:
        return []
    total = sum(estimate_tokens(m.get("content", "")) for m in messages)
    if total <= budget:
        return messages
    merged_content = ""
    for m in messages:
        text = m.get("content", "")
        merged_content += f"[{m.get('role', 'user')}]: {text}\n"
    compressed_text = _summarize_text(merged_content, budget)
    return [{"role": "system", "content": f"Earlier conversation summary: {compressed_text}"}]


def _summarize_text(text: str, max_tokens: int) -> str:
    target_chars = max_tokens * 4
    if len(text) <= target_chars:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    char_count = 0
    for s in sentences:
        if char_count + len(s) > target_chars:
            if result:
                break
            result.append(s[:target_chars])
            break
        result.append(s)
        char_count += len(s)
    summary = " ".join(result)
    if len(summary) < len(text):
        summary += " [...]"
    return summary


def optimize_prompt(prompt: str) -> str:
    original = prompt
    prompt = re.sub(r"\s+", " ", prompt).strip()
    prompt = re.sub(r"\n{3,}", "\n\n", prompt)
    prompt = re.sub(r"#{4,}", "###", prompt)
    prompt = re.sub(r"<!--.*?-->", "", prompt)
    lines = prompt.split("\n")
    optimized = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("---") or stripped.startswith("___"):
            continue
        optimized.append(line)
    result = "\n".join(optimized)
    saved = len(original) - len(result)
    if saved > 100:
        result = "\n\n".join(
            f"<optimized>{result}</optimized>"
        )
    return result
