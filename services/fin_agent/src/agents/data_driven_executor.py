"""
轻量级数据驱动分析执行器。

核心目标：
1. 由代码负责 MCP 工具调用，避免依赖模型自动 tool calling。
2. 保留现有 Agent 工作流、状态结构和日志体系。
3. 让新增 Agent / 新市场后续只需补 profile 和 tool step。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.tools.mcp_client import get_mcp_tools, select_mcp_tools_by_name
from src.utils.agent_trace import summarize_exception, summarize_request_context
from src.utils.execution_logger import get_execution_logger
from src.utils.state_definition import AgentState
from src.utils.streaming import emit_event, get_event_sink

load_dotenv(override=True)

ToolArgsBuilder = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]


@dataclass(frozen=True)
class ToolStep:
    name: str
    label: str
    args_builder: ToolArgsBuilder
    required: bool = True


@dataclass(frozen=True)
class AnalysisProfile:
    agent_name: str
    analysis_key: str
    error_key: str
    metadata_prefix: str
    completion_message: str
    summary_title: str
    summary_objective: str
    summary_requirements: Sequence[str]
    allowed_tools: Sequence[str]
    tool_steps: Sequence[ToolStep]
    temperature: float = 0.3
    max_tokens: int = 1024


def get_reference_date(current_data: Dict[str, Any]) -> datetime:
    current_date = current_data.get("current_date")
    if current_date:
        try:
            return datetime.strptime(current_date, "%Y-%m-%d")
        except ValueError:
            pass
    analysis_timestamp = current_data.get("analysis_timestamp")
    if analysis_timestamp:
        try:
            return datetime.fromisoformat(analysis_timestamp)
        except ValueError:
            pass
    return datetime.now()


def get_recent_date_range(current_data: Dict[str, Any], days: int) -> Dict[str, str]:
    end_date = get_reference_date(current_data)
    start_date = end_date - timedelta(days=days)
    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }


def get_previous_completed_quarter(current_data: Dict[str, Any]) -> Dict[str, int]:
    ref = get_reference_date(current_data)
    year = ref.year
    month = ref.month

    if month <= 3:
        return {"year": year - 1, "quarter": 3}
    if month <= 4:
        return {"year": year - 1, "quarter": 4}
    if month <= 7:
        return {"year": year, "quarter": 1}
    if month <= 10:
        return {"year": year, "quarter": 2}
    return {"year": year, "quarter": 3}


def build_stock_query(current_data: Dict[str, Any]) -> str:
    company_name = current_data.get("company_name")
    stock_code = current_data.get("stock_code")
    if company_name and stock_code:
        return f"{company_name} {stock_code}"
    return company_name or stock_code or current_data.get("query", "")


def compact_text(value: Any, limit: int = 1200) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def summarize_tool_results(tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "result_count": len(tool_results),
        "success_count": sum(1 for item in tool_results if item["status"] == "success"),
        "error_count": sum(1 for item in tool_results if item["status"] == "error"),
        "results": [
            {
                "label": item["label"],
                "tool_name": item["tool_name"],
                "status": item["status"],
                "args": item["args"],
                "duration_seconds": item["duration_seconds"],
                "output_preview": compact_text(item.get("output"), 300),
                "error": item.get("error"),
            }
            for item in tool_results
        ],
    }


def build_summary_prompt(
    profile: AnalysisProfile,
    current_data: Dict[str, Any],
    tool_results: List[Dict[str, Any]],
) -> str:
    company_name = current_data.get("company_name", "未知公司")
    stock_code = current_data.get("stock_code", "未知代码")
    current_time_info = current_data.get("current_time_info", "未知时间")

    sections: List[str] = []
    for result in tool_results:
        header = f"### {result['label']} ({result['tool_name']})"
        if result["status"] == "success":
            body = compact_text(result.get("output"), 1200) or "工具返回为空。"
        else:
            body = f"工具执行失败：{result.get('error', '未知错误')}"
        sections.append(f"{header}\n参数：{result['args']}\n结果：\n{body}")

    data_block = "\n\n".join(sections) if sections else "没有获取到任何有效数据。"
    requirements = "\n".join(
        f"{index}. {item}" for index, item in enumerate(profile.summary_requirements, start=1)
    )

    return f"""你是{profile.summary_title}，只能依据“已获取的数据”进行分析。

目标股票：{company_name}（{stock_code}）
当前时间：{current_time_info}

分析目标：
{profile.summary_objective}

输出要求：
{requirements}

硬性约束：
- 只能依据下方“已获取的数据”得出结论。
- 如果某项数据缺失或执行失败，必须明确说明“该项数据未获取到”。
- 严禁补造数字、新闻、交易信号、事件或公司信息。
- 不要输出工具调用计划，也不要假设你还能继续取数。

已获取的数据：
{data_block}
"""


async def run_data_driven_analysis(
    state: AgentState,
    profile: AnalysisProfile,
    logger,
) -> AgentState:
    execution_logger = get_execution_logger()
    current_data = state.get("data", {})
    current_messages = state.get("messages", [])
    current_metadata = state.get("metadata", {})
    user_query = current_data.get("query")
    event_sink = get_event_sink(current_metadata)

    execution_logger.log_agent_start(
        profile.agent_name,
        {
            "user_query": user_query,
            "stock_code": current_data.get("stock_code"),
            "company_name": current_data.get("company_name"),
            "input_data_keys": list(current_data.keys()),
        },
    )
    await emit_event(
        event_sink,
        "progress",
        {
            "stage": profile.metadata_prefix,
            "status": "started",
            "message": f"{profile.summary_title}开始取数分析",
            "agent": profile.agent_name,
        },
        trace_agent=profile.agent_name,
    )

    if not user_query:
        current_data[profile.error_key] = "User query is missing."
        execution_logger.log_agent_complete(
            profile.agent_name, current_data, 0, False, "User query is missing"
        )
        return {
            "data": current_data,
            "messages": current_messages,
            "metadata": current_metadata,
        }

    agent_start_time = time.time()
    model_config: Dict[str, Any] = {}
    tool_names: List[str] = []
    summary_prompt = ""

    try:
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        model_name = os.getenv("OPENAI_COMPATIBLE_MODEL")

        if not all([api_key, base_url, model_name]):
            raise RuntimeError("Missing OpenAI environment variables.")

        model_config = {
            "model": model_name,
            "temperature": profile.temperature,
            "max_tokens": profile.max_tokens,
            "api_base": base_url,
        }
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
        )

        mcp_tools = await get_mcp_tools()
        if not mcp_tools:
            raise RuntimeError("No MCP tools available.")

        selected_tools = select_mcp_tools_by_name(mcp_tools, profile.allowed_tools)
        if not selected_tools:
            raise RuntimeError("Filtered MCP tools are empty.")

        tool_names = [tool.name for tool in selected_tools]
        execution_logger.log_agent_trace(
            profile.agent_name,
            "tool_catalog",
            {"tool_count": len(tool_names), "tool_names": tool_names},
        )

        tool_map = {tool.name: tool for tool in selected_tools}
        plan_trace = []
        tool_results: List[Dict[str, Any]] = []

        for step in profile.tool_steps:
            args = step.args_builder(current_data)
            plan_trace.append(
                {
                    "tool_name": step.name,
                    "label": step.label,
                    "required": step.required,
                    "args": args,
                }
            )

            if not args:
                tool_results.append(
                    {
                        "tool_name": step.name,
                        "label": step.label,
                        "args": args,
                        "status": "skipped",
                        "output": "",
                        "error": "No arguments generated.",
                        "duration_seconds": 0.0,
                    }
                )
                continue

            tool = tool_map.get(step.name)
            if not tool:
                error = f"Tool not available: {step.name}"
                tool_results.append(
                    {
                        "tool_name": step.name,
                        "label": step.label,
                        "args": args,
                        "status": "error",
                        "output": "",
                        "error": error,
                        "duration_seconds": 0.0,
                    }
                )
                continue

            start_time = time.time()
            try:
                output = await tool.ainvoke(args)
                duration = time.time() - start_time
                execution_logger.log_tool_usage(
                    profile.agent_name,
                    step.name,
                    args,
                    output,
                    duration,
                    True,
                    None,
                )
                tool_results.append(
                    {
                        "tool_name": step.name,
                        "label": step.label,
                        "args": args,
                        "status": "success",
                        "output": str(output),
                        "error": None,
                        "duration_seconds": duration,
                    }
                )
            except Exception as exc:
                duration = time.time() - start_time
                execution_logger.log_tool_usage(
                    profile.agent_name,
                    step.name,
                    args,
                    "",
                    duration,
                    False,
                    str(exc),
                )
                tool_results.append(
                    {
                        "tool_name": step.name,
                        "label": step.label,
                        "args": args,
                        "status": "error",
                        "output": "",
                        "error": str(exc),
                        "duration_seconds": duration,
                    }
                )

        execution_logger.log_agent_trace(
            profile.agent_name,
            "tool_plan",
            {"steps": plan_trace},
        )
        await emit_event(
            event_sink,
            "progress",
            {
                "stage": profile.metadata_prefix,
                "status": "tool_fetch_completed",
                "message": f"{profile.summary_title}完成工具取数",
                "agent": profile.agent_name,
                "successful_tools": sum(1 for item in tool_results if item["status"] == "success"),
                "total_tools": len(tool_results),
            },
            trace_agent=profile.agent_name,
        )
        execution_logger.log_agent_trace(
            profile.agent_name,
            "tool_results",
            summarize_tool_results(tool_results),
        )

        summary_prompt = build_summary_prompt(profile, current_data, tool_results)
        execution_logger.log_agent_trace(
            profile.agent_name,
            "request_context",
            summarize_request_context(summary_prompt, model_config, tool_names),
        )

        llm_start = time.time()
        response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        llm_duration = time.time() - llm_start
        final_output = str(response.content or "").strip() or "未生成分析结果。"

        execution_logger.log_llm_interaction(
            agent_name=profile.agent_name,
            interaction_type="data_driven_summary",
            input_messages=[{"role": "user", "content": summary_prompt}],
            output_content=final_output,
            model_config=model_config,
            execution_time=llm_duration,
        )

        current_data[profile.analysis_key] = final_output
        current_metadata[f"{profile.metadata_prefix}_executed"] = True
        current_metadata[f"{profile.metadata_prefix}_timestamp"] = str(time.time())
        current_metadata[f"{profile.metadata_prefix}_execution_time"] = (
            f"{time.time() - agent_start_time:.2f} seconds"
        )

        updated_messages = current_messages + [
            {"role": "assistant", "content": profile.completion_message}
        ]

        total_execution_time = time.time() - agent_start_time
        execution_logger.log_agent_complete(
            profile.agent_name,
            {
                f"{profile.analysis_key}_length": len(final_output),
                "analysis_preview": final_output[:500] if len(final_output) > 500 else final_output,
                "total_execution_time": total_execution_time,
                "successful_tools": sum(
                    1 for item in tool_results if item["status"] == "success"
                ),
            },
            total_execution_time,
            True,
        )
        await emit_event(
            event_sink,
            "progress",
            {
                "stage": profile.metadata_prefix,
                "status": "completed",
                "message": profile.completion_message,
                "agent": profile.agent_name,
                "successful_tools": sum(
                    1 for item in tool_results if item["status"] == "success"
                ),
            },
            trace_agent=profile.agent_name,
        )

        logger.info("%s finished successfully with %s successful tool calls.", profile.agent_name, sum(
            1 for item in tool_results if item["status"] == "success"
        ))
        return {
            "data": current_data,
            "messages": updated_messages,
            "metadata": current_metadata,
        }

    except Exception as exc:
        logger.error("%s failed: %s", profile.agent_name, exc, exc_info=True)
        execution_logger.log_agent_trace(
            profile.agent_name,
            "agent_error",
            summarize_exception(
                exc,
                stage="data_driven_execution",
                model_config=model_config,
                tool_names=tool_names,
                agent_input=summary_prompt,
            ),
        )
        current_data[profile.error_key] = str(exc)
        current_data[profile.analysis_key] = f"{profile.summary_title}过程中出现错误: {exc}"
        current_metadata[f"{profile.metadata_prefix}_error"] = str(exc)
        execution_logger.log_agent_complete(
            profile.agent_name,
            current_data,
            time.time() - agent_start_time,
            False,
            str(exc),
        )
        await emit_event(
            event_sink,
            "progress",
            {
                "stage": profile.metadata_prefix,
                "status": "error",
                "message": f"{profile.summary_title}失败：{exc}",
                "agent": profile.agent_name,
            },
            trace_agent=profile.agent_name,
        )
        return {
            "data": current_data,
            "messages": current_messages,
            "metadata": current_metadata,
        }
