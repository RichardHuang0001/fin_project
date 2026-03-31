import os
from pathlib import Path
from typing import List, Optional

import torch
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

load_dotenv(dotenv_path=Path(__file__).resolve().with_name('.env'))

MODEL_PATH = os.getenv('MODEL_PATH', '/srv/fin/models/dianjin/DianJin-R1-7B')
SERVED_MODEL_NAME = os.getenv('SERVED_MODEL_NAME', 'dianjin')
HOST = os.getenv('LLM_HOST', '127.0.0.1')
PORT = int(os.getenv('LLM_PORT', '6006'))

app = FastAPI(title='fin_llm')
print('Loading tokenizer...')
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
print('Loading model...')
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype='auto', device_map='auto', trust_remote_code=True)
model.eval()
print('Model loaded.')

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512

@app.get('/health')
def health():
    return {'status': 'ok', 'model': SERVED_MODEL_NAME}

@app.get('/v1/models')
def models():
    return {'data': [{'id': SERVED_MODEL_NAME, 'object': 'model'}], 'object': 'list'}

@app.post('/v1/chat/completions')
def chat_completions(req: ChatCompletionRequest):
    if req.model != SERVED_MODEL_NAME:
        return {'error': {'message': f'Model {req.model} not available', 'type': 'invalid_request_error'}}
    messages = [m.model_dump() for m in req.messages]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors='pt').to(model.device)
    max_new_tokens = min(max(req.max_tokens or 512, 1), 1024)
    temperature = req.temperature if req.temperature is not None else 0.7
    do_sample = temperature > 0
    gen_kwargs = {'max_new_tokens': max_new_tokens, 'do_sample': do_sample}
    if do_sample:
        gen_kwargs['temperature'] = max(temperature, 1e-5)
    with torch.no_grad():
        output = model.generate(**inputs, **gen_kwargs)
    generated = output[0][inputs.input_ids.shape[1]:]
    content = tokenizer.decode(generated, skip_special_tokens=True)
    return {
        'id': 'chatcmpl-local-dianjin',
        'object': 'chat.completion',
        'model': SERVED_MODEL_NAME,
        'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
    }

if __name__ == '__main__':
    uvicorn.run(app, host=HOST, port=PORT)
