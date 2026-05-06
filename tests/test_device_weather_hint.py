from device.main import weather_hint


def test_weather_hint_rain():
    payload = {"weather": {"weather_description": "light rain"}}
    assert "umbrella" in weather_hint(payload).lower()


def test_weather_hint_clear():
    payload = {"weather": {"weather_description": "clear sky"}}
    assert weather_hint(payload) == ""
