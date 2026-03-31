#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 项目轻量自测脚本。

目标：
1. 验证关键依赖可导入
2. 验证 MCP Server 可以构建
3. 验证 Baostock 核心接口可查询
4. 可选验证新闻抓取链路
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("selftest_mcp")


def check_imports() -> list[tuple[str, bool, str]]:
    modules = [
        "baostock",
        "pandas",
        "requests",
        "bs4",
        "mcp",
        "tabulate",
    ]
    results: list[tuple[str, bool, str]] = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            results.append((module_name, True, "ok"))
        except Exception as exc:  # pragma: no cover - diagnostic path
            results.append((module_name, False, str(exc)))
    return results


def run_data_checks(with_news: bool) -> list[tuple[str, bool, str]]:
    from src.baostock_data_source import BaostockDataSource

    ds = BaostockDataSource()
    checks: list[tuple[str, bool, str]] = []

    samples = [
        (
            "get_stock_basic_info",
            lambda: ds.get_stock_basic_info("sh.600000"),
        ),
        (
            "get_historical_k_data",
            lambda: ds.get_historical_k_data(
                code="sh.600000",
                start_date="2024-01-02",
                end_date="2024-01-31",
                frequency="d",
                adjust_flag="3",
            ),
        ),
        (
            "get_trade_dates",
            lambda: ds.get_trade_dates(
                start_date="2024-01-01",
                end_date="2024-01-31",
            ),
        ),
        (
            "get_stock_industry",
            lambda: ds.get_stock_industry(code="sh.600000"),
        ),
    ]

    if with_news:
        samples.append(
            (
                "crawl_news",
                lambda: ds.crawl_news("贵州茅台", top_k=3),
            )
        )

    for name, func in samples:
        try:
            result = func()
            if hasattr(result, "empty"):
                row_count = len(result)
                message = f"ok, rows={row_count}"
                checks.append((name, row_count > 0, message))
            else:
                text = str(result)
                ok = "出错" not in text and "Error:" not in text and len(text.strip()) > 0
                preview = text[:120].replace("\n", " ")
                checks.append((name, ok, preview))
        except Exception as exc:
            checks.append((name, False, str(exc)))

    return checks


def check_server_build() -> tuple[bool, str]:
    try:
        module = importlib.import_module("mcp_server")
        app = getattr(module, "app", None)
        if app is None:
            return False, "mcp_server.py 已导入，但未找到 app"
        return True, f"ok, app_type={type(app).__name__}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="A-Share MCP 本机轻量自测")
    parser.add_argument(
        "--with-news",
        action="store_true",
        help="附带测试新闻抓取链路；此项更慢且受外网/反爬影响",
    )
    args = parser.parse_args()

    failures = 0

    print("== 1. 依赖导入检查 ==")
    for module_name, ok, detail in check_imports():
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {module_name}: {detail}")
        if not ok:
            failures += 1

    print("\n== 2. MCP Server 构建检查 ==")
    ok, detail = check_server_build()
    print(f"[{'PASS' if ok else 'FAIL'}] mcp_server: {detail}")
    if not ok:
        failures += 1

    print("\n== 3. Baostock 核心接口检查 ==")
    for name, ok, detail in run_data_checks(with_news=args.with_news):
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")
        if not ok:
            failures += 1

    print("\n== 结果 ==")
    if failures == 0:
        print("自测通过：关键 MCP 能力可用。")
        return 0

    print(f"自测未通过：共 {failures} 项失败。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
