# fin_project

金融多服务项目总仓库。

## 目录
- `services/fin_agent`：主服务，负责 Agent 编排、代码主导取数、分析流程和报告生成。
- `services/fin_llm`：模型服务，负责本地大模型推理与 OpenAI 兼容接口。
- `services/fin_data_svr`：数据服务，负责 MCP 工具、行情/财务/新闻数据获取。
- `ops`：环境模板、部署脚本、systemd 示例、说明文档。

## 当前项目结构
- `fin_agent` 保留多 Agent 工作流，但工具调用不再依赖模型自动 `tool calling`。
- 当前 4 个分析 Agent（基本面、技术面、估值、新闻）采用统一的“代码主导取数 + LLM 总结”模式。
- 新增轻量执行层：
  - `services/fin_agent/src/agents/data_driven_executor.py`
- 每个 Agent 只维护自己的 profile、允许工具集和取数步骤，后续新增市场或 Agent 时按同样方式扩展。

## 已完成的规范化改造
- 统一了总目录结构，当前服务器标准目录为 `/srv/fin`。
- 三个核心服务都拆成独立运行环境，不再共用一个混乱环境。
- 配置集中到 `/srv/fin/config`，代码不再依赖个人电脑路径。
- `fin_llm` 已切到 `vLLM + OpenAI-compatible API` 方案。
- `fin_data_svr` 已完成独立环境与自测脚本整理。
- `fin_agent` 已完成独立环境整理，并修复了 API 模式下对本地模型依赖的错误导入问题。
- `fin_agent` 已完成“代码主导工具调用”重构，真实 MCP 工具调用已恢复。

## 当前 conda 环境
- `fin_llm_py312`
  激活：`conda activate /root/autodl-tmp/conda-envs/fin_llm_py312`
- `fin_agent_py312`
  激活：`conda activate /root/autodl-tmp/conda-envs/fin_agent_py312`
- `fin_data_py312`
  激活：`conda activate /root/autodl-tmp/conda-envs/fin_data_py312`

说明：当前服务器采用“每服务一个独立 conda 环境”的方式运行，不要再新建个人 venv 或随意复用别的环境。

## 配置位置
- 真实配置：`/srv/fin/config`
- 主要文件：
  - `fin_agent.env`
  - `fin_llm.env`
  - `fin_data_svr.env`

注意：
- 不要把真实 `.env`、日志、报告、模型权重提交到 Git。
- 模型权重和运行日志属于运行时资源，不属于源码。

## 如何运行
### 1. 启动 fin_llm
```bash
conda activate /root/autodl-tmp/conda-envs/fin_llm_py312
cd /srv/fin/services/fin_llm
./scripts/start.sh
```
说明：
- 当前标准启动方式会拉起 vLLM，并监听 `fin_llm.env` 里配置的地址。
- 目前默认本机地址是 `http://127.0.0.1:6006/v1`。

### 2. 测试 fin_llm
```bash
conda activate /root/autodl-tmp/conda-envs/fin_llm_py312
cd /srv/fin/services/fin_llm
python tests/test_openai_tool_call.py
```
这条命令用于验证模型服务是否真的返回 `tool_calls`。

### 3. 测试 fin_data_svr
```bash
conda activate /root/autodl-tmp/conda-envs/fin_data_py312
cd /srv/fin/services/fin_data_svr
./scripts/healthcheck.sh
```
如果要跑完整自测：
```bash
conda activate /root/autodl-tmp/conda-envs/fin_data_py312
cd /srv/fin/services/fin_data_svr
./run_fulltest.sh
```

### 4. 运行 fin_agent
```bash
conda activate /root/autodl-tmp/conda-envs/fin_agent_py312
cd /srv/fin/services/fin_agent
./scripts/start.sh --command '分析嘉友国际(603871)'
```
说明：
- `fin_agent` 会按配置自动调用 `fin_llm`。
- `fin_agent` 会按配置自动拉起 `fin_data_svr` 的 MCP 进程。
- 现在的 `fin_agent` 不再要求模型自己发起 `tool_calls`，而是由代码按 Agent profile 主动取数，再交给模型总结。

### 5. 测试 fin_agent
简单接口测试：
```bash
conda activate /root/autodl-tmp/conda-envs/fin_agent_py312
cd /srv/fin/services/fin_agent
./scripts/selftest.sh
```
端到端分析测试：
```bash
conda activate /root/autodl-tmp/conda-envs/fin_agent_py312
cd /srv/fin/services/fin_agent
./scripts/start.sh --command '分析嘉友国际(603871)'
```
报告输出目录：
- `/srv/fin/services/fin_agent/reports`

## 如何调试
### 看 fin_llm 日志
```bash
tail -f /srv/fin/logs/fin_llm/vllm_6006.log
```

### 看 fin_agent 日志
```bash
tail -f /srv/fin/logs/fin_agent/e2e_smoke.log
```
或看执行目录：
```bash
ls -lt /srv/fin/services/fin_agent/logs
```

### 看 Agent trace
```bash
ls -lt /srv/fin/services/fin_agent/logs/<执行目录>/traces
```
重点看：
- `tool_catalog`
- `tool_plan`
- `tool_results`
- `request_context`
- `agent_error`

### 看数据服务日志/健康检查
```bash
conda activate /root/autodl-tmp/conda-envs/fin_data_py312
cd /srv/fin/services/fin_data_svr
./scripts/healthcheck.sh
```

### 常见排查顺序
1. 先确认 `fin_llm` 是否能访问：`curl http://127.0.0.1:6006/health`
2. 再确认 `fin_llm` 的 tool calling 测试是否通过。
3. 再确认 `fin_data_svr` 自测是否通过。
4. 最后再跑 `fin_agent` 的端到端命令。

## 当前状态
- `fin_llm`：已能正常启动，且协议层支持 tool calling。
- `fin_data_svr`：已能正常自测并访问 Baostock。
- `fin_agent`：已能跑通主流程并生成报告。
- 真实 MCP 调用已恢复，日志中可看到 `CallToolRequest` 和具体工具执行记录。
- 当前剩余问题主要是数据源层面的缺数或返回为空，例如部分业绩快报/预告区间无数据。

## 常用位置
- 总仓库：`/srv/fin`
- 主服务：`/srv/fin/services/fin_agent`
- 模型服务：`/srv/fin/services/fin_llm`
- 数据服务：`/srv/fin/services/fin_data_svr`

## 分支规范
- `main`：稳定分支，只保留可展示、可提交、可回归的版本。
- 开发任何功能前，必须先从 `main` 拉新分支。
- 分支命名建议：
  - `feature/<你的功能名>`
  - `fix/<你的修复名>`

示例：
- `feature/agent-tool-calling`
- `feature/web-ui`
- `fix/summary-import`

开发要求：
- 不要直接在 `main` 上改代码。
- 不要把未测试完成的内容直接合并到 `main`。
- 自己的功能完成后，先自测，再合并。
- 改环境、改依赖、改配置前，先看 README 和 `ops` 目录里的说明。

## 一句话说明
这个仓库现在已经是一个按服务拆分、按环境隔离、适合多人协作的单仓库项目；当前主链路已经改成“代码主导取数 + LLM 总结”，核心 MCP 调用问题已修复。
