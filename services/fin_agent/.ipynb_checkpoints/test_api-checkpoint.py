
import requests
import json

def test_dianjin():
    url = "http://127.0.0.1:6006/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "model": "dianjin",
        "messages": [
            {"role": "user", "content": "请简要分析嘉友国际(603871)的核心竞争力是什么？"}
        ],
        "temperature": 0.7
    }

    print("--- 正在发送金融分析请求 ---")
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"\n模型回答：\n{content}")
    else:
        print(f"请求失败，状态码：{response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_dianjin()