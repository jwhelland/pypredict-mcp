import pytest
import httpx
import time
from unittest.mock import Mock, MagicMock
from pypredict_mcp.main import (
    get_name_from_norad_id,
    get_norad_id_from_name,
    get_tle,
    get_latitude_longitude_from_location_name,
    get_transits,
    Transit,
    get_weather_forecast,
)
import predict
from datetime import datetime, timedelta
from pypredict_mcp.exceptions import APIError, NoDataFoundError, ConfigurationError
from pypredict_mcp.config import settings



@pytest.fixture(autouse=True)
def patch_settings(mocker):
    """Fixture to patch settings for all tests."""
    mocker.patch("pypredict_mcp.config.settings.geocode_api_key", "dummy_key")
    mocker.patch("pypredict_mcp.config.settings.google_api_key", "dummy_key")
    mocker.patch("pypredict_mcp.config.settings.openai_api_key", "dummy_key")


@pytest.fixture(autouse=True)
def clear_caches():
    """Fixture to clear all caches before each test."""
    get_name_from_norad_id.cache.clear()
    get_norad_id_from_name.cache.clear()
    get_tle.cache.clear()
    get_latitude_longitude_from_location_name.cache.clear()


def test_get_name_from_norad_id_success(mocker):
    """
    Test get_name_from_norad_id successfully returns a satellite name.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [{"OBJECT_NAME": "ISS (ZARYA)"}]
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_name_from_norad_id("25544")

    # Assert
    assert result == "ISS (ZARYA)"
    httpx.get.assert_called_once_with(
        f"{settings.celestrak_satcat_url}?CATNR=25544&ACTIVE=true&FORMAT=json"
    )


def test_get_name_from_norad_id_http_error(mocker):
    """
    Test get_name_from_norad_id raises APIError on HTTP error.

    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 500
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(APIError, match="Unable to fetch satellite data. Status code: 500"):
        get_name_from_norad_id("25544")



def test_get_name_from_norad_id_no_data(mocker):
    """
    Test get_name_from_norad_id raises NoDataFoundError when no data is found.

    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(NoDataFoundError, match="No satellite found for NORAD ID 99999"):
        get_name_from_norad_id("99999")



def test_get_norad_id_from_name_success(mocker):
    """
    Test get_norad_id_from_name successfully returns NORAD IDs.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"NORAD_CAT_ID": 25544, "OBJECT_NAME": "ISS (ZARYA)"},
        {"NORAD_CAT_ID": 58225, "OBJECT_NAME": "STARLINK-30169"},
    ]
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_norad_id_from_name("ISS")

    # Assert
    assert result == "25544"
    httpx.get.assert_called_once_with(
        f"{settings.celestrak_satcat_url}?NAME=ISS&ACTIVE=true&FORMAT=json"
    )


def test_get_norad_id_from_name_multiple_results(mocker):
    """
    Test get_norad_id_from_name with multiple matching results.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"NORAD_CAT_ID": 25544, "OBJECT_NAME": "ISS (ZARYA)"},
        {"NORAD_CAT_ID": 58225, "OBJECT_NAME": "STARLINK-30169"},
    ]
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_norad_id_from_name("STARLINK")

    # Assert
    assert result == "58225"


def test_get_norad_id_from_name_no_data(mocker):
    """
    Test get_norad_id_from_name raises NoDataFoundError when no data is found.

    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(NoDataFoundError, match="No satellite found with name containing 'nonexistent'"):
        get_norad_id_from_name("nonexistent")



def test_get_norad_id_from_name_http_error(mocker):
    """
    Test get_norad_id_from_name raises APIError on HTTP error.

    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 500
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(APIError, match="Unable to fetch satellite data. Status code: 500"):
        get_norad_id_from_name("any")



def test_get_tle_success(mocker):
    """
    Test get_tle successfully returns a TLE string.
    """
    # Arrange
    tle_string = "1 25544U 98067A   24229.56250000  .00007714  00000+0  14721-3 0  9995\r\n2 25544  51.6402 218.0000 0006703  66.6667  293.4334 15.4944849342343"
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = tle_string
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_tle("25544")

    # Assert
    assert result == tle_string.replace("\r", "").rstrip()
    httpx.get.assert_called_once_with(
        f"{settings.celestrak_gp_url}?CATNR=25544"
    )


def test_get_tle_no_data(mocker):
    """
    Test get_tle raises NoDataFoundError when no data is found.

    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "No data found"
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(NoDataFoundError, match="No TLE data found for NORAD ID 99999"):
        get_tle("99999")



def test_get_tle_http_error(mocker):
    """
    Test get_tle raises APIError on HTTP error.

    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 500
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(APIError, match="Unable to fetch TLE for NORAD ID 25544. Status code: 500"):
        get_tle("25544")



def test_get_latitude_longitude_from_location_name_success(mocker):
    """
    Test get_latitude_longitude_from_location_name successfully returns lat/lon.
    """
    # Arrange
    mocker.patch("pypredict_mcp.main.settings.geocode_api_key", "fake_api_key")
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [{"lat": "38.8951", "lon": "-77.0364"}]
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_latitude_longitude_from_location_name("Washington, DC")

    # Assert
    assert result == "Latitude: 38.8951, Longitude: -77.0364"


def test_get_latitude_longitude_from_location_name_no_data(mocker):
    """
    Test get_latitude_longitude_from_location_name raises NoDataFoundError when no data is found.

    """
    # Arrange
    mocker.patch("pypredict_mcp.main.settings.geocode_api_key", "fake_api_key")
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(NoDataFoundError, match="No location data found for 'nonexistent'"):
        get_latitude_longitude_from_location_name("nonexistent")



def test_get_latitude_longitude_from_location_name_http_error(mocker):
    """
    Test get_latitude_longitude_from_location_name raises APIError on HTTP error.

    """
    # Arrange
    mocker.patch("pypredict_mcp.main.settings.geocode_api_key", "fake_api_key")
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 500
    mocker.patch("httpx.get", return_value=mock_response)

    # Act & Assert
    with pytest.raises(APIError, match="Unable to fetch location data. Status code: 500"):
        get_latitude_longitude_from_location_name("any")



def test_get_latitude_longitude_from_location_name_no_api_key(mocker):
    """
    Test get_latitude_longitude_from_location_name raises ConfigurationError when no API key is set.

    """
    # Arrange
    mocker.patch("pypredict_mcp.main.settings.geocode_api_key", None)

    # Act & Assert
    with pytest.raises(ConfigurationError, match="GEOCODE_API_KEY is not set"):
        get_latitude_longitude_from_location_name("any")



def test_get_transits_success(mocker):
    """
    Test get_transits successfully returns a list of transits.
    """
    # Arrange
    mocker.patch("pypredict_mcp.main.get_tle", return_value="fake_tle")
    mock_transit = MagicMock()
    mock_above = MagicMock()
    mock_above.start = time.time()
    mock_above.end = time.time() + 100
    mock_above.duration.return_value = 100.0
    mock_transit.above.return_value = mock_above
    mocker.patch("predict.transits", return_value=[mock_transit])

    # Act
    result = get_transits("25544", 38.8951, -77.0364)

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], Transit)
    assert result[0].duration_seconds == 100.0


def test_get_transits_no_transits_found(mocker):
    """
    Test get_transits handles no transits found.
    """
    # Arrange
    mocker.patch("pypredict_mcp.main.get_tle", return_value="fake_tle")
    mocker.patch("predict.transits", return_value=[])

    # Act
    result = get_transits("25544", 38.8951, -77.0364)

    # Assert
    assert len(result) == 0


def test_get_transits_tle_error(mocker):
    """
    Test get_transits propagates an exception from get_tle.
    """
    # Arrange
    mocker.patch("pypredict_mcp.main.get_tle", side_effect=NoDataFoundError("TLE not found"))

    # Act & Assert
    with pytest.raises(NoDataFoundError, match="TLE not found"):
        get_transits("25544", 38.8951, -77.0364)



def test_get_transits_filters_short_durations(mocker):
    """
    Test that get_transits filters out transits with zero or negative duration.
    """
    # Arrange
    mocker.patch("pypredict_mcp.main.get_tle", return_value="fake_tle")
    mocker.patch("pypredict_mcp.main.get_weather_forecast", return_value="10% cloud cover")
    mock_transit = MagicMock()
    mock_above = MagicMock()
    mock_above.duration.return_value = 0.0
    mock_transit.above.return_value = mock_above
    mocker.patch("predict.transits", return_value=[mock_transit])

    # Act
    result = get_transits("25544", 38.8951, -77.0364)

    # Assert
    assert len(result) == 0


def test_get_transits_populates_new_fields(mocker):
    """
    Test get_transits successfully populates the new fields in the Transit object.
    """
    # Arrange
    mocker.patch("pypredict_mcp.main.get_tle", return_value="fake_tle")
    mocker.patch("pypredict_mcp.main.get_weather_forecast", return_value="10% cloud cover")

    mock_transit = MagicMock()
    mock_above = MagicMock()
    mock_above.start = 1672531200 # 2023-01-01 00:00:00
    mock_above.end = 1672531300
    mock_above.duration.return_value = 100.0
    mock_above.peak.return_value = {"elevation": 80.0, "epoch": 1672531250, "azimuth": 180.0}
    mock_above._samples = [{"azimuth": 90.0}, {"azimuth": 270.0}]
    mock_transit.above.return_value = mock_above
    mocker.patch("predict.transits", return_value=[mock_transit])

    # Act
    result = get_transits("25544", 38.8951, -77.0364)

    # Assert
    assert len(result) == 1
    transit_result = result[0]
    assert isinstance(transit_result, Transit)
    assert transit_result.duration_seconds == 100.0
    assert transit_result.max_elevation == 80.0
    assert transit_result.culmination_time == datetime.fromtimestamp(1672531250)
    assert transit_result.start_azimuth == 90.0
    assert transit_result.max_elevation_azimuth == 180.0
    assert transit_result.end_azimuth == 270.0
    assert transit_result.weather_forecast == "10% cloud cover"


@pytest.mark.integration
def test_get_weather_forecast_integration():
    """
    Test get_weather_forecast makes a real API call and returns a valid forecast.
    This is an integration test and requires an internet connection.
    """
    # Arrange
    latitude = 52.52
    longitude = 13.41
    # Use a time in the near future for the forecast
    time_dt = datetime.utcnow() + timedelta(days=1)

    # Act
    result = get_weather_forecast(latitude, longitude, time_dt)

    # Assert
    assert isinstance(result, str)
    assert "%" in result
    assert "cloud cover" in result


@pytest.mark.integration
def test_get_tle_integration():
    """
    Test get_tle makes a real API call and returns a valid TLE.
    This is an integration test and requires an internet connection.
    """
    # Arrange
    norad_id = "25544"  # ISS

    # Act
    result = get_tle(norad_id)

    # Assert
    assert isinstance(result, str)
    assert "1 25544U" in result
    assert "2 25544 " in result


@pytest.mark.integration
def test_get_name_from_norad_id_integration():
    """
    Test get_name_from_norad_id makes a real API call and returns a valid name.
    This is an integration test and requires an internet connection.
    """
    # Arrange
    norad_id = "25544"  # ISS

    # Act
    result = get_name_from_norad_id(norad_id)

    # Assert
    assert isinstance(result, str)
    assert "ISS (ZARYA)" in result


@pytest.mark.integration
def test_get_norad_id_from_name_integration():
    """
    Test get_norad_id_from_name makes a real API call and returns a valid NORAD ID.
    This is an integration test and requires an internet connection.
    """
    # Arrange
    name = "ISS"

    # Act
    result = get_norad_id_from_name(name)

    # Assert
    assert isinstance(result, str)
    assert "25544" in result


def test_get_weather_forecast_http_error(mocker):
    """
    Test get_weather_forecast handles HTTP errors gracefully.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_weather_forecast(52.52, 13.41, datetime.utcnow())

    # Assert
    assert "Weather API request failed" in result


def test_get_weather_forecast_missing_hourly_key(mocker):
    """
    Test get_weather_forecast handles missing 'hourly' key in response.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {}  # Missing 'hourly'
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_weather_forecast(52.52, 13.41, datetime.utcnow())

    # Assert
    assert result == "Weather data not available."


def test_get_weather_forecast_missing_time_key(mocker):
    """
    Test get_weather_forecast handles missing 'time' key in response.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"hourly": {"cloud_cover": []}}  # Missing 'time'
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_weather_forecast(52.52, 13.41, datetime.utcnow())

    # Assert
    assert result == "Weather data not available."


def test_get_weather_forecast_hour_not_found(mocker):
    """
    Test get_weather_forecast handles when the specific hour is not in the response.
    """
    # Arrange
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2024-01-01T10:00"],
            "cloud_cover": [50]
        }
    }
    mocker.patch("httpx.get", return_value=mock_response)

    # Act
    result = get_weather_forecast(52.52, 13.41, datetime(2024, 1, 1, 12, 0))  # Requesting a different hour

    # Assert
    assert result == "Forecast for the specific hour not found."
