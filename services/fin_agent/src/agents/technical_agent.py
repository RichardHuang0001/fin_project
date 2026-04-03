"""
TechnicalAnalysis Agent
技术分析 Agent：由代码主导工具取数，LLM 基于行情数据进行总结。
"""

from __future__ import annotations

from src.agents.data_driven_executor import (
    AnalysisProfile,
    ToolStep,
    get_recent_date_range,
    run_data_driven_analysis,
)
from src.utils.logging_config import WAIT_ICON, setup_logger
from src.utils.state_definition import AgentState

logger = setup_logger(__name__)


def _kline_args(current_data):
    args = get_recent_date_range(current_data, 120)
    args.update(
        {
            "code": current_data.get("stock_code"),
            "frequency": "d",
            "adjust_flag": "3",
        }
    )
    return args


TECHNICAL_PROFILE = AnalysisProfile(
    agent_name="technical_agent",
    analysis_key="technical_analysis",
    error_key="technical_analysis_error",
    metadata_prefix="technical_agent",
    completion_message="技术分析已完成",
    summary_title="技术分析代理",
    summary_objective="围绕最近交易日和近几个月 K 线表现，总结趋势、支撑阻力和技术风险。",
    summary_requirements=[
        "先给出当前趋势判断。",
        "说明趋势依据、波动特征或价格区间。",
        "给出支撑阻力或短线风险提示。",
        "最后给出一句谨慎的技术面判断。",
    ],
    allowed_tools=[
        "get_stock_basic_info",
        "get_latest_trading_date",
        "get_historical_k_data",
        "get_trade_dates",
    ],
    tool_steps=[
        ToolStep(
            name="get_stock_basic_info",
            label="公司基本信息",
            args_builder=lambda data: {"code": data.get("stock_code")},
        ),
        ToolStep(
            name="get_latest_trading_date",
            label="最近交易日",
            args_builder=lambda data: {},
            required=False,
        ),
        ToolStep(
            name="get_historical_k_data",
            label="近 120 天日线",
            args_builder=_kline_args,
        ),
        ToolStep(
            name="get_trade_dates",
            label="近 30 天交易日",
            args_builder=lambda data: get_recent_date_range(data, 30),
            required=False,
        ),
    ],
)


async def technical_agent(state: AgentState) -> AgentState:
    logger.info("%s TechnicalAgent: Starting data-driven technical analysis.", WAIT_ICON)
    return await run_data_driven_analysis(state, TECHNICAL_PROFILE, logger)

