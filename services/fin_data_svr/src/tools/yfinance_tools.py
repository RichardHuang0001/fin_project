"""
YFinance 专属 MCP 工具：提供 yfinance 独有的数据（估值指标、盈利历史、分析师推荐等）。
这些工具通过 MultiMarketDataSource 路由到 YFinanceDataSource。
"""
import logging

from mcp.server.fastmcp import FastMCP
from src.data_source_interface import FinancialDataSource
from src.tools.stock_market import safe_data_fetch

logger = logging.getLogger(__name__)


def register_yfinance_tools(app: FastMCP, active_data_source: FinancialDataSource):
    """注册 yfinance 专属工具到 MCP 应用。"""

    @app.tool()
    def get_stock_valuation_metrics(code: str) -> str:
        """
        获取股票的详细估值指标（适用于美股和港股）

        参数:
            code: 股票代码，支持多种格式：
                  美股：'AAPL', 'MSFT', 'GOOGL'
                  港股：'0700.HK', 'HK700', '9988.HK'
                  A股：'sh.600000', 'sz.000001'（也会返回数据但字段较少）

        返回:
            包含估值指标（PE/PB/PEG/EV/股息率/分析师目标价等）的 Markdown 表格
        """
        logger.info(f"Tool 'get_stock_valuation_metrics' called for {code}")
        return safe_data_fetch(
            "get_stock_valuation_metrics",
            active_data_source.get_stock_valuation_metrics,
            code=code,
        )

    @app.tool()
    def get_earnings_history(code: str) -> str:
        """
        获取股票的盈利历史（EPS 和营收 vs 预期，适用于美股和港股）

        参数:
            code: 股票代码（格式同 get_stock_valuation_metrics）

        返回:
            包含年度/季度盈利数据（实际 EPS、预估 EPS、惊喜值）的 Markdown 表格
        """
        logger.info(f"Tool 'get_earnings_history' called for {code}")
        return safe_data_fetch(
            "get_earnings_history",
            active_data_source.get_earnings_history,
            code=code,
        )

    @app.tool()
    def get_analyst_recommendations(code: str) -> str:
        """
        获取分析师评级推荐（适用于美股和港股）

        参数:
            code: 股票代码（格式同 get_stock_valuation_metrics）

        返回:
            包含分析师买入/持有/卖出评级历史的 Markdown 表格
        """
        logger.info(f"Tool 'get_analyst_recommendations' called for {code}")
        return safe_data_fetch(
            "get_analyst_recommendations",
            active_data_source.get_analyst_recommendations,
            code=code,
        )
