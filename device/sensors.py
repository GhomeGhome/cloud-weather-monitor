import random
from dataclasses import dataclass


@dataclass
class SensorReading:
    temperature_c: float
    humidity_pct: float
    tvoc_ppb: int
    eco2_ppm: int
    motion_detected: bool
    pir_sensor_id: str


class SensorManager:
    """
    Simple sensor abstraction with simulation defaults.
    Replace internals with UIFlow/M5Stack unit reads on device.
    """

    def read(self) -> SensorReading:
        return SensorReading(
            temperature_c=round(random.uniform(20.0, 27.0), 1),
            humidity_pct=round(random.uniform(30.0, 55.0), 1),
            tvoc_ppb=random.randint(40, 650),
            eco2_ppm=random.randint(450, 1300),
            motion_detected=random.random() > 0.65,
            pir_sensor_id="pir-a",
        )
