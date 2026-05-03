"""
GET /v1/traces/{trace_id} — return the structured trace for one pipeline turn.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import TraceNotFoundError
from app.db.models import AgentTrace
from app.db.session import get_db

router = APIRouter(tags=["traces"])


class ToolCallRecord(BaseModel):
    tool_name: str
    args: dict
    result: dict | str | None


class TraceResponse(BaseModel):
    trace_id: str
    session_id: str
    routed_to: str
    tool_calls: list[ToolCallRecord]
    retrieved_chunk_ids: list[str]
    latency_ms: int


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
) -> TraceResponse:
    """
    Return trace for one turn. 404 if not found.
    """
    stmt = select(AgentTrace).where(AgentTrace.id == trace_id)
    result = await db.execute(stmt)
    trace = result.scalar_one_or_none()

    if not trace:
        raise TraceNotFoundError(f"Trace {trace_id} not found")

    tool_calls = []
    if trace.tool_calls:
        for tc in trace.tool_calls:
            if isinstance(tc, dict):
                raw_result = tc.get("result")
                if not isinstance(raw_result, (dict, str, type(None))):
                    raw_result = str(raw_result)
                tool_calls.append(ToolCallRecord(
                    tool_name=tc.get("name", "unknown"),
                    args=tc.get("args", {}),
                    result=raw_result,
                ))
            else:
                tool_calls.append(ToolCallRecord(
                    tool_name="unknown",
                    args={},
                    result=None,
                ))

    return TraceResponse(
        trace_id=trace.id,
        session_id=trace.session_id,
        routed_to=trace.routed_to,
        tool_calls=tool_calls,
        retrieved_chunk_ids=trace.retrieved_chunk_ids or [],
        latency_ms=trace.latency_ms,
    )