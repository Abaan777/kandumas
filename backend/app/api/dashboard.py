from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import CatchRecord, EnvironmentalObservation, Region, Species
from app.schemas.schemas import DashboardOverview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> DashboardOverview:
    total_regions = db.query(func.count(Region.id)).scalar() or 0
    total_species = db.query(func.count(Species.id)).scalar() or 0
    latest_month = db.query(func.max(CatchRecord.catch_month)).scalar()
    max_catch = db.query(func.max(CatchRecord.catch_kg)).scalar()
    avg_catch = db.query(func.avg(CatchRecord.catch_kg)).scalar()
    avg_sst = db.query(func.avg(EnvironmentalObservation.sst)).scalar()

    return DashboardOverview(
        total_regions=total_regions,
        total_species=total_species,
        latest_month=latest_month,
        max_forecast_catch_kg=float(max_catch) if max_catch is not None else None,
        avg_catch_kg=float(avg_catch) if avg_catch is not None else None,
        avg_sst=float(avg_sst) if avg_sst is not None else None,
    )
