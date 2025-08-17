from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    geocode_api_key: str = Field(..., description="API key for the geocoding service.")
    google_api_key: str = Field(..., description="API key for Google services (Gemini).")
    openai_api_key: str = Field(..., description="API key for OpenAI services.")

    agent_instructions: str = Field(
        "You are a satellite tracking agent. Use the MCP tools to calculate transits for satellites. Do not use any other tools and DO NOT make up answers.",
        description="Instructions for the AI agent."
    )
    agent_model: str = Field("gemini-2.5-flash", description="The model to use for the AI agent.")

    celestrak_satcat_url: str = Field("https://celestrak.org/satcat/records.php", description="URL for Celestrak satellite catalog.")
    celestrak_gp_url: str = Field("https://celestrak.org/NORAD/elements/gp.php", description="URL for Celestrak TLE data.")
    geocode_search_url: str = Field("https://geocode.maps.co/search", description="URL for geocoding search.")

settings = Settings()
