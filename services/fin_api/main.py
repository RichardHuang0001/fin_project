from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add the fin_agent src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
fin_agent_path = os.path.join(project_root, "services", "fin_agent")
sys.path.insert(0, fin_agent_path)

from src.main import execute_analysis
from src.utils.execution_logger import initialize_execution_logger
from src.utils.logging_config import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="Financial Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    query: str


class AnalysisResponse(BaseModel):
    query: str
    status: str
    report: Optional[str] = None
    report_path: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    fragments: Optional[Dict[str, str]] = None


def format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_analysis_with_logger(query: str, event_sink=None) -> Dict[str, Any]:
    execution_logger = initialize_execution_logger()
    return await execute_analysis(query, execution_logger, event_sink=event_sink)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    try:
        final_state = await run_analysis_with_logger(request.query)
        if final_state and "data" in final_state:
            data = final_state["data"]
            return AnalysisResponse(
                query=request.query,
                status="success",
                report=data.get("final_report"),
                report_path=data.get("report_path"),
                data=data,
            )
        return AnalysisResponse(
            query=request.query,
            status="error",
            error="Analysis failed to generate results",
        )
    except Exception as e:
        logger.error("Synchronous analyze failed: %s", e, exc_info=True)
        return AnalysisResponse(
            query=request.query,
            status="error",
            error=str(e),
        )


@app.post("/api/analyze/stream")
async def analyze_stream(request: AnalysisRequest):
    async def event_generator():
        queue: asyncio.Queue[tuple[str, Dict[str, Any]]] = asyncio.Queue()
        finished = asyncio.Event()

        async def event_sink(event_type: str, payload: Dict[str, Any]):
            await queue.put((event_type, payload))

        async def worker():
            try:
                final_state = await run_analysis_with_logger(request.query, event_sink=event_sink)
                if final_state and "data" in final_state:
                    data = final_state["data"]
                    await queue.put(
                        (
                            "final",
                            {
                                "query": request.query,
                                "status": "success",
                                "report": data.get("final_report"),
                                "report_path": data.get("report_path"),
                                "data": data,
                            },
                        )
                    )
                else:
                    await queue.put(
                        (
                            "error",
                            {
                                "query": request.query,
                                "status": "error",
                                "message": "Analysis failed to generate results",
                            },
                        )
                    )
            except Exception as exc:
                logger.error("Stream analyze failed: %s", exc, exc_info=True)
                await queue.put(
                    (
                        "error",
                        {
                            "query": request.query,
                            "status": "error",
                            "message": str(exc),
                        },
                    )
                )
            finally:
                finished.set()

        task = asyncio.create_task(worker())

        try:
            while True:
                if finished.is_set() and queue.empty():
                    break
                try:
                    event_type, payload = await asyncio.wait_for(queue.get(), timeout=10)
                    yield format_sse(event_type, payload)
                except asyncio.TimeoutError:
                    yield format_sse("ping", {"status": "alive"})
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    import contextlib

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
