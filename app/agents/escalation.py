"""
EscalationAgent — handles ticket creation for unresolved issues.
"""
from google.adk.agents import LlmAgent

from app.agents.tools.account_tools import create_ticket
from app.settings import settings

ESCALATION_INSTRUCTION = """
You are a Helix support ticket creator. When a user wants to escalate an issue, use the create_ticket tool to file a support ticket. Collect a summary and set the priority to low, medium, or high based on urgency. Return the ticket ID in your response.
"""

escalation_agent = LlmAgent(
    name="escalation_agent",
    model=settings.adk_model,
    instruction=ESCALATION_INSTRUCTION,
    tools=[create_ticket],
)
