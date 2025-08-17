import gradio as gr
from gradio.themes import Glass

from pypredict_mcp.agent import main

js_func = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

async def run_agent(message, history):
    return await main(message)

gr.ChatInterface(
    fn=run_agent, 
    type="messages",
    theme=Glass(),
    js=js_func,
    title="Satellite Tracking Agent",
    description=(
        "Ask the agent to calculate transits for satellites."
        "<br>You can specify the satellite by its NORAD ID or name, and provide a location by latitude/longitude or a place name."
        "<br>Examples:"
        "<br>- Get transit times and the satellite name for norad id 25544 over London, UK and output in a markdown table"
        "<br>- What is the norad id for 'NOAA 15'"
        "<br>- What is the satellite name for norad id 25338"
    )
)

if __name__ == "__main__":
    # To run the app, use `uv run examples/app.py` from the root directory.
    app.launch(inbrowser=True)