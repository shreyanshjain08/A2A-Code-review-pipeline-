"""
Orchestrator — A2A Client + FastAPI Server
Coordinates the 3-agent code review pipeline and serves the web UI.
Runs on port 3000.
"""

import os
import json
import time
import uuid
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# Configuration
# ============================================================
AGENT_URLS = {
    "code_writer": f"http://localhost:{os.getenv('CODE_WRITER_PORT', '5001')}",
    "code_reviewer": f"http://localhost:{os.getenv('CODE_REVIEWER_PORT', '5002')}",
    "code_refactorer": f"http://localhost:{os.getenv('CODE_REFACTORER_PORT', '5003')}",
}


# ============================================================
# A2A Client Helper
# ============================================================
class A2AClient:
    """Simple A2A protocol client that sends messages to agents."""

    def __init__(self, agent_url: str):
        self.agent_url = agent_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def get_agent_card(self) -> dict:
        """Fetch the agent's Agent Card for discovery."""
        url = f"{self.agent_url}/.well-known/agent.json"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def send_message(self, text: str, context_id: Optional[str] = None) -> dict:
        """Send a message/send JSON-RPC request to the agent."""
        request_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "id": request_id,
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": text,
                        }
                    ],
                },
            },
        }

        if context_id:
            payload["params"]["configuration"] = {
                "contextId": context_id,
            }

        response = await self.client.post(
            self.agent_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()

    def extract_artifact_text(self, response: dict) -> str:
        """Extract text from A2A response artifacts."""
        try:
            result = response.get("result", {})
            artifacts = result.get("artifacts", [])
            texts = []
            for artifact in artifacts:
                for part in artifact.get("parts", []):
                    if part.get("kind") == "text" or "text" in part:
                        texts.append(part.get("text", ""))
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"Failed to extract artifact text: {e}")
            return ""

    def get_task_state(self, response: dict) -> str:
        """Get the task state from an A2A response."""
        try:
            return response.get("result", {}).get("status", {}).get("state", "unknown")
        except Exception:
            return "unknown"

    def get_task_message(self, response: dict) -> str:
        """Get the task message from an A2A response."""
        try:
            parts = response.get("result", {}).get("status", {}).get("message", {}).get("parts", [])
            for p in parts:
                if "text" in p:
                    return p["text"]
                if p.get("kind") == "text":
                    return p.get("text", "")
            return "No error details."
        except Exception:
            return "Failed to parse error message."


# ============================================================
# Pipeline Logic
# ============================================================
class PipelineResult(BaseModel):
    """Result of the complete code review pipeline."""
    pipeline_id: str
    prompt: str
    generated_code: str
    code_review: str
    refactored_code: str
    agent_cards: dict
    timings: dict
    status: str


async def run_pipeline(prompt: str) -> PipelineResult:
    """
    Run the full code review pipeline:
    1. Code Writer → generates code
    2. Code Reviewer → reviews  the code
    3. Code Refactorer → refactors based on review
    """
    pipeline_id = str(uuid.uuid4())[:8]
    agent_cards = {}
    timings = {}

    writer_client = A2AClient(AGENT_URLS["code_writer"])
    reviewer_client = A2AClient(AGENT_URLS["code_reviewer"])
    refactorer_client = A2AClient(AGENT_URLS["code_refactorer"])

    try:
        # ── Step 1: Discover Agents ──
        logger.info(f"[{pipeline_id}] 🔍 Discovering agents...")
        t0 = time.time()
        try:
            agent_cards["code_writer"] = await writer_client.get_agent_card()
            agent_cards["code_reviewer"] = await reviewer_client.get_agent_card()
            agent_cards["code_refactorer"] = await refactorer_client.get_agent_card()
            timings["discovery"] = round(time.time() - t0, 2)
            logger.info(f"[{pipeline_id}] ✅ All 3 agents discovered ({timings['discovery']}s)")
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Agent discovery failed. Make sure all agents are running. Error: {str(e)}"
            )

        # ── Step 2: Code Generation ──
        logger.info(f"[{pipeline_id}] 🖊️  Sending prompt to Code Writer...")
        t1 = time.time()
        writer_response = await writer_client.send_message(prompt)
        timings["code_generation"] = round(time.time() - t1, 2)

        writer_state = writer_client.get_task_state(writer_response)
        generated_code = writer_client.extract_artifact_text(writer_response)

        if writer_state != "completed" or not generated_code:
            error_msg = writer_client.get_task_message(writer_response)
            raise HTTPException(
                status_code=500,
                detail=f"Code Writer failed. State: {writer_state}. Details: {error_msg}"
            )
        logger.info(f"[{pipeline_id}] ✅ Code generated ({timings['code_generation']}s, {len(generated_code)} chars)")

        # ── Step 3: Code Review ──
        logger.info(f"[{pipeline_id}] 🔍 Sending code to Code Reviewer...")
        t2 = time.time()
        reviewer_response = await reviewer_client.send_message(
            f"Please review the following code:\n\n{generated_code}"
        )
        timings["code_review"] = round(time.time() - t2, 2)

        reviewer_state = reviewer_client.get_task_state(reviewer_response)
        code_review = reviewer_client.extract_artifact_text(reviewer_response)

        if reviewer_state != "completed" or not code_review:
            error_msg = reviewer_client.get_task_message(reviewer_response)
            raise HTTPException(
                status_code=500,
                detail=f"Code Reviewer failed. State: {reviewer_state}. Details: {error_msg}"
            )
        logger.info(f"[{pipeline_id}] ✅ Code reviewed ({timings['code_review']}s)")

        # ── Step 4: Code Refactoring ──
        logger.info(f"[{pipeline_id}] ✨ Sending code + review to Code Refactorer...")
        t3 = time.time()
        refactor_prompt = f"""## Original Code:
{generated_code}

## Code Review Feedback:
{code_review}

Please refactor the code fixing all issues mentioned in the review."""

        refactorer_response = await refactorer_client.send_message(refactor_prompt)
        timings["code_refactoring"] = round(time.time() - t3, 2)

        refactorer_state = refactorer_client.get_task_state(refactorer_response)
        refactored_code = refactorer_client.extract_artifact_text(refactorer_response)

        if refactorer_state != "completed" or not refactored_code:
            error_msg = refactorer_client.get_task_message(refactorer_response)
            raise HTTPException(
                status_code=500,
                detail=f"Code Refactorer failed. State: {refactorer_state}. Details: {error_msg}"
            )
        logger.info(f"[{pipeline_id}] ✅ Code refactored ({timings['code_refactoring']}s)")

        timings["total"] = round(sum(v for v in timings.values()), 2)

        return PipelineResult(
            pipeline_id=pipeline_id,
            prompt=prompt,
            generated_code=generated_code,
            code_review=code_review,
            refactored_code=refactored_code,
            agent_cards={k: v.get("name", k) for k, v in agent_cards.items()},
            timings=timings,
            status="completed",
        )

    finally:
        await writer_client.close()
        await reviewer_client.close()
        await refactorer_client.close()


# ============================================================
# FastAPI Application
# ============================================================
app = FastAPI(
    title="A2A Code Review Pipeline",
    description="Multi-agent code review pipeline using Google A2A protocol",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")


class PipelineRequest(BaseModel):
    prompt: str


@app.get("/")
async def serve_frontend():
    """Serve the main web UI."""
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.post("/api/pipeline")
async def execute_pipeline(request: PipelineRequest):
    """Execute the full code review pipeline."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    logger.info(f"Pipeline request: {request.prompt[:100]}...")
    result = await run_pipeline(request.prompt)
    return result


@app.get("/api/health")
async def health_check():
    """Check health of all agents."""
    statuses = {}
    for name, url in AGENT_URLS.items():
        try:
            client = A2AClient(url)
            card = await client.get_agent_card()
            statuses[name] = {
                "status": "online",
                "name": card.get("name", name),
                "url": url,
            }
            await client.close()
        except Exception as e:
            statuses[name] = {
                "status": "offline",
                "error": str(e),
                "url": url,
            }
    return {"agents": statuses}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ORCHESTRATOR_PORT", "3000"))
    logger.info(f"🚀 Orchestrator starting on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
