# Refactor Progress

## Completed
- Surveyed current server layout and environments.
- Created `/srv/fin` runtime root as a symlink to `/root/autodl-tmp/fin`.
- Migrated service code into `/srv/fin/services/{fin_agent,fin_data_svr,fin_llm}`.
- Centralized runtime config under `/srv/fin/config`.
- Added `ops` skeleton with env templates, deploy script, current-state note, and systemd templates.
- Added standardized `scripts/start.sh`, `scripts/selftest.sh`, and `scripts/healthcheck.sh` for all three services.
- Patched `fin_agent` MCP path to read `FIN_DATA_SVR_DIR` and default to `/srv/fin/services/fin_data_svr`.
- Patched `fin_llm/simple_openai_server.py` to read `.env` from centralized config symlink.
- Verified `fin_data_svr` selftest passes from `/srv/fin/services/fin_data_svr`.
- Removed duplicated 15G model copy from the new service tree and repointed model symlinks to save disk.
- Cleaned system disk caches and old failed environments; root usage dropped from 100% to about 42%.
- Simplified `fin_llm` requirements to remove the FastAPI/Starlette resolver conflict.

## In Progress
- Building a dedicated `fin_llm` conda environment on the data disk prefix `/root/autodl-tmp/conda-envs/fin_llm_py312`.
- Active tmux session: `fin-llm-build`
- Active log: `/srv/fin/logs/fin_llm/setup_fin_llm_env.log`
- Current stage: `conda create --clone base` into the data disk prefix.

## Next
- Finish `fin_llm` environment build.
- Start vLLM tool-calling server on a side port for validation.
- Run `tests/test_openai_tool_call.py`.
- If tool calling works, point `fin_agent` to the new `fin_llm` endpoint for end-to-end verification.
