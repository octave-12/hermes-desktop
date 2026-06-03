"""
Smart Context Manager for long conversations.

Strategies:
1. Sliding window: keep recent N messages in full
2. Auto-summarization: older messages compressed into summary via LLM
3. Token-aware: estimate token count, respect model context limits
4. Summary persistence: DB-backed cache to avoid re-summarizing
"""
import json
import re
from typing import Optional

# ~4 chars per token for mixed CJK/English content (conservative estimate)
CHARS_PER_TOKEN = 3.5

# Defaults
DEFAULT_MAX_CONTEXT_TOKENS = 100_000  # Leave room for system prompt + response
RECENT_MESSAGE_WINDOW = 30           # Keep last 30 messages in full
SUMMARY_TRIGGER_COUNT = 50           # Start summarizing when total > 50 messages
SUMMARY_MAX_TOKENS = 2000            # Summary cap


def estimate_tokens(text: str) -> int:
    """Rough token count estimate. Good enough for context management."""
    if not text:
        return 0
    cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
    ascii_chars = len(text) - cjk
    return int(cjk * 1.5 + ascii_chars / 4)


def build_smart_history(
    messages: list[dict],
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    recent_window: int = RECENT_MESSAGE_WINDOW,
) -> tuple[list[dict], list[dict]]:
    """
    Build conversation history with intelligent pruning.

    Returns:
        (kept_messages, dropped_messages)
        - kept_messages: the messages that fit in context (for LLM history)
        - dropped_messages: the messages that were pruned (for summarization)
    """
    if not messages:
        return [], []

    # Filter to user/assistant only
    filtered = [m for m in messages if m.get("role") in ("user", "assistant")]

    if not filtered:
        return [], []

    # Small session — return everything, nothing dropped
    if len(filtered) <= recent_window:
        kept = [{"role": m["role"], "content": m["content"]} for m in filtered]
        return kept, []

    # Large session — apply sliding window
    recent = filtered[-recent_window:]
    recent_tokens = sum(estimate_tokens(m["content"]) for m in recent)

    if recent_tokens > max_context_tokens:
        # Even recent window is too large — trim from the front
        trimmed = _fit_to_token_budget(recent, max_context_tokens)
        dropped = [m for m in filtered if m not in trimmed]
        kept = [{"role": m["role"], "content": m["content"]} for m in trimmed]
        return kept, dropped

    # Budget remaining after recent messages — fill with older messages
    remaining_tokens = max_context_tokens - recent_tokens
    older = filtered[:-recent_window]
    older_kept = _fit_to_token_budget_reversed(older, remaining_tokens)

    # Dropped = older messages that didn't fit
    older_kept_ids = {id(m) for m in older_kept}
    dropped = [m for m in older if id(m) not in older_kept_ids]

    result = older_kept + recent
    kept = [{"role": m["role"], "content": m["content"]} for m in result]
    return kept, dropped


def build_summary_prompt(dropped_messages: list[dict]) -> str:
    """Build a prompt for LLM to summarize dropped messages."""
    # Format messages as conversation transcript
    lines = []
    for msg in dropped_messages:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:500]  # Truncate very long messages
        lines.append(f"{role}: {content}")

    transcript = "\n".join(lines)

    return f"""请用中文简洁地总结以下对话的关键信息。要求：
1. 保留重要的技术细节、决定、承诺、名字、数字
2. 保留未完成的任务或待跟进的事项
3. 压缩到200字以内
4. 输出纯文本，不要markdown格式

对话记录：
{transcript}

总结："""


def extract_summary_from_response(response: str) -> str:
    """Clean up LLM summary response — strip thinking tags, whitespace."""
    # Remove  blocks
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    # Remove <think>...</think> blocks (incomplete)
    response = re.sub(r'<think>.*', '', response, flags=re.DOTALL)
    # Strip whitespace
    response = response.strip()
    # Limit length
    if len(response) > 1000:
        response = response[:1000] + "..."
    return response


def inject_summary(history: list[dict], summary_text: str) -> list[dict]:
    """Inject a summary message at the beginning of conversation history."""
    if not summary_text:
        return history

    summary_msg = {
        "role": "system",
        "content": f"[以下是对之前对话的总结]\n{summary_text}"
    }
    return [summary_msg] + history


def build_context_stats(original_messages: list[dict], kept_count: int,
                        has_summary: bool = False) -> dict:
    """Build stats dict for WS notification."""
    filtered = [m for m in original_messages if m.get("role") in ("user", "assistant")]
    total_tokens = sum(estimate_tokens(m["content"]) for m in filtered)
    dropped = len(filtered) - kept_count

    return {
        "total_messages": len(filtered),
        "estimated_tokens": total_tokens,
        "needs_pruning": len(filtered) > RECENT_MESSAGE_WINDOW,
        "kept_messages": kept_count,
        "dropped_messages": dropped,
        "has_summary": has_summary,
    }


# ── Internal helpers ──────────────────────────────────────────

def _fit_to_token_budget(messages: list[dict], max_tokens: int) -> list[dict]:
    """Keep messages from the END that fit within token budget.
    Always returns at least the last message."""
    if not messages:
        return []
    result = []
    tokens_used = 0
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg["content"])
        if tokens_used + msg_tokens > max_tokens and result:
            break
        result.append(msg)
        tokens_used += msg_tokens
    result.reverse()
    return result


def _fit_to_token_budget_reversed(messages: list[dict], max_tokens: int) -> list[dict]:
    """Keep messages from the END (newest first) that fit within token budget."""
    result = []
    tokens_used = 0
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg["content"])
        if tokens_used + msg_tokens > max_tokens:
            break
        result.append(msg)
        tokens_used += msg_tokens
    result.reverse()
    return result
