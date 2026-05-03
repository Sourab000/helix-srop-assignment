"""
Account tools.

Provides functions to retrieve account status and build information.
"""
from datetime import datetime


def get_recent_builds(user_id: str, limit: int = 5) -> list[dict]:
    """
    Get recent builds for a user.
    
    Args:
        user_id: The user ID to query
        limit: Maximum number of builds to return
    
    Returns:
        List of dicts with build_id, status, branch, commit_sha, duration_seconds, created_at
    """
    builds = []

    for i in range(limit):
        build_id = f"build_{i}_{abs(hash(user_id + str(i)) % 1000)}"

        # Deterministic status based on user_id + build_id
        status_hash = abs(hash(build_id)) % 3
        status = "success" if status_hash == 0 else "failed" if status_hash == 1 else "running"

        # Deterministic branch
        branch = "main" if i % 2 == 0 else "develop"

        builds.append({
            "build_id": build_id,
            "status": status,
            "branch": branch,
            "commit_sha": f"sha_{abs(hash(user_id + str(i))) % 100000:07x}",
            "duration_seconds": (abs(hash(build_id)) % 600) + 60,
            "created_at": datetime.utcnow().isoformat(),
        })

    return builds


def get_account_status(user_id: str) -> dict:
    """
    Get account status for a user.
    
    Args:
        user_id: The user ID to query
    
    Returns:
        Dict with user_id, plan_tier, seats_used, seats_total, api_calls_this_month, storage_gb_used, deploy_keys_count
    """
    # Deterministic based on user_id
    user_hash = abs(hash(user_id))

    plan_tier = "enterprise" if user_hash % 2 == 0 else "pro"
    seats_used = (user_hash % 10) + 1
    seats_total = 20 if plan_tier == "pro" else 100
    api_calls = (user_hash % 1000) + 100
    storage_gb = round((user_hash % 100) / 10.0, 1)
    deploy_keys = (user_hash % 5) + 1

    return {
        "user_id": user_id,
        "plan_tier": plan_tier,
        "seats_used": seats_used,
        "seats_total": seats_total,
        "api_calls_this_month": api_calls,
        "storage_gb_used": storage_gb,
        "deploy_keys_count": deploy_keys,
    }


async def create_ticket(user_id: str, summary: str, priority: str, session_id: str) -> dict:
    """
    Create a support ticket.
    
    Args:
        user_id: The user ID
        summary: Ticket summary/description
        priority: Priority level (low, medium, high)
        session_id: The session ID
    
    Returns:
        Dict with ticket_id, user_id, summary, priority, created_at
    """
    # This would normally write to the database
    # For now, return a mock response
    ticket_id = f"TKT-{abs(hash(user_id + summary + session_id)) % 10000:04d}"

    return {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "summary": summary,
        "priority": priority,
        "created_at": datetime.utcnow().isoformat(),
    }
