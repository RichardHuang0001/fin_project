# fin_data_svr

`fin_data_svr` is the standalone market data service extracted from the current MCP project. It keeps the same tested behavior and provides:

- A-share market data tools
- Financial report tools
- Index and macro tools
- News crawling tools
- Self-test and full-test scripts

## Directory

```text
fin_data_svr/
  mcp_server.py
  src/
  run_server.sh
  run_selftest.sh
  run_fulltest.sh
  selftest_mcp.py
  test_baostock.py
  requirements.txt
  environment.yml
  .env.example
```

## Quick Start

```bash
conda env create -f environment.yml
conda activate fin_data_py312
./run_selftest.sh
./run_fulltest.sh
./run_server.sh
```

## Optional Environment Variables

Copy `.env.example` to `.env` only if you want local sentiment/risk model support for news analysis. `mcp_server.py` loads `.env` automatically from the service root.

- `FINANCE_QWEN_BASE_MODEL`
- `QWEN_RISK_MODEL_DIR`
- `QWEN_SENTIMENT_MODEL_DIR`

If these are unset, the service still runs and the news tool degrades gracefully to "未分析", which matches the tested behavior on the laptop.
