# #!/usr/bin/env bash
# set -euo pipefail
# set -a
# source /srv/fin/config/fin_agent.env
# set +a
# cd /srv/fin/services/fin_agent
# PYTHON_BIN="${FIN_AGENT_PYTHON:-python}"
# export PYTHONPATH="/srv/fin/services/fin_agent:${PYTHONPATH:-}"
# exec "$PYTHON_BIN" -m src.main "$@"

#!/usr/bin/env bash
##############################################################################
# 脚本功能：启动 fin_agent 服务
# 改造点：
# 1. 增强错误处理与友好提示
# 2. 增加关键依赖/文件检查
# 3. 补充日志输出（可选文件日志）
# 4. 增加脚本帮助信息
# 5. 规范化路径与变量管理
# 6. 支持调试模式/后台运行（可选）
##############################################################################

# ======================== 基础配置（可根据实际需求调整） ========================
# 环境文件路径
ENV_FILE="/srv/fin/config/fin_agent.env"
# 服务工作目录
WORK_DIR="/srv/fin/services/fin_agent"
# 日志文件路径（可选，为空则仅输出到控制台）
LOG_FILE="/var/log/fin_agent/start.log"
# 默认Python二进制名称
DEFAULT_PYTHON="python3"  # 建议显式指定python3，避免系统python2兼容问题

# ======================== 工具函数 ========================
# 日志输出函数（带时间戳）
log() {
    local level=$1
    local msg=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    local log_content="[$timestamp] [$level] $msg"
    
    # 输出到控制台
    echo -e "$log_content"
    # 如果配置了日志文件，同时写入文件
    if [ -n "$LOG_FILE" ]; then
        mkdir -p $(dirname "$LOG_FILE")
        echo -e "$log_content" >> "$LOG_FILE"
    fi
}

# 错误退出函数
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# 显示帮助信息
show_help() {
    cat << EOF
用法: $0 [选项] [-- Python脚本参数...]

选项:
  -h, --help          显示此帮助信息
  -d, --debug         启用调试模式（不启用set -e，输出更多日志）
  -b, --background    后台运行服务（需配置LOG_FILE才能查看输出）
  --python <path>     指定Python二进制路径（优先级高于环境变量FIN_AGENT_PYTHON）

示例:
  # 正常启动
  $0
  
  # 调试模式启动，传递自定义参数给Python脚本
  $0 -d -- --env=test --port=8080
  
  # 指定Python3.9启动，后台运行
  $0 --python /usr/bin/python3.9 -b
EOF
}

# ======================== 解析命令行参数 ========================
# 初始化参数变量
DEBUG_MODE=0
BACKGROUND=0
CUSTOM_PYTHON=""
PYTHON_ARGS=()

# 解析参数（处理短选项/长选项）
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--debug)
            DEBUG_MODE=1
            shift
            ;;
        -b|--background)
            BACKGROUND=1
            shift
            ;;
        --python)
            CUSTOM_PYTHON="$2"
            shift 2
            ;;
        --)
            # 分隔符后所有参数传递给Python脚本
            shift
            PYTHON_ARGS=("$@")
            break
            ;;
        *)
            # 未匹配的参数默认传递给Python脚本
            PYTHON_ARGS+=("$1")
            shift
            ;;
    esac
done

# ======================== 调试模式处理 ========================
if [ $DEBUG_MODE -eq 1 ]; then
    log "DEBUG" "启用调试模式，禁用严格模式"
    set -uo pipefail  # 调试模式下关闭set -e，避免脚本因单行错误退出
    set -x  # 输出执行的每一条命令（调试用）
else
    # 原始严格模式（保证脚本健壮性）
    set -euo pipefail
fi

# ======================== 前置检查 ========================
# 检查环境文件是否存在
if [ ! -f "$ENV_FILE" ]; then
    error_exit "环境文件不存在: $ENV_FILE"
fi

# 检查工作目录是否存在
if [ ! -d "$WORK_DIR" ]; then
    error_exit "工作目录不存在: $WORK_DIR"
fi

# 确定Python二进制路径（优先级：命令行指定 > 环境变量 > 默认值）
set -a  # 自动导出变量
source "$ENV_FILE"
set +a

PYTHON_BIN=""
if [ -n "$CUSTOM_PYTHON" ]; then
    PYTHON_BIN="$CUSTOM_PYTHON"
elif [ -n "${FIN_AGENT_PYTHON:-}" ]; then
    PYTHON_BIN="$FIN_AGENT_PYTHON"
else
    PYTHON_BIN="$DEFAULT_PYTHON"
fi

# 检查Python是否可执行
if ! command -v "$PYTHON_BIN" &> /dev/null; then
    error_exit "Python二进制文件不可用: $PYTHON_BIN（请检查路径或环境变量）"
fi
log "INFO" "使用Python路径: $PYTHON_BIN"

# ======================== 启动服务 ========================
# 切换到工作目录
cd "$WORK_DIR" || error_exit "无法切换到工作目录: $WORK_DIR"
log "INFO" "切换到工作目录: $WORK_DIR"

# 设置PYTHONPATH
export PYTHONPATH="$WORK_DIR:${PYTHONPATH:-}"
log "INFO" "设置PYTHONPATH: $PYTHONPATH"

# 构建启动命令
START_CMD=("$PYTHON_BIN" -m src.main "${PYTHON_ARGS[@]}")
log "INFO" "启动命令: ${START_CMD[*]}"

# 执行启动命令（支持后台运行）
if [ $BACKGROUND -eq 1 ]; then
    log "INFO" "后台运行fin_agent服务，日志文件: $LOG_FILE"
    nohup "${START_CMD[@]}" > /dev/null 2>&1 &
    # 可选：输出进程ID
    log "INFO" "服务启动成功，PID: $!"
else
    log "INFO" "前台运行fin_agent服务..."
    exec "${START_CMD[@]}"
fi