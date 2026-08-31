"""ADK agent definition for the All Things Agentic submission."""

from google.adk.agents import Agent


def explain_agent_role() -> str:
    """Describe the IPCC agent's autonomous workflow for the ADK runtime."""
    return "The IPCC research agent retrieves evidence, delegates document analysis, and returns cited findings."


root_agent = Agent(
    name="ipcc_research_agent",
    model="gemini-3.7-flash",
    description="An evidence-grounded climate research agent.",
    instruction=(
        "You are an IPCC climate research agent. Plan multi-step research tasks, "
        "use available evidence, explain uncertainty constructively, and always cite "
        "the reports or passages used."
    ),
    tools=[explain_agent_role],
)
