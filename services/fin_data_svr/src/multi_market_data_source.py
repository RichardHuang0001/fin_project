from typing import Optional, List

import pandas as pd

from .data_source_interface import FinancialDataSource, NoDataFoundError
from .baostock_data_source import BaostockDataSource
from .yfinance_data_source import YFinanceDataSource


class MultiMarketDataSource(FinancialDataSource):
    """多市场数据源路由：A股走Baostock，美股/港股走YFinance。"""

    def __init__(self):
        self.baostock_source = BaostockDataSource()
        self.yfinance_source = YFinanceDataSource()

    def _is_a_share_code(self, code: str) -> bool:
        if not code:
            return False
        normalized = code.strip().lower()
        return normalized.startswith("sh.") or normalized.startswith("sz.")

    def _get_source(self, code: str):
        if self._is_a_share_code(code):
            return self.baostock_source
        return self.yfinance_source

    def _non_a_share_not_supported(self, method_name: str) -> NoDataFoundError:
        return NoDataFoundError(
            f"{method_name} is currently not supported for non-A-share markets."
        )

    def get_historical_k_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjust_flag: str = "3",
        fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        source = self._get_source(code)
        return source.get_historical_k_data(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjust_flag=adjust_flag,
            fields=fields,
        )

    def get_stock_basic_info(self, code: str, fields: Optional[List[str]] = None) -> pd.DataFrame:
        source = self._get_source(code)
        return source.get_stock_basic_info(code=code, fields=fields)

    def get_trade_dates(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_trade_dates(start_date=start_date, end_date=end_date)

    def get_all_stock(self, date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_all_stock(date=date)

    def get_deposit_rate_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_deposit_rate_data(start_date=start_date, end_date=end_date)

    def get_loan_rate_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_loan_rate_data(start_date=start_date, end_date=end_date)

    def get_required_reserve_ratio_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        year_type: str = "0",
        **kwargs,
    ) -> pd.DataFrame:
        effective_year_type = kwargs.get("yearType", year_type)
        return self.baostock_source.get_required_reserve_ratio_data(
            start_date=start_date,
            end_date=end_date,
            year_type=effective_year_type,
        )

    def get_money_supply_data_month(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_money_supply_data_month(start_date=start_date, end_date=end_date)

    def get_money_supply_data_year(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_money_supply_data_year(start_date=start_date, end_date=end_date)

    def get_profit_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_profit_data")
        return source.get_profit_data(code=code, year=year, quarter=quarter)

    def get_operation_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_operation_data")
        return source.get_operation_data(code=code, year=year, quarter=quarter)

    def get_growth_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_growth_data")
        return source.get_growth_data(code=code, year=year, quarter=quarter)

    def get_balance_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_balance_data")
        return source.get_balance_data(code=code, year=year, quarter=quarter)

    def get_cash_flow_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_cash_flow_data")
        return source.get_cash_flow_data(code=code, year=year, quarter=quarter)

    def get_dupont_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_dupont_data")
        return source.get_dupont_data(code=code, year=year, quarter=quarter)

    def get_sz50_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_sz50_stocks(date=date)

    def get_hs300_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_hs300_stocks(date=date)

    def get_zz500_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        return self.baostock_source.get_zz500_stocks(date=date)

    def get_dividend_data(self, code: str, year: str, year_type: str = "report") -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_dividend_data")
        return source.get_dividend_data(code=code, year=year, year_type=year_type)

    def get_adjust_factor_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_adjust_factor_data")
        return source.get_adjust_factor_data(code=code, start_date=start_date, end_date=end_date)

    def get_performance_express_report(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_performance_express_report")
        return source.get_performance_express_report(code=code, start_date=start_date, end_date=end_date)

    def get_forecast_report(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        source = self._get_source(code)
        if source is self.yfinance_source:
            raise self._non_a_share_not_supported("get_forecast_report")
        return source.get_forecast_report(code=code, start_date=start_date, end_date=end_date)

    def get_stock_industry(self, code: Optional[str] = None, date: Optional[str] = None) -> pd.DataFrame:
        if code and not self._is_a_share_code(code):
            raise self._non_a_share_not_supported("get_stock_industry")
        return self.baostock_source.get_stock_industry(code=code, date=date)

    def crawl_news(self, query: str, top_k: int = 10) -> str:
        return self.baostock_source.crawl_news(query=query, top_k=top_k)
