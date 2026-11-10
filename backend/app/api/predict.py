from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.schemas import (
    DailyEstimateResponse,
    PredictionPoint,
    PredictionRequest,
    PredictionResponse,
    RegionAccuracy,
)
from app.services.daily_forecast_service import get_daily_estimate
from app.services.prediction_service import PredictionUnavailable, generate_forecast, get_region_accuracy

router = APIRouter(prefix="/predict", tags=["predict"])


def run_prediction(db: Session, region: str, species: str, months_ahead: int) -> PredictionResponse:
    try:
        model_used, metrics, points = generate_forecast(db, region, species, months_ahead)
    except PredictionUnavailable as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return PredictionResponse(
        # An empty region (the frontend's "All regions" option) routes to the national
        # LSTM model in generate_forecast -- shown back as a real label here rather than
        # an empty string, since this also appears verbatim in downloaded reports.
        region=region or "All regions",
        species=species,
        model_used=model_used,
        rmse=metrics["rmse"] if metrics else None,
        mape=metrics["mape"] if metrics else None,
        points=[PredictionPoint(target_month=m, predicted_catch_kg=v, model_name=model_used) for m, v in points],
    )


@router.post("", response_model=PredictionResponse)
def predict_post(
    payload: PredictionRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> PredictionResponse:
    return run_prediction(db, payload.region, payload.species, payload.months_ahead)


@router.get("", response_model=PredictionResponse)
def predict_get(
    region: str = Query(...),
    species: str = Query(...),
    months_ahead: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> PredictionResponse:
    return run_prediction(db, region, species, months_ahead)


@router.get("/accuracy", response_model=list[RegionAccuracy])
def predict_accuracy(
    species: str = Query(...), db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> list[RegionAccuracy]:
    """Per-region model accuracy for one species, for the dashboard map. Cheap (DB
    reads only, no model inference), so any authenticated role can call it -- unlike
    /admin/metrics this isn't admin-only, since the map is on the main Dashboard."""
    return [RegionAccuracy(**r) for r in get_region_accuracy(db, species)]


@router.get("/daily", response_model=DailyEstimateResponse)
def predict_daily(
    region: str = Query(...),
    species: str = Query(...),
    date: date | None = Query(None, description="Defaults to today. Must be within 7 days ahead of today."),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> DailyEstimateResponse:
    """Weather-adjusted catch estimate for a single date (today through 7 days ahead)
    -- see app/services/daily_forecast_service.py for exactly what this is (and,
    importantly, what it isn't: an independently validated daily model, which no data
    source used in this project has the resolution to support)."""
    try:
        result = get_daily_estimate(db, region, species, date)
    except PredictionUnavailable as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        # The live weather-forecast fetch (Open-Meteo) is an external call that can
        # fail transiently -- surface it as a clean 502, not a raw 500.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not fetch live weather forecast: {exc}") from exc
    return DailyEstimateResponse(**result)
