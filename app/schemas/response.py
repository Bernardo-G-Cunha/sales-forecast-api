from pydantic import BaseModel


class PredictionResponse(BaseModel):
    predicted_sales: int