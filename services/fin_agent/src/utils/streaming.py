"""
流式事件辅助工具
为 fin_api 的 SSE 接口和 fin_agent 的执行链路提供统一的事件发送能力。
"""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Dict, Optional

from src.utils.execution_logger import get_execution_logger

EventSink = Optional[Callable[[str, Dict[str, Any]], Awaitable[None] | None]]


def get_event_sink(metadata: Optional[Dict[str, Any]]) -> EventSink:
    if not metadata:
        return None
    sink = metadata.get("event_sink")
    return sink if callable(sink) else None


async def emit_event(
    sink: EventSink,
    event_type: str,
    payload: Dict[str, Any],
    *,
    trace_agent: Optional[str] = None,
) -> None:
    """
    向流式接口发送事件，同时写入轻量 trace 日志。
    """
    execution_logger = get_execution_logger()
    if execution_logger and trace_agent:
        execution_logger.log_agent_trace(
            trace_agent,
            "stream_event",
            {"event": event_type, "payload": payload},
        )

    if not sink:
        return

    result = sink(event_type, payload)
    if inspect.isawaitable(result):
        await result

