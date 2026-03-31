# Current State

- Runtime root: `/srv/fin` (symlink to `/root/autodl-tmp/fin`)
- Services: `fin_agent`, `fin_data_svr`, `fin_llm`
- MCP mode: stdio, launched by `fin_agent`
- Current LLM fallback: `simple_openai_server.py`
- Known blocker: current fallback server does not support OpenAI tool calling
- System disk is tight; heavy downloads must use data disk-backed paths and tmux
