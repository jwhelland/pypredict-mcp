import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents import Agent, Runner, trace, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio, MCPServerStdioParams
import asyncio

# NOTE: Ensure you have defined OPENAI_API_KEY in your .env file or environment variables.
load_dotenv(override=True)

google_api_key = os.getenv("GOOGLE_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI()

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

    params = MCPServerStdioParams(command="uv", args=["run", "main.py"])
    instructions = (
        "You are a satellite tracking agent. "
        "Use the MCP tools to calculate transits for satellites. Do not use any other tools and DO NOT make up answers."
    )

    # model = "gpt-4.1-mini"
    model = "gemini-2.5-flash"
    
    async with MCPServerStdio(params=params, client_session_timeout_seconds=30) as mcp_server:
        agent = Agent(name="SatelliteTracker", instructions=instructions, model=get_model(model), mcp_servers=[mcp_server])
        with trace("SatelliteTrackingTrace"):
            # Run the agent with the request, view the trace in the OPENAI dashboard
            response = await Runner.run(agent, request)
            print("Agent response:", response.final_output)
    return response.final_output

if __name__ == "__main__":
    asyncio.run(main("Get transits for the ISS (NORAD ID 25544) at Fairfax, Virginia, USA"))