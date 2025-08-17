import pytest
import httpx
import time
from unittest.mock import Mock, MagicMock
from main import (
    get_name_from_norad_id,
    get_norad_id_from_name,
    get_tle,
    get_latitude_longitude_from_location_name,
    get_transits,
    Transit,
)
import predict
from datetime import datetime
from exceptions import APIError, NoDataFoundError, ConfigurationError


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
        "https://celestrak.org/satcat/records.php?CATNR=25544&ACTIVE=true&FORMAT=json"
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
        "https://celestrak.org/satcat/records.php?NAME=ISS&ACTIVE=true&FORMAT=json"
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
        "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544"
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
    mocker.patch("main.geocode_api_key", "fake_api_key")
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
    mocker.patch("main.geocode_api_key", "fake_api_key")
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
    mocker.patch("main.geocode_api_key", "fake_api_key")
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
    mocker.patch("main.geocode_api_key", None)

    # Act & Assert
    with pytest.raises(ConfigurationError, match="GEOCODE_API_KEY is not set"):
        get_latitude_longitude_from_location_name("any")


def test_get_transits_success(mocker):
    """
    Test get_transits successfully returns a list of transits.
    """
    # Arrange
    mocker.patch("main.get_tle", return_value="fake_tle")
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
    mocker.patch("main.get_tle", return_value="fake_tle")
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
    mocker.patch("main.get_tle", side_effect=NoDataFoundError("TLE not found"))

    # Act & Assert
    with pytest.raises(NoDataFoundError, match="TLE not found"):
        get_transits("25544", 38.8951, -77.0364)


def test_get_transits_filters_short_durations(mocker):
    """
    Test that get_transits filters out transits with zero or negative duration.
    """
    # Arrange
    mocker.patch("main.get_tle", return_value="fake_tle")
    mock_transit = MagicMock()
    mock_above = MagicMock()
    mock_above.duration.return_value = 0.0
    mock_transit.above.return_value = mock_above
    mocker.patch("predict.transits", return_value=[mock_transit])

    # Act
    result = get_transits("25544", 38.8951, -77.0364)

    # Assert
    assert len(result) == 0
