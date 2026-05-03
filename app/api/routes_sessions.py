"""
POST /v1/sessions — create a session.
"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import get_db
from app.srop.state import SessionState

router = APIRouter(tags=["sessions"])


class CreateSessionRequest(BaseModel):
    user_id: str
    plan_tier: str = "free"


class CreateSessionResponse(BaseModel):
    session_id: str
    user_id: str


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateSessionResponse:
    """
    Create a new session. Initialize SessionState and persist to DB.
    """
    session_id = str(uuid.uuid4())

    # Initialize session state
    initial_state = SessionState(
        user_id=body.user_id,
        plan_tier=body.plan_tier,  # type: ignore
    )

    session = Session(
        id=session_id,
        user_id=body.user_id,
        plan_tier=body.plan_tier,
        state=initial_state.to_db_dict(),
    )

    db.add(session)
    await db.commit()

    return CreateSessionResponse(session_id=session_id, user_id=body.user_id)
