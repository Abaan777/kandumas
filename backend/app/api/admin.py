"""Admin-only endpoints (UC6 update datasets, UC7 monitor model performance, UC8 trigger
retraining). Every route requires role == 'admin'."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import ModelRun, Species
from app.schemas.schemas import ModelMetric

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])
logger = logging.getLogger(__name__)


def _refresh_datasets_job() -> None:
    from app.ml.ingestion.iotc import fetch_maldives_catch
    from app.ml.ingestion.noaa import fetch_all_environmental_data
    from app.ml.pipeline.preprocess import build_monthly_features

    logger.info("Admin-triggered dataset refresh starting")
    fetch_maldives_catch(force_download=True)
    fetch_all_environmental_data()
    build_monthly_features()
    logger.info("Admin-triggered dataset refresh finished")


def _retrain_job() -> None:
    from app.ml.training import evaluate, train_lstm, train_prophet

    logger.info("Admin-triggered retraining starting")
    train_lstm.train_all()
    train_prophet.train_all()
    evaluate.run()
    logger.info("Admin-triggered retraining finished")


@router.post("/datasets/refresh", status_code=202)
def refresh_datasets(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_refresh_datasets_job)
    return {"status": "started", "detail": "Re-fetching IOTC + NOAA data and rebuilding features in the background."}


@router.post("/retrain", status_code=202)
def retrain(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_retrain_job)
    return {"status": "started", "detail": "Retraining LSTM + Prophet models in the background."}


@router.get("/metrics", response_model=list[ModelMetric])
def metrics(db: Session = Depends(get_db)) -> list[ModelMetric]:
    runs = db.query(ModelRun).order_by(ModelRun.trained_at.desc()).limit(200).all()
    species_by_id = {s.id: s.name for s in db.query(Species).all()}
    return [
        ModelMetric(
            model_name=r.model_name,
            species=species_by_id.get(r.species_id, "?"),
            region=(r.params_json or {}).get("region"),
            rmse=r.rmse,
            mape=r.mape,
            is_best=r.is_best,
            trained_at=r.trained_at,
        )
        for r in runs
    ]
