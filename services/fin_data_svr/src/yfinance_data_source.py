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

        if upper.isdigit() and 4 <= len(upper) <= 5:
            return f"{int(upper):04d}.HK"

        return upper

    def _unsupported(self, method_name: str) -> NoDataFoundError:
        return NoDataFoundError(
            f"{method_name} is not supported for non-A-share markets via yfinance."
        )

    # ------------------------------------------------------------------
    # 辅助：将 year+quarter 映射到 yfinance 报表列
    # ------------------------------------------------------------------

    @staticmethod
    def _quarter_end_date(year: int, quarter: int) -> pd.Timestamp:
        """返回该季度的大致结束日期（用于匹配 yfinance 报表列）。"""
        month_map = {1: 3, 2: 6, 3: 9, 4: 12}
        return pd.Timestamp(year=year, month=month_map.get(quarter, 12), day=28)

    def _find_matching_period(
        self, columns: pd.DatetimeIndex, year: int, quarter: int, tolerance_days: int = 60
    ) -> Optional[pd.Timestamp]:
        """在 yfinance 报表的列中找到最接近 year Q{quarter} 的日期。"""
        if columns is None or len(columns) == 0:
            return None
        target = self._quarter_end_date(year, quarter)
        diffs = (columns - target).abs()
        min_idx = diffs.idxmin()
        if diffs[min_idx] <= pd.Timedelta(days=tolerance_days):
            return min_idx
        return None

    @staticmethod
    def _safe_get(df: pd.DataFrame, row_key: str, col) -> Optional[float]:
        """从 DataFrame 中安全提取单个值，支持模糊匹配行索引。"""
        if df is None or df.empty or col not in df.columns:
            return None
        for idx in df.index:
            if row_key.lower() in str(idx).lower():
                val = df.loc[idx, col]
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
        return None

    # ------------------------------------------------------------------
    # 已有方法：K 线 & 基本信息
    # ------------------------------------------------------------------

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
            # 基础信息
            "code": symbol,
            "code_name": code_name,
            "exchange": info.get("exchange"),
            "market": info.get("market"),
            "currency": info.get("currency"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
            # 估值指标
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "trailing_peg_ratio": info.get("trailingPegRatio"),
            "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
            "enterprise_to_revenue": info.get("enterpriseToRevenue"),
            # 财务健康
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "total_revenue": info.get("totalRevenue"),
            "ebitda": info.get("ebitda"),
            "free_cashflow": info.get("freeCashflow"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "gross_margins": info.get("grossMargins"),
            # 价格快照
            "previous_close": info.get("previousClose"),
            "regular_market_price": info.get("regularMarketPrice"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "two_hundred_day_average": info.get("twoHundredDayAverage"),
            "average_volume": info.get("averageVolume"),
            "beta": info.get("beta"),
            # 公司信息
            "employees": info.get("fullTimeEmployees"),
            "description": info.get("longBusinessSummary"),
            # 股本
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
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

    # ------------------------------------------------------------------
    # 财务报表方法（通过 yfinance financials / balance_sheet / cashflow）
    # ------------------------------------------------------------------

    def get_profit_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        stmts = ticker.quarterly_financials
        if stmts is None or stmts.empty:
            stmts = ticker.financials
        if stmts is None or stmts.empty:
            raise NoDataFoundError(f"No financial statements found for {symbol}")

        matched_col = self._find_matching_period(stmts.columns, int(year), quarter)
        if matched_col is None:
            raise NoDataFoundError(f"No profit data found for {year} Q{quarter} for {symbol}")

        row_data = {
            "code": symbol,
            "year": year,
            "quarter": quarter,
            "revenue": self._safe_get(stmts, "Total Revenue", matched_col),
            "gross_profit": self._safe_get(stmts, "Gross Profit", matched_col),
            "operating_income": self._safe_get(stmts, "Operating Income", matched_col),
            "net_income": self._safe_get(stmts, "Net Income", matched_col),
            "ebitda": self._safe_get(stmts, "EBITDA", matched_col),
        }

        # 计算利润率
        if row_data["revenue"] and row_data["revenue"] != 0:
            if row_data["net_income"] is not None:
                row_data["net_profit_margin"] = row_data["net_income"] / row_data["revenue"]
            if row_data["gross_profit"] is not None:
                row_data["gross_profit_margin"] = row_data["gross_profit"] / row_data["revenue"]
            if row_data["operating_income"] is not None:
                row_data["operating_margin"] = row_data["operating_income"] / row_data["revenue"]

        return pd.DataFrame([row_data])

    def get_balance_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        stmts = ticker.quarterly_balance_sheet
        if stmts is None or stmts.empty:
            stmts = ticker.balance_sheet
        if stmts is None or stmts.empty:
            raise NoDataFoundError(f"No balance sheet found for {symbol}")

        matched_col = self._find_matching_period(stmts.columns, int(year), quarter)
        if matched_col is None:
            raise NoDataFoundError(f"No balance data found for {year} Q{quarter} for {symbol}")

        row_data = {
            "code": symbol,
            "year": year,
            "quarter": quarter,
            "total_assets": self._safe_get(stmts, "Total Assets", matched_col),
            "total_liabilities": self._safe_get(stmts, "Total Liabilities Net Minority Interest", matched_col)
            or self._safe_get(stmts, "Total Liabilities", matched_col),
            "total_equity": self._safe_get(stmts, "Stockholders Equity", matched_col)
            or self._safe_get(stmts, "Total Equity Gross Minority Interest", matched_col),
            "current_assets": self._safe_get(stmts, "Current Assets", matched_col),
            "current_liabilities": self._safe_get(stmts, "Current Liabilities", matched_col),
            "cash": self._safe_get(stmts, "Cash And Cash Equivalents", matched_col),
            "total_debt": self._safe_get(stmts, "Total Debt", matched_col),
        }

        # 计算比率
        if row_data["total_assets"] and row_data["total_assets"] != 0:
            if row_data["total_equity"] is not None:
                row_data["debt_to_asset_ratio"] = (
                    row_data["total_liabilities"] / row_data["total_assets"]
                    if row_data["total_liabilities"]
                    else None
                )
        if row_data["current_liabilities"] and row_data["current_liabilities"] != 0:
            if row_data["current_assets"] is not None:
                row_data["current_ratio"] = row_data["current_assets"] / row_data["current_liabilities"]

        return pd.DataFrame([row_data])

    def get_cash_flow_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        stmts = ticker.quarterly_cashflow
        if stmts is None or stmts.empty:
            stmts = ticker.cashflow
        if stmts is None or stmts.empty:
            raise NoDataFoundError(f"No cash flow statement found for {symbol}")

        matched_col = self._find_matching_period(stmts.columns, int(year), quarter)
        if matched_col is None:
            raise NoDataFoundError(f"No cash flow data found for {year} Q{quarter} for {symbol}")

        row_data = {
            "code": symbol,
            "year": year,
            "quarter": quarter,
            "operating_cashflow": self._safe_get(stmts, "Operating Cash Flow", matched_col),
            "investing_cashflow": self._safe_get(stmts, "Investing Cash Flow", matched_col),
            "financing_cashflow": self._safe_get(stmts, "Financing Cash Flow", matched_col),
            "free_cashflow": self._safe_get(stmts, "Free Cash Flow", matched_col),
            "capital_expenditure": self._safe_get(stmts, "Capital Expenditure", matched_col),
        }

        return pd.DataFrame([row_data])

    def get_growth_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        """通过对比两个季度报表计算同比增长率。"""
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        stmts = ticker.quarterly_financials
        if stmts is None or stmts.empty:
            stmts = ticker.financials
        if stmts is None or stmts.empty:
            raise NoDataFoundError(f"No financial statements found for {symbol}")

        matched_col = self._find_matching_period(stmts.columns, int(year), quarter)
        if matched_col is None:
            raise NoDataFoundError(f"No growth data found for {year} Q{quarter} for {symbol}")

        # 查找一年前的同期数据
        prev_year = int(year) - 1
        prev_col = self._find_matching_period(stmts.columns, prev_year, quarter)
        if prev_col is None:
            raise NoDataFoundError(
                f"No prior year data found for {prev_year} Q{quarter} for {symbol}"
            )

        def _calc_growth(key: str) -> Optional[float]:
            curr = self._safe_get(stmts, key, matched_col)
            prev = self._safe_get(stmts, key, prev_col)
            if curr is not None and prev is not None and prev != 0:
                return (curr - prev) / abs(prev)
            return None

        row_data = {
            "code": symbol,
            "year": year,
            "quarter": quarter,
            "revenue_growth": _calc_growth("Total Revenue"),
            "net_income_growth": _calc_growth("Net Income"),
            "gross_profit_growth": _calc_growth("Gross Profit"),
            "operating_income_growth": _calc_growth("Operating Income"),
        }

        return pd.DataFrame([row_data])

    def get_dividend_data(self, code: str, year: str, year_type: str = "report") -> pd.DataFrame:
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        divs = ticker.dividends
        if divs is None or divs.empty:
            raise NoDataFoundError(f"No dividend data found for {symbol}")

        divs = divs.reset_index()
        divs.columns = ["date", "dividend"]
        divs["date"] = pd.to_datetime(divs["date"], errors="coerce")
        divs["year"] = divs["date"].dt.year

        target_year = int(year)
        yearly = divs[divs["year"] == target_year]

        if yearly.empty:
            raise NoDataFoundError(f"No dividend data for {symbol} in {target_year}")

        result = {
            "code": symbol,
            "year": str(target_year),
            "total_dividend": float(yearly["dividend"].sum()),
            "dividend_count": len(yearly),
            "dividends": yearly[["date", "dividend"]].to_dict(orient="records"),
        }

        return pd.DataFrame([result])

    # ------------------------------------------------------------------
    # 不支持的方法（yfinance 无对应数据源）
    # ------------------------------------------------------------------

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

    def get_operation_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_operation_data")

    def get_dupont_data(self, code: str, year: str, quarter: int) -> pd.DataFrame:
        raise self._unsupported("get_dupont_data")

    def get_sz50_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_sz50_stocks")

    def get_hs300_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_hs300_stocks")

    def get_zz500_stocks(self, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_zz500_stocks")

    def get_adjust_factor_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise self._unsupported("get_adjust_factor_data")

    def get_performance_express_report(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise self._unsupported("get_performance_express_report")

    def get_forecast_report(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise self._unsupported("get_forecast_report")

    def get_stock_industry(self, code: Optional[str] = None, date: Optional[str] = None) -> pd.DataFrame:
        raise self._unsupported("get_stock_industry")

    # ------------------------------------------------------------------
    # yfinance 独有方法（无 baostock 对应）
    # ------------------------------------------------------------------

    def get_earnings_history(self, code: str) -> pd.DataFrame:
        """获取盈利历史（EPS、营收 vs 预期）。"""
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        rows = []
        # 年度盈利
        earnings = ticker.earnings
        if earnings is not None and not earnings.empty:
            for date_val, row in earnings.iterrows():
                rows.append({
                    "code": symbol,
                    "period": str(date_val),
                    "period_type": "annual",
                    "eps_actual": row.get("epsActual") if "epsActual" in row.index else row.iloc[0] if len(row) > 0 else None,
                    "eps_estimate": row.get("epsEstimate") if "epsEstimate" in row.index else row.iloc[1] if len(row) > 1 else None,
                    "eps_surprise": row.get("epsDifference") if "epsDifference" in row.index else None,
                })

        # 季度盈利
        q_earnings = ticker.quarterly_earnings
        if q_earnings is not None and not q_earnings.empty:
            for date_val, row in q_earnings.iterrows():
                rows.append({
                    "code": symbol,
                    "period": str(date_val),
                    "period_type": "quarterly",
                    "eps_actual": row.get("epsActual") if "epsActual" in row.index else row.iloc[0] if len(row) > 0 else None,
                    "eps_estimate": row.get("epsEstimate") if "epsEstimate" in row.index else row.iloc[1] if len(row) > 1 else None,
                    "eps_surprise": row.get("epsDifference") if "epsDifference" in row.index else None,
                })

        if not rows:
            raise NoDataFoundError(f"No earnings history found for {symbol}")

        return pd.DataFrame(rows)

    def get_analyst_recommendations(self, code: str) -> pd.DataFrame:
        """获取分析师评级（买入/持有/卖出）。"""
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        recs = ticker.recommendations
        if recs is None or recs.empty:
            raise NoDataFoundError(f"No analyst recommendations found for {symbol}")

        recs = recs.reset_index()
        recs.columns = [str(c).lower() if isinstance(c, str) else c for c in recs.columns]
        recs["code"] = symbol

        return recs

    def get_stock_valuation_metrics(self, code: str) -> pd.DataFrame:
        """获取详细估值指标（从 ticker.info 提取）。"""
        symbol = self._normalize_symbol(code)
        ticker = yf.Ticker(symbol)

        info = ticker.info or {}

        data = {
            "code": symbol,
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "trailing_peg_ratio": info.get("trailingPegRatio"),
            "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
            "enterprise_to_revenue": info.get("enterpriseToRevenue"),
            "beta": info.get("beta"),
            "analyst_target_price": info.get("analystTargetPrice"),
            "analyst_rating": info.get("recommendationKey"),
            "number_of_analysts": info.get("numberOfAnalystOpinions"),
        }

        return pd.DataFrame([data])
