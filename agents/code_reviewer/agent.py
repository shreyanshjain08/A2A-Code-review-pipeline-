"""
Code Reviewer Agent — A2A Server
Reviews code for bugs, security issues, and best practices using Google Gemini.
Runs on port 5002.
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

SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices, security vulnerabilities, and performance optimization.

Your task is to thoroughly review the provided code and give a detailed review report.

Your review MUST include these sections:

## 🔍 Code Review Report

### Summary
A brief 1-2 sentence summary of the code and its purpose.

### Issues Found

For each issue, use this format:
- 🔴 **CRITICAL**: [description] — Issues that will cause bugs, crashes, or security vulnerabilities
- 🟡 **WARNING**: [description] — Issues that could cause problems or are bad practices  
- 🔵 **INFO**: [description] — Suggestions for improvement, style, or readability

### Security Analysis
Check for common security vulnerabilities:
- SQL injection, XSS, CSRF
- Hardcoded credentials or secrets
- Input validation issues
- Authentication/authorization flaws

### Performance Notes
- Any obvious performance bottlenecks
- Unnecessary complexity
- Memory leak potential

### Best Practices
- Code organization and structure
- Error handling
- Naming conventions
- Documentation/comments quality

### Score
Give an overall code quality score from 1-10 with brief justification.

Be specific. Reference exact line numbers or code snippets when pointing out issues.
"""


class CodeReviewerExecutor(AgentExecutor):
    """Executes code review tasks using Google Gemini."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Process a code review request."""
        user_message = context.get_user_input()
        logger.info(f"Code Reviewer received code to review ({len(user_message)} chars)")

        task = context.current_task or new_task(context.message)
        task.status = TaskStatus(state=TaskState.working)
        await event_queue.enqueue_event(task)

        try:
            model = genai.GenerativeModel(
                model_name="models/gemma-4-31b-it",
                system_instruction=SYSTEM_PROMPT
            )

            prompt = f"Please review the following code thoroughly:\n\n{user_message}"
            response = model.generate_content(prompt)
            review_result = response.text

            task.status = TaskStatus(
                state=TaskState.completed,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text="Code review completed successfully.")]
                )
            )
            task.artifacts = [
                Artifact(
                    artifactId=str(uuid.uuid4()),
                    name="code_review",
                    parts=[TextPart(text=review_result)]
                )
            ]

        except Exception as e:
            logger.error(f"Code review failed: {e}")
            task.status = TaskStatus(
                state=TaskState.failed,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text=f"Code review failed: {str(e)}")]
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
    name="Code Reviewer Agent",
    description="Reviews code for bugs, security vulnerabilities, performance issues, and best practice violations. Provides detailed feedback with severity ratings.",
    url=f"http://localhost:{os.getenv('CODE_REVIEWER_PORT', '5002')}",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(
        streaming=False,
        pushNotifications=False,
    ),
    skills=[
        AgentSkill(
            id="code-review",
            name="Code Review",
            description="Performs thorough code review including bug detection, security analysis, performance review, and best practice checking.",
            tags=["code", "review", "security", "bugs", "quality"],
        )
    ],
)


from a2a.server.tasks import InMemoryTaskStore

def create_app():
    executor = CodeReviewerExecutor()
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
    port = int(os.getenv("CODE_REVIEWER_PORT", "5002"))
    logger.info(f"🔍 Code Reviewer Agent starting on port {port}...")
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
