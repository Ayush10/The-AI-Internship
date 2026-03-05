"""Returns A2A Service — standalone agent exposed via to_a2a() on port 8001."""

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .tools import check_return_eligibility, initiate_return

MODEL = "gemini-2.5-flash"

returns_agent = Agent(
    model=MODEL,
    name="returns_agent",
    description="Handles product return requests. Can check return eligibility and initiate returns with RMA numbers.",
    instruction="""You are a returns specialist agent. When a customer asks about returning an order:

1. First use check_return_eligibility to verify the order can be returned.
2. Present the eligibility result clearly to the customer.
3. If eligible and the customer confirms they want to proceed, use initiate_return to process it.
4. Always provide the RMA number and full return instructions.
5. If not eligible, explain why clearly and suggest alternatives (contact support, warranty claim, etc.).

Be helpful, clear, and empathetic. Returning a product can be frustrating — make the process as smooth as possible.""",
    tools=[check_return_eligibility, initiate_return],
)

# Expose as A2A service
a2a_app = to_a2a(returns_agent, port=8001)
