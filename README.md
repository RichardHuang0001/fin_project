# fin_project

金融多服务项目总仓库。

## 目录
- `services/fin_agent`：主服务，负责 Agent 编排、分析流程和报告生成。
- `services/fin_llm`：模型服务，负责本地大模型推理与 OpenAI 兼容接口。
- `services/fin_data_svr`：数据服务，负责 MCP 工具、行情/财务/新闻数据获取。
- `ops`：环境模板、部署脚本、systemd 示例、说明文档。

## 今天完成的规范化改造
- 统一了总目录结构，当前服务器标准目录为 `/srv/fin`。
- 三个核心服务都拆成独立运行环境，不再共用一个混乱环境。
- 配置集中到 `/srv/fin/config`，代码不再依赖个人电脑路径。
- `fin_llm` 已切到 `vLLM + OpenAI-compatible API` 方案。
- `fin_data_svr` 已完成独立环境与自测脚本整理。
- `fin_agent` 已完成独立环境整理，并修复了 API 模式下对本地模型依赖的错误导入问题。

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

## 当前状态
- `fin_llm`：已能正常启动，且协议层支持 tool calling。
- `fin_data_svr`：已能正常自测并访问 Baostock。
- `fin_agent`：已能跑通主流程并生成报告。
- 已知问题：当前模型在完整 Agent 工作流中，仍不能稳定自动触发 MCP 工具调用，因此业务效果还未完全达到目标。

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
这个仓库现在已经不是最初那种临时拼起来的代码目录，而是一个按服务拆分、按环境隔离、适合多人协作的单仓库项目；但核心业务上仍有一个待解决问题：模型还不能稳定驱动 MCP 工具调用。
