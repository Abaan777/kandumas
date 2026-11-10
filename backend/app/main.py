import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, dashboard, historical, meta, predict, reports
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

app = FastAPI(
    title="Kandumas API",
    description="Backend for Kandumas, the Maldives tuna catch forecasting dashboard (IT3004 capstone project).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(historical.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
