from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str


class ForgotPasswordResponse(BaseModel):
    detail: str
    # Populated only because no email provider is wired up yet (see api/auth.py) -- in
    # production this would be emailed instead of returned in the response body.
    reset_token: str | None = None
    reset_url: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    detail: str


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    lat_center: float
    lon_center: float


class SpeciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    scientific_name: str | None = None


class HistoricalPoint(BaseModel):
    month: date
    region: str
    species: str
    catch_kg: float
    sst: float | None = None
    wind_speed: float | None = None
    salinity: float | None = None


class DashboardOverview(BaseModel):
    total_regions: int
    total_species: int
    latest_month: date | None
    max_forecast_catch_kg: float | None
    avg_catch_kg: float | None
    avg_sst: float | None


class PredictionRequest(BaseModel):
    region: str
    species: str
    months_ahead: int = 3


class PredictionPoint(BaseModel):
    target_month: date
    predicted_catch_kg: float
    model_name: str


class PredictionResponse(BaseModel):
    region: str
    species: str
    model_used: str
    rmse: float | None = None
    mape: float | None = None
    points: list[PredictionPoint]


class RegionAccuracy(BaseModel):
    region: str
    model_name: str | None = None
    rmse: float | None = None
    mape: float | None = None
    accuracy_pct: float | None = None


class DailyEstimateDay(BaseModel):
    date: str
    sst: float | None = None
    wind_speed: float | None = None
    baseline_daily_catch_kg: float | None = None
    favorability_ratio: float | None = None
    estimated_catch_kg: float | None = None
    note: str | None = None


class DailyEstimateResponse(BaseModel):
    region: str
    species: str
    days: list[DailyEstimateDay]
    disclaimer: str


class ModelMetric(BaseModel):
    model_name: str
    species: str
    region: str | None = None
    rmse: float
    mape: float
    is_best: bool
    trained_at: datetime


class ReportRequest(BaseModel):
    region: str | None = None
    species: str | None = None
    file_format: str = "csv"  # "csv" | "pdf"
