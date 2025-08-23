import time
from datetime import datetime
from typing import List
from urllib.parse import quote_plus

import httpx
import predict
from cachetools import LRUCache, TTLCache, cached
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, NaiveDatetime

from .config import settings
from .exceptions import APIError, ConfigurationError, NoDataFoundError

mcp = FastMCP("pypredict-mcp")

class Transit(BaseModel):
    """
    A class to represent a satellite transit.
    """

    start_time: NaiveDatetime = Field(
        ..., description="The start time of the transit in UTC."
    )
    end_time: NaiveDatetime = Field(
        ..., description="The end time of the transit in UTC."
    )
    duration_seconds: float = Field(
        ..., description="The duration of the transit in seconds."
    )
    max_elevation: float = Field(
        ..., description="The maximum elevation of the transit in degrees."
    )
    culmination_time: NaiveDatetime = Field(
        ..., description="The time of maximum elevation in UTC."
    )
    start_azimuth: float = Field(
        ..., description="The azimuth of the satellite at the start of the transit in degrees."
    )
    max_elevation_azimuth: float = Field(
        ..., description="The azimuth of the satellite at maximum elevation in degrees."
    )
    end_azimuth: float = Field(
        ..., description="The azimuth of the satellite at the end of the transit in degrees."
    )
    weather_forecast: str | None = Field(
        default=None, description="The weather forecast for the transit location at the time of the transit."
    )


    def __repr__(self):
        return (
            f"Start: {self.start_time} ({self.start_azimuth:.1f}°), "
            f"Max Elevation: {self.max_elevation:.1f}° at {self.culmination_time} ({self.max_elevation_azimuth:.1f}°), "
            f"End: {self.end_time} ({self.end_azimuth:.1f}°), "
            f"Duration: {self.duration_seconds} seconds, "
            f"Weather: {self.weather_forecast}"
        )


@mcp.tool()
@cached(cache=LRUCache(maxsize=100))
def get_name_from_norad_id(norad_id: str) -> str:
    """
    Get the name of a satellite from its NORAD ID.

    Args:
        norad_id (str): The NORAD catalog ID of the satellite.
    Returns:
        str: The name of the satellite.
    Raises:
        APIError: If the API call fails.
        NoDataFoundError: If no satellite is found for the given NORAD ID.
    """
    response = httpx.get(
        f"{settings.celestrak_satcat_url}?CATNR={norad_id}&ACTIVE=true&FORMAT=json"
    )
    if response.status_code != 200:
        raise APIError(f"Unable to fetch satellite data. Status code: {response.status_code}")
    satcat_data = response.json()
    if not satcat_data:
        raise NoDataFoundError(f"No satellite found for NORAD ID {norad_id}")
    return satcat_data[0]["OBJECT_NAME"]


@mcp.tool()
@cached(cache=LRUCache(maxsize=100))
def get_norad_id_from_name(name: str) -> str:
    """
    Get the NORAD ID of a satellite from its name.

    Args:
        name (str): The name of the satellite.
    Returns:
        A comma separated list of NORAD IDs that match the name.
    Raises:
        APIError: If the API call fails.
        NoDataFoundError: If no matching satellite is found.
    """
    response = httpx.get(
        f"{settings.celestrak_satcat_url}?NAME={name}&ACTIVE=true&FORMAT=json"
    )
    if response.status_code != 200:
        raise APIError(f"Unable to fetch satellite data. Status code: {response.status_code}")
    satcat_data = response.json()
    results = [
        str(sat["NORAD_CAT_ID"])
        for sat in satcat_data
        if name.lower() in sat["OBJECT_NAME"].lower()
    ]
    if not results:
        raise NoDataFoundError(f"No satellite found with name containing '{name}'")

    return ", ".join(results)


@mcp.tool()
@cached(cache=TTLCache(maxsize=100, ttl=60 * 60 * 2))  # Cache for 2 hours
def get_tle(norad_id: str) -> str:
    """
    Get the TLE (Two-Line Element set) for a satellite given its NORAD ID.
    CelesTrak only updates TLEs every 2 hours, so we cache the result for 2 hours.

    Args:
        norad_id (str): The NORAD catalog ID of the satellite.
    Returns:
        str: The TLE of the satellite.
    Raises:
        APIError: If the API call fails.
        NoDataFoundError: If no TLE data is found for the given NORAD ID.
    """

    response = httpx.get(
        f"{settings.celestrak_gp_url}?CATNR={norad_id}"
    )
    if response.status_code != 200:
        raise APIError(f"Unable to fetch TLE for NORAD ID {norad_id}. Status code: {response.status_code}")
    if "No data found" in response.text:
        raise NoDataFoundError(f"No TLE data found for NORAD ID {norad_id}")
    # Clean up the TLE text
    # Remove carriage returns and trailing whitespace
    tle = response.text.replace("\r", "").rstrip()
    return tle


@mcp.tool()
@cached(cache=LRUCache(maxsize=100))
def get_weather_forecast(latitude: float, longitude: float, time_dt: datetime) -> str:
    """
    Get the weather forecast for a given location and time.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        time_dt (datetime): The time for which to get the forecast.

    Returns:
        str: The weather forecast summary.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "cloud_cover",
            "start_date": time_dt.strftime("%Y-%m-%d"),
            "end_date": time_dt.strftime("%Y-%m-%d"),
            "timezone": "UTC",
        }
        response = httpx.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "hourly" not in data or "time" not in data["hourly"] or "cloud_cover" not in data["hourly"]:
            return "Weather data not available."

        time_str = time_dt.strftime("%Y-%m-%dT%H:00")
        try:
            index = data["hourly"]["time"].index(time_str)
            cloud_cover = data["hourly"]["cloud_cover"][index]
            return f"{cloud_cover}% cloud cover"
        except (ValueError, IndexError):
            return "Forecast for the specific hour not found."

    except httpx.HTTPStatusError as e:
        return f"Weather API request failed: {e}"
    except Exception as e:
        return f"An error occurred while fetching weather: {e}"


@mcp.tool()
def get_transits(norad_id: str, latitude: float, longitude: float, angle_above_horizon: float = 10) -> List[Transit]:
    """
    Get the transits of a satellite given its NORAD ID and observer's location.

    Args:
        norad_id (str): The NORAD catalog ID of the satellite.
        latitude (float): Latitude of the observer's location.
        longitude (float): Longitude of the observer's location.
        angle_above_horizon (float): The minimum angle above the horizon to consider a transit (default is 10 degrees).

    Returns:
        List[Transit]: A list of transits for the satellite.
    """
    tle = get_tle(norad_id)
    if tle.startswith("Error:"):
        return tle
    qth = (latitude, longitude, 0)

    transits = list(
        predict.transits(tle, qth, ending_before=time.time() + 60 * 60 * 24 * 1)
    )
    results = []
    for transit in transits:
        t = transit.above(angle_above_horizon)
        if t.duration() <= 0.0:
            continue

        peak = t.peak()
        start_time = datetime.fromtimestamp(t.start)
        end_time = datetime.fromtimestamp(t.end)
        duration_seconds = t.duration()
        max_elevation = peak["elevation"]
        culmination_time = datetime.fromtimestamp(peak["epoch"])
        start_azimuth = t._samples[0]["azimuth"]
        max_elevation_azimuth = peak["azimuth"]
        end_azimuth = t._samples[-1]["azimuth"]
        weather_forecast = get_weather_forecast(latitude, longitude, culmination_time)

        results.append(
            Transit(
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                max_elevation=max_elevation,
                culmination_time=culmination_time,
                start_azimuth=start_azimuth,
                max_elevation_azimuth=max_elevation_azimuth,
                end_azimuth=end_azimuth,
                weather_forecast=weather_forecast,
            )
        )
    return results

@mcp.tool()
@cached(cache=LRUCache(maxsize=100))
def get_latitude_longitude_from_location_name(location_name: str) -> str:
    """
    Get the latitude and longitude of a location given its name.
    Args:
        location_name (str): The name of the location.
    Returns:
        str: A string containing the latitude and longitude of the location.
    Raises:
        ConfigurationError: If the GEOCODE_API_KEY is not set.
        APIError: If the API call fails.
        NoDataFoundError: If no location data is found.
    """

    if not settings.geocode_api_key:
        raise ConfigurationError("GEOCODE_API_KEY is not set in the environment variables.")
    
    location_name_encoded = quote_plus(location_name)
    response = httpx.get(
        f"{settings.geocode_search_url}?q={location_name_encoded}&api_key={settings.geocode_api_key}"
    )
    if response.status_code != 200:
        raise APIError(f"Unable to fetch location data. Status code: {response.status_code}")
    location_data = response.json()
    if not location_data:
        raise NoDataFoundError(f"No location data found for '{location_name}'.")
    
    # First entry is has the highest importance
    latitude = location_data[0]["lat"]
    longitude = location_data[0]["lon"]
    return f"Latitude: {latitude}, Longitude: {longitude}"

import typer

app = typer.Typer()

@app.command()
def main(
    transport: str = typer.Option(
        settings.transport,
        "--transport",
        "-t",
        help="The transport to use for the MCP server.",
    ),
    host: str = typer.Option(
        settings.host,
        "--host",
        "-h",
        help="The host to bind the MCP server to.",
    ),
    port: int = typer.Option(
        settings.port,
        "--port",
        "-p",
        help="The port to bind the MCP server to.",
    ),
):
    """
    Run the PyPredict MCP server.
    """
    print(f"Starting MCP server with {transport} transport...")
    mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    app()
