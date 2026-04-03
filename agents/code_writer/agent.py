"""
Code Writer Agent — A2A Server
Generates code from natural language prompts using Google Gemini.
Runs on port 5001.
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

SYSTEM_PROMPT = """You are an expert software engineer and code writer. 
Your task is to generate clean, well-structured, production-quality code based on the user's request.

Rules:
1. Write complete, working code — not pseudocode or snippets.
2. Include necessary imports and dependencies.
3. Add clear comments explaining the logic.
4. Follow best practices for the language/framework being used.
5. Return ONLY the code. Do not include explanations outside of code comments.
6. If the user doesn't specify a language, use Python.
7. Wrap code in appropriate markdown code blocks with language tags.
"""


class CodeWriterExecutor(AgentExecutor):
    """Executes code generation tasks using Google Gemini."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process a code generation request."""
        # Extract the user's prompt from the context
        user_message = context.get_user_input()
        logger.info(f"Code Writer received prompt: {user_message[:100]}...")
        
        task = context.current_task or new_task(context.message)

        # Update task status to working
        task.status = TaskStatus(state=TaskState.working)
        await event_queue.enqueue_event(task)

        try:
            # Call Gemini to generate code
            model = genai.GenerativeModel(
                model_name="models/gemma-4-31b-it",
                system_instruction=SYSTEM_PROMPT
            )
            
            response = model.generate_content(user_message)
            generated_code = response.text

            # Create artifact with the generated code
            task.status = TaskStatus(
                state=TaskState.completed,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text="Code generation completed successfully.")]
                )
            )
            task.artifacts = [
                Artifact(
                    artifactId=str(uuid.uuid4()),
                    name="generated_code",
                    parts=[TextPart(text=generated_code)]
                )
            ]

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            task.status = TaskStatus(
                state=TaskState.failed,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text=f"Code generation failed: {str(e)}")]
                )
            )

        await event_queue.enqueue_event(task)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel a running task."""
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
    name="Code Writer Agent",
    description="Generates production-quality code from natural language prompts using Google Gemini AI. Supports multiple programming languages and frameworks.",
    url=f"http://localhost:{os.getenv('CODE_WRITER_PORT', '5001')}",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(
        streaming=False,
        pushNotifications=False,
    ),
    skills=[
        AgentSkill(
            id="code-generation",
            name="Code Generation",
            description="Generates complete, working code from a natural language description. Supports Python, JavaScript, TypeScript, Java, Go, Rust, and more.",
            tags=["code", "generation", "programming", "development"],
        )
    ],
)


from a2a.server.tasks import InMemoryTaskStore

def create_app():
    """Create and configure the A2A Starlette application."""
    executor = CodeWriterExecutor()
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
    port = int(os.getenv("CODE_WRITER_PORT", "5001"))
    logger.info(f"🖊️  Code Writer Agent starting on port {port}...")
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
