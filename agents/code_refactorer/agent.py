"""
Code Refactorer Agent — A2A Server
Takes code + review feedback and produces clean, optimized final code using Google Gemini.
Runs on port 5003.
"""

import os
import sys
import uuid
import logging
from typing import AsyncIterable

import google.generativeai as genai
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    MessageSendParams,
    SendMessageRequest,
    Task,
    TaskState,
    TaskStatus,
    Message,
    Artifact,
    Part,
    TextPart,
    Role,
)
from a2a.utils import new_agent_text_message, new_task


load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are an expert code refactoring specialist. You receive:
1. Original code that was generated
2. A code review with identified issues

Your job is to produce the FINAL, polished version of the code that:

1. Fixes ALL critical and warning issues identified in the review
2. Implements the suggestions from the review where appropriate  
3. Improves code organization, readability, and maintainability
4. Adds proper error handling where missing
5. Adds type hints (for Python) or type annotations (for TypeScript)
6. Ensures proper input validation
7. Follows the language's official style guide
8. Adds comprehensive docstrings/comments

Rules:
- Return ONLY the final refactored code — no explanations outside code.
- The code must be complete and ready to run.
- Wrap code in appropriate markdown code blocks with language tags.
- Add a comment at the top: "# Refactored by AI Code Review Pipeline"
- At the end, add a brief comment block summarizing what was changed.
"""


class CodeRefactorerExecutor(AgentExecutor):
    """Executes code refactoring tasks using Google Gemini."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process a code refactoring request."""
        user_message = context.get_user_input()
        logger.info(f"Code Refactorer received code + review ({len(user_message)} chars)")

        task = context.current_task or new_task(context.message)
        task.status = TaskStatus(state=TaskState.working)
        await event_queue.enqueue_event(task)

        try:
            model = genai.GenerativeModel(
                model_name="models/gemma-4-31b-it",
                system_instruction=SYSTEM_PROMPT
            )

            prompt = f"""Please refactor the following code based on the review feedback provided.

{user_message}

Produce the final, polished, production-ready version of the code."""

            response = model.generate_content(prompt)
            refactored_code = response.text

            task.status = TaskStatus(
                state=TaskState.completed,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text="Code refactoring completed successfully.")]
                )
            )
            task.artifacts = [
                Artifact(
                    artifactId=str(uuid.uuid4()),
                    name="refactored_code",
                    parts=[TextPart(text=refactored_code)]
                )
            ]

        except Exception as e:
            logger.error(f"Code refactoring failed: {e}")
            task.status = TaskStatus(
                state=TaskState.failed,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text=f"Code refactoring failed: {str(e)}")]
                )
            )

        await event_queue.enqueue_event(task)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task:
            task = context.current_task
            task.status = TaskStatus(
                state=TaskState.canceled,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text="Task was cancelled.")]
                )
            )
            await event_queue.enqueue_event(task)


# --- Agent Card ---
AGENT_CARD = AgentCard(
    name="Code Refactorer Agent",
    description="Refactors and optimizes code based on review feedback. Produces clean, production-ready code with all issues fixed.",
    url=f"http://localhost:{os.getenv('CODE_REFACTORER_PORT', '5003')}",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(
        streaming=False,
        pushNotifications=False,
    ),
    skills=[
        AgentSkill(
            id="code-refactoring",
            name="Code Refactoring",
            description="Takes code and review feedback, then produces a clean, optimized, bug-free final version.",
            tags=["code", "refactoring", "optimization", "cleanup"],
        )
    ],
)


from a2a.server.tasks import InMemoryTaskStore

def create_app():
    executor = CodeRefactorerExecutor()
    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )
    app = A2AStarletteApplication(
        agent_card=AGENT_CARD,
        http_handler=request_handler,
    )
    return app.build()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("CODE_REFACTORER_PORT", "5003"))
    logger.info(f"✨ Code Refactorer Agent starting on port {port}...")
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
