import logging
from typing import List, Optional

import pandas as pd
import yfinance as yf

from .data_source_interface import FinancialDataSource, NoDataFoundError

logger = logging.getLogger(__name__)


class YFinanceDataSource(FinancialDataSource):
    """YFinance 实现：用于美股与港股数据获取。"""

    _INTERVAL_MAP = {
        "d": "1d",
        "w": "1wk",
        "m": "1mo",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "60m",
    }

    def _normalize_symbol(self, code: str) -> str:
        """将用户输入规范化为 yfinance 代码，包含港股自动映射。"""
        if not code:
            raise ValueError("code cannot be empty")

        raw = code.strip()
        upper = raw.upper()

        if upper.startswith("SH.") or upper.startswith("SZ."):
            return raw

        if upper.startswith("HK") and upper[2:].isdigit():
            return f"{int(upper[2:]):04d}.HK"

        if upper.startswith("HK.") and upper[3:].isdigit():
            return f"{int(upper[3:]):04d}.HK"

        if upper.endswith(".HK"):
            prefix = upper[:-3]
            if prefix.isdigit():
                return f"{int(prefix):04d}.HK"
            return upper

        if upper.isdigit() and len(upper) <= 5:
            return f"{int(upper):04d}.HK"

        return upper

    def _unsupported(self, method_name: str) -> NoDataFoundError:
        return NoDataFoundError(
            f"{method_name} is not supported for non-A-share markets via yfinance."
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
        symbol = self._normalize_symbol(code)
        interval = self._INTERVAL_MAP.get(frequency, "1d")

        logger.info(
            "Fetching yfinance K-data for %s (%s to %s), interval=%s, adjust=%s",
            symbol,
            start_date,
            end_date,
            interval,
            adjust_flag,
        )

        df = yf.download(
            tickers=symbol,
            start=start_date,
            end=end_date,
            interval=interval,
            auto_adjust=False,
            progress=False,
            actions=False,
            group_by="column",
        )

        if df is None or df.empty:
            raise NoDataFoundError(
                f"No historical data found for {symbol} in the specified range."
            )

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else "Datetime"
        if date_col in df.columns:
            df = df.rename(columns={date_col: "date"})
        elif "index" in df.columns:
            df = df.rename(columns={"index": "date"})
        else:
            df.insert(0, "date", pd.NaT)

        df.columns = [str(col).lower() for col in df.columns]
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["code"] = symbol

        default_cols = ["date", "code", "open", "high", "low", "close", "volume"]
        available_default = [col for col in default_cols if col in df.columns]
        ordered = df[available_default + [col for col in df.columns if col not in available_default]]

        if fields:
            selected = [col for col in fields if col in ordered.columns]
            if not selected:
                raise ValueError(
                    f"None of the requested fields {fields} are available in yfinance result."
                )
            return ordered[selected]

        return ordered

    def get_stock_basic_info(self, code: str, fields: Optional[List[str]] = None) -> pd.DataFrame:
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        info = ticker.info or {}
        code_name = (
            info.get("shortName")
            or info.get("longName")
            or info.get("displayName")
            or symbol
        )

        data = {
            "code": symbol,
            "code_name": code_name,
            "exchange": info.get("exchange"),
            "market": info.get("market"),
            "currency": info.get("currency"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
        }

        df = pd.DataFrame([data])
        if fields:
            selected = [col for col in fields if col in df.columns]
            if not selected:
                raise ValueError(
                    f"None of the requested fields {fields} are available in yfinance basic info."
                )
            return df[selected]
        return df

    def get_trade_dates(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_trade_dates")

    def get_all_stock(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_all_stock")

    def get_deposit_rate_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_deposit_rate_data")

    def get_loan_rate_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_loan_rate_data")

    def get_required_reserve_ratio_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        year_type: str = "0",
        **kwargs,
    ) -> pd.DataFrame:
        raise self._unsupported("get_required_reserve_ratio_data")

    def get_money_supply_data_month(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_money_supply_data_month")

    def get_money_supply_data_year(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_money_supply_data_year")

    def get_profit_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_profit_data")

    def get_operation_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_operation_data")

    def get_growth_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_growth_data")

    def get_balance_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_balance_data")

    def get_cash_flow_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_cash_flow_data")

    def get_dupont_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_dupont_data")

    def get_sz50_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_sz50_stocks")

    def get_hs300_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_hs300_stocks")

    def get_zz500_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_zz500_stocks")

    def get_dividend_data(self, code: str, year: str, year_type: str = "report") -> pd.DataFrame:
        raise self._unsupported("get_dividend_data")

    def get_adjust_factor_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise self._unsupported("get_adjust_factor_data")

    def get_performance_express_report(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise self._unsupported("get_performance_express_report")

    def get_forecast_report(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise self._unsupported("get_forecast_report")

    def get_stock_industry(self, code: Optional[str] = None, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_stock_industry")
