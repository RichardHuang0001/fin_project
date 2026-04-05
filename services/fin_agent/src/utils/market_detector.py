"""
市场检测工具：根据股票代码判断所属市场（A股/港股/美股）。
"""
import re
from enum import Enum
from typing import Optional


class MarketType(Enum):
    A_SHARE = "a_share"
    HK = "hk"
    US = "us"
    UNKNOWN = "unknown"


def detect_market(
    stock_code: Optional[str], company_name: Optional[str] = None
) -> MarketType:
    """
    根据股票代码（和可选的公司名称）检测所属市场。

    代码规则：
    - A股：以 "sh." 或 "sz." 开头，或 6 位纯数字
    - 港股：包含 ".HK"，以 "HK" 开头，或 4-5 位纯数字
    - 美股：1-5 位英文字母代码（如 AAPL, MSFT）
    """
    if not stock_code:
        return MarketType.UNKNOWN

    code = stock_code.strip()
    upper = code.upper()

    # 显式 A 股前缀
    if upper.startswith("SH.") or upper.startswith("SZ."):
        return MarketType.A_SHARE

    # 港股模式
    if ".HK" in upper:
        return MarketType.HK
    if upper.startswith("HK") and len(upper) > 2 and upper[2:].isdigit():
        return MarketType.HK
    if upper.startswith("HK.") and len(upper) > 3 and upper[3:].isdigit():
        return MarketType.HK

    # 纯数字模式
    if code.isdigit():
        if len(code) == 6:
            return MarketType.A_SHARE
        if 4 <= len(code) <= 5:
            return MarketType.HK

    # 美股代码（1-5 位英文字母，可选带 .XX 后缀如 BRK.B）
    if re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", upper):
        return MarketType.US

    return MarketType.UNKNOWN
