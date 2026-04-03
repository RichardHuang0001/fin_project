"""
NewsAnalysis Agent
新闻分析 Agent：由代码主导新闻抓取，LLM 基于真实新闻结果进行总结。
"""

from __future__ import annotations

from src.agents.data_driven_executor import (
    AnalysisProfile,
    ToolStep,
    build_stock_query,
    run_data_driven_analysis,
)
from src.utils.logging_config import WAIT_ICON, setup_logger
from src.utils.state_definition import AgentState

logger = setup_logger(__name__)


NEWS_PROFILE = AnalysisProfile(
    agent_name="news_agent",
    analysis_key="news_analysis",
    error_key="news_analysis_error",
    metadata_prefix="news_agent",
    completion_message="新闻分析已完成",
    summary_title="新闻分析代理",
    summary_objective="围绕相关新闻和事件脉络，输出情绪倾向、风险提示与简要结论。",
    summary_requirements=[
        "先概括新闻主线或主要事件。",
        "说明新闻偏正面、偏中性还是偏负面，并给出依据。",
        "指出最值得关注的风险或不确定性。",
        "最后给出一句谨慎的新闻面判断。",
    ],
    allowed_tools=[
        "get_stock_basic_info",
        "crawl_news",
    ],
    tool_steps=[
        ToolStep(
            name="get_stock_basic_info",
            label="公司基本信息",
            args_builder=lambda data: {"code": data.get("stock_code")},
            required=False,
        ),
        ToolStep(
            name="crawl_news",
            label="相关新闻",
            args_builder=lambda data: {"query": build_stock_query(data), "top_k": 6},
        ),
    ],
)


async def news_agent(state: AgentState) -> AgentState:
    logger.info("%s NewsAgent: Starting data-driven news analysis.", WAIT_ICON)
    return await run_data_driven_analysis(state, NEWS_PROFILE, logger)

