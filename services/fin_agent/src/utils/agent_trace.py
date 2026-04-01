"""
Agent链路追踪辅助工具
用于提炼ReAct响应中的关键证据，帮助判断是否真正触发了工具调用。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, ToolMessage


PSEUDO_TOOL_PATTERNS = [
    r'"name"\s*:\s*"[^"]+"',
    r'tool\s*=\s*"[^"]+"',
    r'get_[a-zA-Z0-9_]+\s*\(',
]


def _content_preview(content: Any, limit: int = 400) -> str:
    text = str(content or "")
    text = text.replace("\n", "\\n")
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def summarize_react_messages(messages: List[Any]) -> Dict[str, Any]:
    """提取ReAct消息序列中的关键信息。"""
    summary: List[Dict[str, Any]] = []
    ai_tool_call_count = 0
    tool_message_count = 0
    pseudo_tool_signal_count = 0

    for idx, message in enumerate(messages):
        entry: Dict[str, Any] = {
            "index": idx,
            "type": type(message).__name__,
        }

        content = getattr(message, "content", "")
        if content:
            entry["content_preview"] = _content_preview(content)

        if isinstance(message, AIMessage):
            tool_calls = getattr(message, "tool_calls", None) or []
            invalid_tool_calls = getattr(message, "invalid_tool_calls", None) or []
            entry["tool_call_count"] = len(tool_calls)
            if tool_calls:
                entry["tool_calls"] = tool_calls
                ai_tool_call_count += len(tool_calls)
            if invalid_tool_calls:
                entry["invalid_tool_calls"] = invalid_tool_calls

            content_text = str(content or "")
            pseudo_hits = [
                pattern for pattern in PSEUDO_TOOL_PATTERNS
                if re.search(pattern, content_text)
            ]
            if pseudo_hits:
                entry["pseudo_tool_patterns"] = pseudo_hits
                pseudo_tool_signal_count += 1

        if isinstance(message, ToolMessage):
            tool_message_count += 1
            entry["tool_name"] = getattr(message, "name", None)
            entry["tool_call_id"] = getattr(message, "tool_call_id", None)

        summary.append(entry)

    return {
        "message_count": len(messages),
        "ai_tool_call_count": ai_tool_call_count,
        "tool_message_count": tool_message_count,
        "pseudo_tool_signal_count": pseudo_tool_signal_count,
        "messages": summary,
    }


def summarize_request_context(
    agent_input: str,
    model_config: Dict[str, Any],
    tool_names: List[str],
) -> Dict[str, Any]:
    """记录发起 ReAct 调用前的轻量上下文。"""
    return {
        "input_length": len(agent_input or ""),
        "input_preview": _content_preview(agent_input, 600),
        "tool_count": len(tool_names),
        "tool_names": tool_names,
        "model_config": model_config,
    }


def summarize_exception(
    error: Exception,
    stage: str,
    model_config: Dict[str, Any] | None = None,
    tool_names: List[str] | None = None,
    agent_input: str | None = None,
) -> Dict[str, Any]:
    """记录关键异常信息，便于区分模型层和工具层问题。"""
    return {
        "stage": stage,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "tool_count": len(tool_names or []),
        "tool_names": tool_names or [],
        "input_length": len(agent_input or ""),
        "input_preview": _content_preview(agent_input or "", 300),
        "model_config": model_config or {},
    }
