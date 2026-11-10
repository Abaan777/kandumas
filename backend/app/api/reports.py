from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.historical import get_historical
from app.api.predict import run_prediction
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Report, User
from app.services.report_service import build_csv, build_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/download")
def download_report(
    region: str = Query(...),
    species: str = Query(...),
    months_ahead: int = Query(3, ge=1, le=12),
    file_format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prediction = run_prediction(db, region, species, months_ahead)
    historical = get_historical(region=region, species=species, start=None, end=None, db=db, _user=user)
    historical_rows = [h.model_dump() for h in historical]

    if file_format == "pdf":
        content = build_pdf(prediction, historical_rows)
        media_type = "application/pdf"
        filename = f"kandumas_report_{region}_{species}.pdf".replace(" ", "_")
    else:
        content = build_csv(prediction, historical_rows)
        media_type = "text/csv"
        filename = f"kandumas_report_{region}_{species}.csv".replace(" ", "_")

    db.add(
        Report(
            user_id=user.id,
            filters_json={"region": region, "species": species, "months_ahead": months_ahead},
            file_format=file_format,
            file_path=filename,
        )
    )
    db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
