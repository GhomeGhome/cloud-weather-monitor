from device.announcer import AnnouncementManager


def test_low_humidity_triggers_announcement():
    manager = AnnouncementManager(cooldown_sec=3600)
    decision = manager.evaluate(humidity_pct=35.0, tvoc_ppb=50, eco2_ppm=500, weather_hint="")
    assert decision.should_announce is True
    assert "Humidity is low" in (decision.message or "")


def test_cooldown_blocks_immediate_repeat():
    manager = AnnouncementManager(cooldown_sec=3600)
    first = manager.evaluate(humidity_pct=35.0, tvoc_ppb=50, eco2_ppm=500, weather_hint="")
    second = manager.evaluate(humidity_pct=35.0, tvoc_ppb=50, eco2_ppm=500, weather_hint="")
    assert first.should_announce is True
    assert second.should_announce is False
