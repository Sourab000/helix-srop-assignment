"""
SROP entrypoint — called by the message route.

This simplified pipeline uses direct LLM calls instead of ADK to avoid version issues.
"""
import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any

from groq import Groq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import SessionNotFoundError
from app.db.models import AgentTrace, Message
from app.db.models import Session as DbSession
from app.settings import settings
from app.srop.state import SessionState


@dataclass
class PipelineResult:
    content: str
    routed_to: str
    trace_id: str


def determine_routing(user_message: str) -> str:
    """Determine which agent should handle the request based on message content."""
    msg_lower = user_message.lower()

    if any(kw in msg_lower for kw in ['how', 'what', 'explain', 'docs', 'document', 'guide', 'setup', 'configure', 'use']):
        return "knowledge"
    elif any(kw in msg_lower for kw in ['build', 'status', 'account', 'usage', 'plan', 'deploy', 'ticket']):
        return "account"
    elif any(kw in msg_lower for kw in ['escalate', 'urgent', 'help', 'issue', 'problem']):
        return "escalation"
    else:
        return "smalltalk"


async def call_llm(prompt: str, tools: list | None = None) -> str:
    """Call the LLM directly via Groq."""
    client = Groq(api_key=settings.groq_api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


async def run(session_id: str, user_message: str, db: AsyncSession) -> PipelineResult:
    trace_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    # 1. Load session from DB
    stmt = select(DbSession).where(DbSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")

    # Load session state
    state_dict = session.state.copy() if session.state else {}
    state_dict.setdefault("user_id", session.user_id)
    state_dict.setdefault("plan_tier", session.plan_tier)

    state = SessionState.from_db_dict(state_dict)

    # 2. Determine routing
    routed_to = determine_routing(user_message)
    tool_calls_list: list[dict[str, Any]] = []
    retrieved_chunk_ids: list[str] = []
    content = ""

    try:
        if routed_to == "knowledge":
            from app.agents.tools.search_docs import search_docs
            docs = await search_docs(user_message, k=3)

            if docs:
                context = "\n\n".join([
                    f"[{d['chunk_id']}] {d['content'][:500]}"
                    for d in docs
                ])
                for d in docs:
                    if d.get("chunk_id"):
                        retrieved_chunk_ids.append(d["chunk_id"])

                tool_calls_list.append({
                    "name": "search_docs",
                    "args": {"query": user_message},
                    "result": docs,
                })

                prompt = f"""Based on the following documentation, answer the user's question.

Documentation:
{context}

User question: {user_message}

Provide a helpful answer citing the source IDs like [chunk_id] where applicable."""
            else:
                prompt = user_message

        elif routed_to == "account":
            from app.agents.tools.account_tools import get_account_status, get_recent_builds

            builds = get_recent_builds(session.user_id, limit=3)
            status = get_account_status(session.user_id)

            tool_calls_list.append({
                "name": "get_recent_builds",
                "args": {"user_id": session.user_id},
                "result": builds,
            })
            tool_calls_list.append({
                "name": "get_account_status",
                "args": {"user_id": session.user_id},
                "result": status,
            })

            prompt = f"""Based on the following account information, answer the user's question.

Builds: {builds}

Account Status: {status}

User question: {user_message}

Provide a clear, helpful answer."""
        elif routed_to == "escalation":
            from app.agents.tools.account_tools import create_ticket

            ticket = await create_ticket(
                session.user_id,
                user_message,
                "medium",
                session_id,
            )

            tool_calls_list.append({
                "name": "create_ticket",
                "args": {"summary": user_message},
                "result": ticket,
            })

            prompt = f"""The user wants to escalate an issue. Create a support ticket.

User issue: {user_message}

Ticket created: {ticket['ticket_id']}

Acknowledge the ticket creation and provide the ticket ID."""
        else:
            prompt = user_message

        # Call LLM with timeout
        try:
            content = await asyncio.wait_for(
                call_llm(prompt),
                timeout=settings.llm_timeout_seconds,
            )
        except TimeoutError:
            content = "Sorry, the request took too long. Please try again."
            routed_to = "error"
        except Exception as e:
            error_msg = str(e)
            if "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                content = "The service is temporarily unavailable due to high demand. Please try again in a few moments."
                routed_to = "error"
            else:
                content = f"An error occurred: {error_msg}"
                routed_to = "error"

    except Exception as e:
        content = f"An error occurred: {str(e)}"
        routed_to = "error"

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # 3. Record the trace
    trace = AgentTrace(
        id=trace_id,
        session_id=session_id,
        routed_to=routed_to,
        tool_calls=tool_calls_list,
        retrieved_chunk_ids=retrieved_chunk_ids,
        latency_ms=latency_ms,
    )
    db.add(trace)

    # 4. Update session state
    if routed_to not in ("smalltalk", "error"):
        state.last_agent = routed_to
    state.turn_count += 1
    session.state = state.to_db_dict()

    # 5. Save user message
    db.add(Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=user_message,
    ))

    # 6. Save assistant message
    db.add(Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=content,
    ))

    await db.commit()

    return PipelineResult(
        content=content,
        routed_to=routed_to,
        trace_id=trace_id
    )
