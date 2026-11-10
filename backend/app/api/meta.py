"""Lookup endpoints the frontend uses to populate filter dropdowns (region/species)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Region, Species
from app.schemas.schemas import RegionOut, SpeciesOut

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/regions", response_model=list[RegionOut])
def list_regions(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> list[RegionOut]:
    return db.query(Region).order_by(Region.lat_center.desc()).all()


@router.get("/species", response_model=list[SpeciesOut])
def list_species(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> list[SpeciesOut]:
    return db.query(Species).order_by(Species.name).all()
