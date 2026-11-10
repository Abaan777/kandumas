from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import CatchRecord, EnvironmentalObservation, Region, Species
from app.schemas.schemas import HistoricalPoint

router = APIRouter(prefix="/historical", tags=["historical"])


@router.get("", response_model=list[HistoricalPoint])
def get_historical(
    region: str | None = Query(None),
    species: str | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[HistoricalPoint]:
    query = (
        db.query(CatchRecord, Region, Species, EnvironmentalObservation)
        .join(Region, CatchRecord.region_id == Region.id)
        .join(Species, CatchRecord.species_id == Species.id)
        .outerjoin(
            EnvironmentalObservation,
            (EnvironmentalObservation.region_id == Region.id)
            & (EnvironmentalObservation.obs_month == CatchRecord.catch_month),
        )
    )
    if region:
        query = query.filter(Region.name == region)
    if species:
        query = query.filter(Species.name == species)
    if start:
        query = query.filter(CatchRecord.catch_month >= start)
    if end:
        query = query.filter(CatchRecord.catch_month <= end)

    query = query.order_by(CatchRecord.catch_month)

    return [
        HistoricalPoint(
            month=catch.catch_month,
            region=reg.name,
            species=sp.name,
            catch_kg=catch.catch_kg,
            sst=env.sst if env else None,
            wind_speed=env.wind_speed if env else None,
            salinity=env.salinity if env else None,
        )
        for catch, reg, sp, env in query.all()
    ]
