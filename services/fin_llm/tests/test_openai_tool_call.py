import json
import os
import requests

base_url = os.getenv('BASE_URL', 'http://127.0.0.1:6006/v1')
url = f"{base_url}/chat/completions"
headers = {'Content-Type': 'application/json'}
payload = {
    'model': os.getenv('MODEL_NAME', 'dianjin'),
    'messages': [{'role': 'user', 'content': '请调用 get_stock_basic_info 工具查询 600000 的基本信息，不要直接回答。'}],
    'tools': [{
        'type': 'function',
        'function': {
            'name': 'get_stock_basic_info',
            'description': '获取股票基本信息',
            'parameters': {
                'type': 'object',
                'properties': {'code': {'type': 'string', 'description': '股票代码'}},
                'required': ['code']
            }
        }
    }],
    'tool_choice': {'type': 'function', 'function': {'name': 'get_stock_basic_info'}},
    'temperature': 0.0,
    'max_tokens': 64,
}
resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
print('status=', resp.status_code)
print(resp.text)
resp.raise_for_status()
body = resp.json()
assert body['choices'][0]['message'].get('tool_calls'), body
print('tool_call_ok')
