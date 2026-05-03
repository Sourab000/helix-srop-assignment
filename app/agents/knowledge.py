"""
KnowledgeAgent — answers questions about Helix products using RAG.
"""
from google.adk.agents import LlmAgent

from app.agents.tools.search_docs import search_docs
from app.settings import settings

KNOWLEDGE_INSTRUCTION = """
You are a Helix product knowledge assistant. When answering, always call search_docs to retrieve relevant documentation. You MUST cite chunk IDs in your answer using the format [chunk_id]. Never answer from memory alone — always retrieve first.
"""

knowledge_agent = LlmAgent(
    name="knowledge_agent",
    model=settings.adk_model,
    instruction=KNOWLEDGE_INSTRUCTION,
    tools=[search_docs],
)
