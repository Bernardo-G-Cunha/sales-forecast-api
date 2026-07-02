from pydantic import BaseModel
from typing import Literal


class PredictionRequest(BaseModel):
    store: int
    date: str
    promo: bool
    state_holiday: Literal["0", "a", "b", "c"]
    school_holiday: bool