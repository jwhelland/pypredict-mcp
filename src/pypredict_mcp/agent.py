from openai import AsyncOpenAI

from agents import Agent, Runner, trace, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio, MCPServerStdioParams
import asyncio

from .config import settings

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=settings.google_api_key)

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

def get_model(model_name: str) -> OpenAIChatCompletionsModel:
    """
    Returns the appropriate model based on the model name.
    If the model name contains "gemini", it returns an OpenAIChatCompletionsModel
    configured for Gemini, otherwise it returns the default OpenAI model.
    """
    if "gemini" in model_name:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=gemini_client)
    else:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=openai_client)

async def main(request: str) -> str:

    params = MCPServerStdioParams(
        command="uv", args=["run", "-m", "pypredict_mcp.main"]
    )
    
    async with MCPServerStdio(params=params, client_session_timeout_seconds=30) as mcp_server:
        agent = Agent(
            name="SatelliteTracker",
            instructions=settings.agent_instructions,
            model=get_model(settings.agent_model),
            mcp_servers=[mcp_server]
        )
        with trace("SatelliteTrackingTrace"):
            # Run the agent with the request, view the trace in the OPENAI dashboard
            response = await Runner.run(agent, request)
            print("Agent response:", response.final_output)
    return response.final_output

if __name__ == "__main__":
    # This script is intended to be run as a module, not directly.
    # To run the agent, use `uv run pypredict_mcp.agent` from the root directory.
    asyncio.run(main("Get transits for the ISS (NORAD ID 25544) at Fairfax, Virginia, USA"))