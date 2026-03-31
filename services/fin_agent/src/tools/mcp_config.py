"""MCP server configuration for fin_agent."""

import os
import sys
from pathlib import Path

DEFAULT_MCP_DIR = Path(os.getenv('FIN_DATA_SVR_DIR', '/srv/fin/services/fin_data_svr')).resolve()
DEFAULT_MCP_PYTHON = os.getenv('FIN_DATA_SVR_PYTHON', sys.executable)

SERVER_CONFIGS = {
    'a_share_mcp_v2': {
        'command': DEFAULT_MCP_PYTHON,
        'args': [str(DEFAULT_MCP_DIR / 'mcp_server.py')],
        'transport': 'stdio',
    }
}
