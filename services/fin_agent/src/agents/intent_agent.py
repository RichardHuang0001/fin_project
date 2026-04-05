"""
Intent Agent: Parses user natural language query into structured analysis tasks.
意图识别智能体：将用户自然语言查询解析为结构化的分析任务。
"""
import os
import re
import json
import time
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from src.utils.state_definition import AgentState
from src.utils.logging_config import setup_logger, WAIT_ICON, SUCCESS_ICON, ERROR_ICON
from src.utils.execution_logger import get_execution_logger
from src.utils.market_detector import detect_market
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

logger = setup_logger(__name__)

async def intent_agent(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the user's query to identify the company, stock code, and specific analysis tasks.
    分析用户查询以识别公司名称、股票代码和具体分析任务。
    """
    logger.info(f"{WAIT_ICON} IntentAgent: Identifying user intent.")

    execution_logger = get_execution_logger()
    agent_name = "intent_agent"

    current_data = state.get("data", {})
    user_query = current_data.get("query", "")

    # 记录 Agent 开始
    execution_logger.log_agent_start(agent_name, {"user_query": user_query})
    start_time = time.time()

    # 获取 LLM 配置
    api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
    model_name = os.getenv("OPENAI_COMPATIBLE_MODEL")

    if not all([api_key, base_url, model_name]):
        logger.error(f"{ERROR_ICON} IntentAgent: Missing API environment variables.")
        return {"data": {**current_data, "intent_error": "Missing environment variables"}}

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1, # 保持低温度以获得稳定的 JSON 输出
        max_tokens=500
    )

    system_prompt = """
    你是一个金融分析意图识别专家。你的任务是从用户的查询中提取股票分析所需的信息。

    ### 输出格式：
    必须输出且仅输出 JSON 格式（不要包含任何其他文字）：
    {
        "company_name": "公司简称或全称，未提及则为 null",
        "stock_code": "股票代码，保持用户输入的原始格式",
        "market": "a_share / hk / us / unknown（标注市场类型）",
        "tasks": ["需要执行的任务列表，可选值：fundamental, technical, value, news, summary"],
        "reasoning": "简短的任务识别理由",
        "is_financial_query": true/false (是否为股票分析相关请求)
    }

    ### 任务分配逻辑：
    1. fundamental: 涉及财务状况、盈利能力、资产负债、表现等财务指标。
    2. technical: 涉及股价走势、趋势判断、K线、均线、MACD等指标。
    3. value: 涉及估值水平、便宜/贵、PE/PB分位数等。
    4. news: 涉及近期新闻、舆情热点、风险动态。
    5. summary: 涉及"值得买吗"、"分析一下"、"表现如何"等需要综合判断的问题。

    ### 市场识别规则：
    - A股：6位数字代码（如600519、000001、300750）
    - 港股：4-5位数字代码（如0700、9988），或带HK前缀（HK0700），或带.HK后缀（0700.HK）
    - 美股：英文代码（如AAPL、MSFT、GOOGL、TSLA、NVDA）
    - 如果用户提到"港股"、"美股"、"纳斯达克"、"纽交所"等关键词，请据此判断市场

    ### 提取规则：
    - 如果用户只提供了代码，请在 company_name 中填入该代码对应的已知公司名。如果你不知道，请填入 null。
    - 如果用户只提供了公司名，请尽量补全公司名。
    - 如果用户的问题很笼统（如"分析一下茅台"），请在 tasks 中包含所有 5 个任务。
    - 如果用户问特定问题（如"财务怎么样"），tasks 中只需包含 fundamental。
    """

    user_prompt = f"用户查询：{user_query}"

    try:
        llm_start_time = time.time()
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        llm_execution_time = time.time() - llm_start_time

        # 解析 JSON
        content = response.content.strip()
        logger.info(f"IntentAgent raw response: {content}")

        # 更加鲁棒的 JSON 提取逻辑
        json_str = ""
        # 优先匹配 ```json ... ```
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 其次匹配 ``` ... ```
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # 最后尝试寻找第一个 { 和最后一个 }
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx:end_idx+1]
                else:
                    json_str = content

        intent_data = json.loads(json_str)
        print(f"\n[DEBUG] IntentAgent parsed data: {intent_data}\n")

        # 记录 LLM 交互
        execution_logger.log_llm_interaction(
            agent_name=agent_name,
            interaction_type="intent_parsing",
            input_messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            output_content=json_str,
            model_config={"model": model_name, "temperature": 0.1},
            execution_time=llm_execution_time
        )

        # 更新状态中的数据
        updated_data = {**current_data}
        updated_data["intent"] = intent_data

        # 如果 LLM 提取到了公司名或代码，覆盖之前正则提取的结果
        if intent_data.get("company_name") and intent_data["company_name"] != "null":
            updated_data["company_name"] = intent_data["company_name"]
            logger.info(f"IntentAgent found company: {updated_data['company_name']}")

        if intent_data.get("stock_code") and intent_data["stock_code"] != "null":
            code = str(intent_data["stock_code"]).strip()
            market = intent_data.get("market", "unknown")

            if market == "a_share":
                # A 股：添加 sh./sz. 前缀
                if code.startswith('6'):
                    updated_data["stock_code"] = f"sh.{code}"
                elif code.startswith('0') or code.startswith('3'):
                    updated_data["stock_code"] = f"sz.{code}"
                else:
                    updated_data["stock_code"] = code
            else:
                # 港股/美股：原样传入，yfinance _normalize_symbol 负责处理
                updated_data["stock_code"] = code

            logger.info(f"IntentAgent found code: {updated_data['stock_code']}, market: {market}")

        # 写入市场类型到 state
        if intent_data.get("market") and intent_data["market"] != "null":
            updated_data["market_type"] = intent_data["market"]
        elif updated_data.get("stock_code"):
            # 回退：用 detect_market 推断
            from src.utils.market_detector import MarketType
            detected = detect_market(updated_data["stock_code"])
            if detected != MarketType.UNKNOWN:
                updated_data["market_type"] = detected.value

        # 记录 Agent 完成
        execution_logger.log_agent_complete(agent_name, updated_data, time.time() - start_time, True)

        logger.info(f"{SUCCESS_ICON} IntentAgent: Identified tasks: {intent_data.get('tasks')}")
        return {"data": updated_data}

    except Exception as e:
        logger.error(f"{ERROR_ICON} IntentAgent: Error parsing intent: {e}")
        return {"data": {**current_data, "intent_error": str(e)}}
