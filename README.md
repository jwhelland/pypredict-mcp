# pypredict-mcp

MCP server for predicting satellite transits over a given location.

## Overview

`pypredict-mcp` is a Model Context Protocol (MCP) server that provides tools for satellite tracking and prediction. It allows you to:
- Retrieve satellite names from NORAD IDs
- Retrieve NORAD IDs from satellite names
- Fetch TLE (Two-Line Element) data for satellites
- Predict satellite transits (passes) over a specified location

The server is built using [mcp](https://pypi.org/project/mcp/), [pypredict](https://pypi.org/project/pypredict/), [pydantic](https://pydantic-docs.helpmanual.io/), and other modern Python libraries.

It uses [CelesTrak](https://celestrak.org/) for TLE and name/noradid lookups

## Features

- **Get satellite name from NORAD ID**
- **Get NORAD ID(s) from satellite name**
- **Fetch TLE data for a satellite**
- **Predict upcoming satellite transits for a given latitude/longitude**
- Caching for improved performance

## Installation

You need Python 3.13.1 or newer.

1. Clone this repository:
   ```sh
   git clone <repo-url>
   cd pypredict_mcp
   ```
2. Install dependencies (using [uv](https://github.com/astral-sh/uv) or pip):
   ```sh
   uv pip install -r pyproject.toml
   # or
   pip install .
   ```
3. Setup environment variables with your API keys
   - OPENAI_API_KEY   (https://platform.openai.com/api-keys)
   - GOOGLE_API_KEY   (https://aistudio.google.com/apikey)
   - GEOCODE_API_KEY  (https://geocode.maps.co)

## Usage

You can run the MCP server via:

```sh
uv run src/pypredict_mcp/main.py
```

Or, to inspect with the MCP Inspector:

```sh
npx @modelcontextprotocol/inspector uv run src/pypredict_mcp/main.py
```

### Command-Line Options

You can configure the server's transport method and other settings using command-line options.

- `--transport` or `-t`: The transport to use for the MCP server. Options are `stdio`, `http`, and `sse`. Default is `stdio`.
- `--host` or `-h`: The host to bind the MCP server to. Default is `127.0.0.1`.
- `--port` or `-p`: The port to bind the MCP server to. Default is `8000`.

#### Examples

To run the server with the default `stdio` transport:

```bash
uv run src/pypredict_mcp/main.py
```

To run the server with the `http` transport on port `8080`:

```bash
uv run src/pypredict_mcp/main.py -- --transport http --port 8080
```

You can run the example agent via cli once you've set your API keys:
```sh
uv run agent.py
```

You can run the gradio ui once you've set your API keys:
```sh
uv run app.py
```

## API Tools

The following tools are exposed via MCP:

- `get_name_from_norad_id(norad_id: str) -> str`
- `get_norad_id_from_name(name: str) -> List[str]`
- `get_tle(norad_id: str) -> str`
- `get_transits(norad_id: str, latitude: float, longitude: float, angle_above_horizon: float) -> List[Transit]`
- `get_latitude_longitude_from_location_name(location_name: str) -> str`

### Transit Model

A `Transit` object contains:
- `start_time`: Start time of the transit (UTC)
- `end_time`: End time of the transit (UTC)
- `duration_seconds`: Duration of the transit in seconds

## Development

Install dev dependencies:

```sh
uv pip install -r pyproject.toml --group dev
```

## License

MIT License
