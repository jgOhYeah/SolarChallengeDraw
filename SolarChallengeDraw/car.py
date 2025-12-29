from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict

import numpy as np
import pandas as pd

@dataclass
class Car:
    car_id: int
    school_id: int
    car_name: str
    car_scruitineered: bool
    present_round_robin: bool
    present_knockout: bool
    points: int = 0  # Lower is better.

    def __repr__(self) -> str:
        return f"<{self.car_id:>3d}, {self.points:>2.0f}>"
    
    class Fields(StrEnum):
        CAR_ID = "Car ID"
        SCHOOL_ID = "School ID"
        CAR_NAME = "Car name"
        SCRUITINEERED = "Scruitineered"
        PRESENT_ROUND_ROBIN = "Present for round robin"
        PRESENT_KNOCKOUT = "Present for knockout"
        POINTS = "Points"
    
    def to_dict(self) -> Dict[Car.Fields, Any]:
        return {
            self.Fields.CAR_ID: self.car_id,
            self.Fields.SCHOOL_ID: self.school_id,
            self.Fields.CAR_NAME: self.car_name,
            self.Fields.SCRUITINEERED: self.car_scruitineered,
            self.Fields.PRESENT_ROUND_ROBIN: self.present_round_robin,
            self.Fields.PRESENT_KNOCKOUT: self.present_knockout,
            self.Fields.POINTS: self.points
        }
    
    @classmethod
    def from_dict(cls, dt:Dict[str, Any]) -> Car:
        car_id = dt[cls.Fields.CAR_ID]
        assert not pd.isna(car_id), "Invalid car ID provided."
        assert not pd.isna(dt[cls.Fields.SCHOOL_ID]), f"Invalid school ID provided for car {car_id}."
        assert not pd.isna(dt[cls.Fields.CAR_NAME]), f"Invalid car name provided for car {car_id}."
        assert not pd.isna(dt[cls.Fields.POINTS]), f"Invalid points provided for car {car_id}."
        return Car(
            car_id=dt[cls.Fields.CAR_ID],
            school_id=dt[cls.Fields.SCHOOL_ID],
            car_name=dt[cls.Fields.CAR_NAME],
            car_scruitineered=bool(dt[cls.Fields.SCRUITINEERED]),
            present_round_robin=bool(dt[cls.Fields.PRESENT_ROUND_ROBIN]),
            present_knockout=bool(dt[cls.Fields.PRESENT_KNOCKOUT]),
            points=dt[cls.Fields.POINTS],
        )
