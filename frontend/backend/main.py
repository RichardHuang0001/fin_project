from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import asyncio
from typing import Optional, List, Dict, Any

# Add the fin_agent src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
fin_agent_path = os.path.join(project_root, "services", "fin_agent")
sys.path.insert(0, fin_agent_path)

# Import the refactored functions from fin_agent
try:
    from src.main import execute_analysis
    from src.utils.execution_logger import initialize_execution_logger
except ImportError as e:
    print(f"Error importing from fin_agent: {e}")
    print(f"Path searched: {fin_agent_path}")
    # Fallback or exit
    raise e

app = FastAPI(title="Financial Agent API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend URL
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

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    # Offload the heavy analysis task to a separate thread to keep the API responsive
    return await asyncio.to_thread(sync_analyze, request)

def sync_analyze(request: AnalysisRequest):
    # Create a new event loop for this thread since execute_analysis is async
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(do_analyze(request))
    finally:
        loop.close()

async def do_analyze(request: AnalysisRequest):
    try:
        # Initialize a new logger for this request
        execution_logger = initialize_execution_logger()
        
        # Execute the analysis workflow
        final_state = await execute_analysis(request.query, execution_logger)
        
        if final_state and "data" in final_state:
            data = final_state["data"]
            return AnalysisResponse(
                query=request.query,
                status="success",
                report=data.get("final_report"),
                report_path=data.get("report_path"),
                data=data
            )
        else:
            return AnalysisResponse(
                query=request.query,
                status="error",
                error="Analysis failed to generate results"
            )
    except Exception as e:
        return AnalysisResponse(
            query=request.query,
            status="error",
            error=str(e)
        )

@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
