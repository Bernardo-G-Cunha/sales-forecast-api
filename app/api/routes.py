from fastapi import APIRouter

from app.schemas import PredictionRequest, PredictionResponse
from app.services import predict as predict_sales

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}



@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    prediction = predict_sales(request)

    return PredictionResponse(
        predicted_sales=prediction,
    )