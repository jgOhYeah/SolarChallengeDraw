from dataclasses import dataclass
from enum import StrEnum
from typing import List
import numpy as np
import pandas as pd


class CarTableFields(StrEnum):
    CAR_ID = "Car ID"
    SCHOOL_ID = "School ID"
    CAR_NAME = "Car name"
    SCRUITINEERED = "Scruitineered"
    PRESENT_ROUND_ROBIN = "Present for round robin"
    PRESENT_KNOCKOUT = "Present for knockout"
    POINTS = "Points"


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


def load_cars(csv_filename: str) -> List[Car]:
    """Loads a list of cars from a CSV file.

    Args:
        csv_filename (str): The file path to load the CSV from.
        event_id (int, optional): The ID of the event to assign to the car. Defaults to 0.

    Returns:
        List[Car]: The list of cars.
    """
    print(csv_filename)
    df = pd.read_csv(csv_filename)
    cars: List[Car] = []
    for _, row in df.iterrows():
        print(row[CarTableFields.POINTS], pd.isna(row[CarTableFields.POINTS]))
        cars.append(
            Car(
                car_id=row[CarTableFields.CAR_ID],
                school_id=row[CarTableFields.SCHOOL_ID],
                car_name=row[CarTableFields.CAR_NAME],
                car_scruitineered=row[CarTableFields.SCRUITINEERED],
                present_round_robin=row[CarTableFields.PRESENT_ROUND_ROBIN],
                present_knockout=row[CarTableFields.PRESENT_KNOCKOUT],
                points=row[CarTableFields.POINTS] if not np.isnan(row[CarTableFields.POINTS]) else 0
            )
        )

    return cars
