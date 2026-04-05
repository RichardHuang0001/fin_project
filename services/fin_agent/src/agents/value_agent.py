"""
ValueAnalysis Agent
估值分析 Agent：由代码主导工具取数，LLM 基于估值相关数据进行总结。
"""
from __future__ import annotations

from src.agents.data_driven_executor import (
    AnalysisProfile,
    ToolStep,
    get_previous_completed_quarter,
    get_recent_date_range,
    get_market_type,
    run_data_driven_analysis,
)
from src.utils.logging_config import WAIT_ICON, setup_logger
from src.utils.state_definition import AgentState

logger = setup_logger(__name__)


def _quarter_args(current_data):
    args = get_previous_completed_quarter(current_data)
    args["code"] = current_data.get("stock_code")
    if "year" in args:
        args["year"] = str(args["year"])
    return args


def _price_args(current_data):
    args = get_recent_date_range(current_data, 365)
    args.update(
        {
            "code": current_data.get("stock_code"),
            "frequency": "d",
            "adjust_flag": "3",
        }
    )
    return args


def _only_a_share_args_builder(default_builder):
    """包装 args_builder，非 A 股时返回 None。"""
    def wrapper(data):
        if get_market_type(data) != "a_share":
            return None
        return default_builder(data)
    return wrapper


def _only_non_a_share_args_builder(default_builder):
    """包装 args_builder，仅非 A 股时执行。"""
    def wrapper(data):
        if get_market_type(data) == "a_share":
            return None
        return default_builder(data)
    return wrapper


VALUE_PROFILE = AnalysisProfile(
    agent_name="value_agent",
    analysis_key="value_analysis",
    error_key="value_analysis_error",
    metadata_prefix="value_agent",
    completion_message="估值分析已完成",
    summary_title="估值分析代理",
    summary_objective="围绕估值指标、盈利成长、分红和历史价格表现，判断当前估值是否合理。",
    summary_requirements=[
        "先给出当前估值结论。",
        "解释估值依据以及与基本面的匹配情况。",
        "说明历史价格或股息信息能否支持你的判断。",
        "最后给出一句谨慎的估值判断。",
    ],
    allowed_tools=[
        "get_stock_basic_info",
        "get_stock_industry",
        "get_dividend_data",
        "get_profit_data",
        "get_growth_data",
        "get_historical_k_data",
        "get_stock_valuation_metrics",
    ],
    tool_steps=[
        ToolStep(
            name="get_stock_basic_info",
            label="公司基本信息",
            args_builder=lambda data: {"code": data.get("stock_code")},
        ),
        ToolStep(
            name="get_stock_industry",
            label="行业信息",
            args_builder=_only_a_share_args_builder(
                lambda data: {"code": data.get("stock_code")}
            ),
            required=False,
        ),
        ToolStep(
            name="get_stock_valuation_metrics",
            label="详细估值指标",
            args_builder=_only_non_a_share_args_builder(
                lambda data: {"code": data.get("stock_code")}
            ),
            required=False,
        ),
        ToolStep(
            name="get_dividend_data",
            label="分红信息",
            args_builder=lambda data: {
                "code": data.get("stock_code"),
                "year": str(get_previous_completed_quarter(data)["year"]),
                "year_type": "report",
            },
            required=False,
        ),
        ToolStep(
            name="get_profit_data",
            label="盈利能力",
            args_builder=_quarter_args,
            required=False,
        ),
        ToolStep(
            name="get_growth_data",
            label="成长能力",
            args_builder=_quarter_args,
            required=False,
        ),
        ToolStep(
            name="get_historical_k_data",
            label="近 1 年日线",
            args_builder=_price_args,
            required=False,
        ),
    ],
)


async def value_agent(state: AgentState) -> AgentState:
    logger.info("%s ValueAgent: Starting data-driven value analysis.", WAIT_ICON)
    return await run_data_driven_analysis(state, VALUE_PROFILE, logger)
