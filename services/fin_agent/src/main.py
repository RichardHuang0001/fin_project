"""
金融分析智能体系统主程序 (Financial Analysis AI Agent System Main Program)

本文件是金融分析智能体系统的核心入口点，实现了以下主要功能：

1. 多智能体工作流管理：使用LangGraph构建并行执行的智能体工作流
2. 命令行界面：提供用户友好的交互式命令行界面
3. 自然语言处理：自动识别和提取股票代码、公司名称
4. 日志系统：完整的执行日志记录和错误处理
5. 报告生成：生成综合性的金融分析报告

工作流程：
start_node → [fundamental_analyst, technical_analyst, value_analyst] → summarizer → END
"""

# ============================================================================
# 导入必要的模块和依赖
# ============================================================================

# 在导入其他模块之前设置环境变量，抑制无用输出
import os
import sys

# 设置环境变量来抑制transformers和其他库的冗余输出
os.environ["TRANSFORMERS_VERBOSITY"] = "error"  # 只显示错误信息
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # 禁用tokenizer并行化警告
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # 减少CUDA相关输出
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"  # 减少内存分配信息

# 设置日志级别，抑制第三方库的INFO级别输出
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("accelerate").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# 日志和状态管理相关导入
from src.utils.logging_config import setup_logger, SUCCESS_ICON, ERROR_ICON, WAIT_ICON
from src.utils.state_definition import AgentState
from src.utils.execution_logger import initialize_execution_logger, finalize_execution_logger, get_execution_logger

# 智能体模块导入 - 六个核心分析智能体
from src.agents.intent_agent import intent_agent       # 意图智能体：解析用户意图
from src.agents.summary_agent import summary_agent      # 总结智能体：整合所有分析结果
from src.agents.value_agent import value_agent          # 估值智能体：分析股票估值水平
from src.agents.technical_agent import technical_agent  # 技术分析智能体：分析价格趋势和技术指标
from src.agents.fundamental_agent import fundamental_agent  # 基本面智能体：分析财务状况和盈利能力
from src.agents.news_agent import news_agent            # 新闻分析智能体：分析新闻情感和风险

# LangGraph工作流框架导入
from langgraph.graph import StateGraph, END

# 环境变量和系统相关导入
from dotenv import load_dotenv
import argparse
import asyncio
import re
from datetime import datetime

# ============================================================================
# 初始化和配置
# ============================================================================

# 设置日志记录器
logger = setup_logger(__name__)

# 添加项目根目录到Python路径，确保模块导入正常工作
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# 加载环境变量（从.env文件）
load_dotenv(override=True)

# 调试：打印关键环境变量以验证配置
logger.info(f"Environment Variables Loaded:")
logger.info(
    f"  OPENAI_COMPATIBLE_MODEL: {os.getenv('OPENAI_COMPATIBLE_MODEL', 'Not Set')}")
logger.info(
    f"  OPENAI_COMPATIBLE_BASE_URL: {os.getenv('OPENAI_COMPATIBLE_BASE_URL', 'Not Set')}")
logger.info(
    f"  OPENAI_COMPATIBLE_API_KEY: {'*' * 20 if os.getenv('OPENAI_COMPATIBLE_API_KEY') else 'Not Set'}")

# 重新设置日志记录器（确保正确配置）
logger = setup_logger(__name__)


# ============================================================================
# 自然语言处理和股票信息提取
# ============================================================================

def extract_stock_info(query):
    """精确提取股票代码和公司名称"""
    stock_code = None
    company_name = None
    
    # 模式1: 包含"请帮我分析一下"的复杂查询，如"请帮我分析一下嘉友国际(603871)这只股票的投资价值如何"
    pattern1 = r'请帮我分析一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]'
    match1 = re.search(pattern1, query)
    if match1:
        company_name = match1.group(1).strip()
        stock_code = match1.group(2)
        return company_name, stock_code
    
    # 模式2: 包含"分析一下"的复杂查询，如"分析一下嘉友国际(603871)的财务状况"
    pattern2 = r'分析一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]'
    match2 = re.search(pattern2, query)
    if match2:
        company_name = match2.group(1).strip()
        stock_code = match2.group(2)
        return company_name, stock_code
    
    # 模式3: 股票代码在括号内，如"分析嘉友国际(603871)"
    pattern3 = r'分析\s*([^（(]+?)\s*[（(](\d{5,6})[)）]'
    match3 = re.search(pattern3, query)
    if match3:
        company_name = match3.group(1).strip()
        stock_code = match3.group(2)
        return company_name, stock_code
    
    # 模式4: 股票代码在括号内，如"分析(603871)嘉友国际"
    pattern4 = r'分析\s*[（(](\d{5,6})[)）]\s*([^）)]+)'
    match4 = re.search(pattern4, query)
    if match4:
        stock_code = match4.group(1)
        company_name = match4.group(2).strip()
        return company_name, stock_code
    
    # 模式5: 包含"帮我看看"的查询，如"帮我看看(000001)平安银行这只股票"
    pattern5 = r'帮我看看\s*[（(](\d{5,6})[)）]\s*([^）)]+?)(?:\s*这只|\s*这个)?\s*股票'
    match5 = re.search(pattern5, query)
    if match5:
        stock_code = match5.group(1)
        company_name = match5.group(2).strip()
        return company_name, stock_code
    
    # 模式6: 包含"我想了解一下"的查询，如"我想了解一下比亚迪(002594)的投资价值"
    pattern6 = r'我想了解一下\s*([^（(]+?)\s*[（(](\d{5,6})[)）]'
    match6 = re.search(pattern6, query)
    if match6:
        company_name = match6.group(1).strip()
        stock_code = match6.group(2)
        return company_name, stock_code
    
    # 模式7: 包含"帮我看看"的复杂查询，如"帮我看看茅台(600519)这只股票值得投资吗"
    pattern7 = r'帮我看看\s*([^（(]+?)\s*[（(](\d{5,6})[)）]'
    match7 = re.search(pattern7, query)
    if match7:
        company_name = match7.group(1).strip()
        stock_code = match7.group(2)
        return company_name, stock_code
    
    # 模式8: 直接公司名+括号格式，如"平安银行(000001)值得买吗"
    pattern8 = r'^([^（(]+?)\s*[（(](\d{5,6})[)）]'
    match8 = re.search(pattern8, query)
    if match8:
        company_name = match8.group(1).strip()
        stock_code = match8.group(2)
        return company_name, stock_code
    
    # 模式9: 包含"分析一下"的查询，如"分析一下宁德时代的财务状况"
    pattern9 = r'分析一下\s*([^0-9（）()\s]+?)(?:\s*的|\s|$)'
    match9 = re.search(pattern9, query)
    if match9:
        company_name = match9.group(1).strip()
    
    # 模式10: 包含"分析"关键词，如"分析嘉友国际"
    pattern10 = r'分析\s*([^0-9（）()\s]+)'
    match10 = re.search(pattern10, query)
    if match10 and not company_name:
        company_name = match10.group(1).strip()
    
    # 模式11: 包含"股票"关键词的查询，如"嘉友国际这只股票怎么样"
    pattern11 = r'([^0-9（）()\s]+)\s*(?:这只|这个|的)?\s*股票'
    match11 = re.search(pattern11, query)
    if match11 and not company_name:
        company_name = match11.group(1).strip()
    
    # 模式12: 包含"投资价值"的查询，如"了解一下腾讯的投资价值"
    pattern12 = r'了解一下\s*([^0-9（）()\s]+?)(?:\s*的|\s|$)'
    match12 = re.search(pattern12, query)
    if match12 and not company_name:
        company_name = match12.group(1).strip()
    
    # 模式13: 包含"给我分析一下"的查询，如"给我分析一下宁德时代的财务状况"
    pattern13 = r'给我分析一下\s*([^0-9（）()\s]+?)(?:\s*的|\s|$)'
    match13 = re.search(pattern13, query)
    if match13 and not company_name:
        company_name = match13.group(1).strip()
    
    # 模式14: 包含"的"字的查询，如"嘉友国际的财务表现如何"
    pattern14 = r'([^0-9（）()\s]+?)\s*的\s*(?:财务表现|盈利能力|现金流状况|资产负债情况|技术面|股价走势|技术指标|技术面表现|估值水平|市盈率|市净率|估值|投资风险|风险因素|风险评估|投资价值|股票|基本面情况|基本面|财务状况)'
    match14 = re.search(pattern14, query)
    if match14 and not company_name:
        company_name = match14.group(1).strip()
    
    # 模式15: 包含"在...中"的查询（无"的"字），如"比亚迪在新能源汽车行业的表现"
    pattern15 = r'([^0-9（）()\s]+?)\s*在\s*[^0-9（）()\s]*\s*中'
    match15 = re.search(pattern15, query)
    if match15 and not company_name:
        company_name = match15.group(1).strip()
    
    # 模式16: 包含"在...中"的查询，如"嘉友国际在行业中的地位"
    pattern16 = r'([^0-9（）()\s]+?)\s*在\s*[^0-9（）()\s]*\s*中\s*的'
    match16 = re.search(pattern16, query)
    if match16 and not company_name:
        company_name = match16.group(1).strip()
    
    # 模式17: 包含"面临"的查询，如"比亚迪面临的主要风险"
    pattern17 = r'([^0-9（）()\s]+?)\s*面临'
    match17 = re.search(pattern17, query)
    if match17 and not company_name:
        company_name = match17.group(1).strip()
    
    # 模式18: 直接包含5-6位数字股票代码
    pattern18 = r'\b(\d{5,6})\b'
    match18 = re.search(pattern18, query)
    if match18:
        stock_code = match18.group(1)
        # 如果只有代码没有名字，尝试保持 stock_code
        if not company_name:
            # 这里的 stock_code 已经赋值，直接返回
            return company_name, stock_code
    
    # 模式18b: 包含"分析" + 5-6位代码
    pattern18b = r'分析\s*(\d{5,6})'
    match18b = re.search(pattern18b, query)
    if match18b and not stock_code:
        stock_code = match18b.group(1)

    # 模式21: 识别常见的公司名称关键词（放在最后兜底）
    if not company_name:
        # 尝试匹配 2-6 个汉字，后接代码的情况，如 "贵州茅台 600519"
        pattern21 = r'([\u4e00-\u9fa5]{2,6})\s*(\d{5,6})?'
        match21 = re.search(pattern21, query)
        if match21:
            company_name = match21.group(1).strip()
            if not stock_code and match21.group(2):
                stock_code = match21.group(2)
    
    # 模式19: 包含"值得买"的查询，如"603871 这个股票值得买吗"
    pattern19 = r'(\d{5,6})\s*(?:这个|这只)?\s*股票\s*值得买'
    match19 = re.search(pattern19, query)
    if match19 and not stock_code:
        stock_code = match19.group(1)
    
    # 模式20: 包含"这个股票最近表现"的查询，如"603871这个股票最近表现怎么样，值得投资吗"
    pattern20 = r'(\d{5,6})\s*这个\s*股票\s*最近表现'
    match20 = re.search(pattern20, query)
    if match20 and not stock_code:
        stock_code = match20.group(1)
    
    # 清理公司名称（移除常见的无意义词汇）
    if company_name:
        # 移除常见的无意义词汇
        stop_words = ['的', '这个', '这只', '一下', '看看', '了解', '分析', '帮我', '我想', '给我', '财务状况', '投资价值', '基本面情况', '这只股票', '这个股票']
        for word in stop_words:
            company_name = company_name.replace(word, '').strip()
        
        # 如果公司名称太短（少于2个字符），可能是误匹配
        if len(company_name) < 2:
            company_name = None
    
    return company_name, stock_code

# ============================================================================
# 工作流路由逻辑
# ============================================================================

def router(state: AgentState):
    """根据意图识别结果决定后续路径"""
    intent = state.get("data", {}).get("intent", {})
    
    # 如果不是金融查询，直接结束
    if not intent.get("is_financial_query", True):
        return ["summarizer"]
    
    tasks = intent.get("tasks", [])
    
    # 映射任务到节点名称
    mapping = {
        "fundamental": "fundamental_analyst",
        "technical": "technical_analyst",
        "value": "value_analyst",
        "news": "news_analyst"
    }
    
    destinations = [mapping[t] for t in tasks if t in mapping]
    
    # 如果识别出的任务列表为空，但又是金融查询，则执行所有分析
    if not destinations:
        return ["fundamental_analyst", "technical_analyst", "value_analyst", "news_analyst"]
        
    return destinations

# ============================================================================
# 工作流构建
# ============================================================================

def create_workflow():
    """创建并编译LangGraph工作流"""
    # 创建工作流图，使用AgentState作为状态类型
    workflow = StateGraph(AgentState)

    # 添加核心智能体节点
    workflow.add_node("intent_analyst", intent_agent)           # 意图分析（新增）
    workflow.add_node("fundamental_analyst", fundamental_agent)  # 基本面分析智能体
    workflow.add_node("technical_analyst", technical_agent)      # 技术分析智能体
    workflow.add_node("value_analyst", value_agent)             # 估值分析智能体
    workflow.add_node("news_analyst", news_agent)               # 新闻分析智能体
    workflow.add_node("summarizer", summary_agent)              # 总结智能体

    # 设置工作流入口点为意图分析
    workflow.set_entry_point("intent_analyst")

    # 添加条件边：根据意图路由到不同的分析智能体
    workflow.add_conditional_edges(
        "intent_analyst",
        router,
        {
            "fundamental_analyst": "fundamental_analyst",
            "technical_analyst": "technical_analyst",
            "value_analyst": "value_analyst",
            "news_analyst": "news_analyst",
            "summarizer": "summarizer"
        }
    )

    # 所有分析结果最后汇聚到总结智能体
    workflow.add_edge("fundamental_analyst", "summarizer")
    workflow.add_edge("technical_analyst", "summarizer")
    workflow.add_edge("value_analyst", "summarizer")
    workflow.add_edge("news_analyst", "summarizer")

    # 添加结束边 - 总结智能体完成后结束工作流
    workflow.add_edge("summarizer", END)

    # 编译工作流
    return workflow.compile()

# ============================================================================
# 分析执行引擎
# ============================================================================

async def execute_analysis(user_query, execution_logger=None):
    """
    执行完整的金融分析流程
    
    Args:
        user_query: 用户查询字符串
        execution_logger: 可选的执行日志记录器
        
    Returns:
        final_state: 工作流执行后的最终状态
    """
    if execution_logger is None:
        execution_logger = initialize_execution_logger()
        
    try:
        # 记录分析开始
        execution_logger.log_agent_start("analysis_engine", {"user_query": user_query})
        
        # 1. 准备时间信息
        current_datetime = datetime.now()
        current_date_cn = current_datetime.strftime("%Y年%m月%d日")
        current_date_en = current_datetime.strftime("%Y-%m-%d")
        current_weekday_cn = ["星期一", "星期二", "星期三", "星期四",
                              "星期五", "星期六", "星期日"][current_datetime.weekday()]
        current_time = current_datetime.strftime("%H:%M:%S")
        current_time_info = f"{current_date_cn} ({current_date_en}) {current_weekday_cn} {current_time}"
        
        # 2. 准备初始状态
        initial_data = {
            "query": user_query,
            "current_date": current_date_en,
            "current_date_cn": current_date_cn,
            "current_time": current_time,
            "current_weekday_cn": current_weekday_cn,
            "current_time_info": current_time_info,
            "analysis_timestamp": current_datetime.isoformat()
        }
        
        # 尝试通过正则做初步提取（作为补充，IntentAgent 会做最终决定）
        company_name, stock_code = extract_stock_info(user_query)
        if company_name:
            initial_data["company_name"] = company_name
        if stock_code:
            if stock_code.startswith('6'):
                initial_data["stock_code"] = f"sh.{stock_code}"
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                initial_data["stock_code"] = f"sz.{stock_code}"
            else:
                initial_data["stock_code"] = stock_code

        initial_state = AgentState(
            messages=[],
            data=initial_data,
            metadata={}
        )
        
        # 4. 构建并执行工作流
        app = create_workflow()
        
        logger.info(f"Starting workflow for: {user_query}")
        final_state = await app.ainvoke(initial_state)
        logger.info("Workflow execution completed")
        
        # 5. 记录报告（如果生成了）
        if final_state and final_state.get("data") and "final_report" in final_state["data"]:
            report_content = final_state["data"]["final_report"]
            report_path = final_state["data"].get("report_path", "")
            execution_logger.log_final_report(report_content, report_path)
            
        return final_state
        
    except Exception as e:
        logger.error(f"Error in execute_analysis: {e}", exc_info=True)
        execution_logger.log_agent_error("analysis_engine", str(e))
        raise e

async def main():
    """
    主函数：金融分析智能体系统的核心执行逻辑
    """
    
    # 初始化执行日志系统
    execution_logger = initialize_execution_logger()
    logger.info(
        f"{SUCCESS_ICON} 执行日志系统已初始化，日志目录: {execution_logger.execution_dir}")

    try:
        # ============================================================================
        # 实现命令行界面 
        # ============================================================================
        
        # 创建命令行参数解析器
        parser = argparse.ArgumentParser(description="Financial Agent CLI")
        parser.add_argument(
            "--command",
            type=str,
            required=False,
            help="The user query for financial analysis (e.g., '分析嘉友国际')"
        )
        args = parser.parse_args()

        # 处理用户查询输入
        if args.command:
            user_query = args.command
        else:
            # 显示交互式界面
            print("\n🏦 金融分析智能体系统 (Financial Analysis AI Agent System)\n")
            user_query = input("💬 请输入您的分析需求: ")
            while not user_query.strip():
                user_query = input("请输入您的分析需求: ")

        # 执行分析
        print(f"\n{WAIT_ICON} 正在处理您的请求，这可能需要几分钟，请耐心等待...\n")
        final_state = await execute_analysis(user_query, execution_logger)
        
        # 打印结果
        if final_state and final_state.get("data") and "final_report" in final_state["data"]:
            print(f"\n{SUCCESS_ICON} 分析完成！")
            if "report_path" in final_state["data"]:
                print(f"{SUCCESS_ICON} 报告已保存到: {final_state['data']['report_path']}")
        
        finalize_execution_logger(success=True)

    except Exception as e:
        print(f"\n{ERROR_ICON} 执行失败: {e}")
        finalize_execution_logger(success=False, error=str(e))


# ============================================================================
# 程序入口点
# ============================================================================

if __name__ == "__main__":
    # 使用asyncio运行主函数
    asyncio.run(main())
