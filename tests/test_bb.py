from factory.tools.bb import usage_from_log


def total(n: int) -> dict:
    return {"totalTokens": n, "inputTokens": n - 10, "cachedInputTokens": 0, "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0, "outputTokens": 8, "reasoningOutputTokens": 2}


def test_usage_is_the_last_token_report_with_turns_and_items_counted() -> None:
    events = [
        {"type": "turn/started", "data": {}},
        {"type": "item/completed", "data": {"item": {"type": "reasoning"}}},
        {"type": "item/completed", "data": {"item": {"type": "commandExecution"}}},
        {"type": "thread/tokenUsage/updated", "data": {"tokenUsage": {"total": total(100), "last": total(100)}}},
        {"type": "turn/completed", "data": {}},
        {"type": "item/completed", "data": {"item": {"type": "commandExecution"}}},
        {"type": "thread/tokenUsage/updated", "data": {"tokenUsage": {"total": total(250), "last": total(150)}}},
        {"type": "turn/completed", "data": {}},
    ]

    usage = usage_from_log(events)

    assert usage == {"turns": 2, "items": {"reasoning": 1, "commandExecution": 2},
                     "tokens": {"input": 240, "cached_input": 0, "output": 8, "reasoning": 2, "total": 250}}


def test_a_thread_without_a_token_report_has_no_tokens() -> None:
    usage = usage_from_log([{"type": "turn/completed", "data": {}}])

    assert usage == {"turns": 1, "items": {}, "tokens": {}}
