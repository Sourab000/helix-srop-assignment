"""
AccountAgent — provides account-related information.
"""
from google.adk.agents import LlmAgent

from app.agents.tools.account_tools import create_ticket, get_account_status, get_recent_builds
from app.settings import settings

ACCOUNT_INSTRUCTION = """
You are a Helix account assistant. Use the available tools to look up build history and account status. Present data clearly. Always use the user_id from session context.
"""

account_agent = LlmAgent(
    name="account_agent",
    model=settings.adk_model,
    instruction=ACCOUNT_INSTRUCTION,
    tools=[get_recent_builds, get_account_status, create_ticket],
)
