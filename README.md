# fin

Monorepo for the financial AI project.

## Layout
- `services/fin_agent`: agent orchestration service
- `services/fin_llm`: local LLM serving service
- `services/fin_data_svr`: MCP-based market data service
- `ops`: env templates, deployment helpers, systemd units, docs

## Current Status
- Service directories and environment definitions have been standardized.
- `fin_llm` serves DianJin through vLLM with OpenAI-compatible API.
- `fin_data_svr` runs with a dedicated conda environment and passes selftest.
- `fin_agent` can run end-to-end and generate reports.
- Remaining known issue: the current model does not yet reliably trigger MCP tool calls in the full agent loop.
