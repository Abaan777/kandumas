from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(Enum("fisherman", "officer", "admin", name="user_role"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PasswordResetToken(Base):
    """A single-use, expiring token issued by POST /auth/forgot-password and consumed
    by POST /auth/reset-password. Only the SHA-256 hash of the token is stored (the
    token itself is high-entropy random data, not a user-chosen password, so a fast
    hash is appropriate here -- unlike User.password_hash, which uses bcrypt)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship()


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    lat_center: Mapped[float] = mapped_column(Float)
    lon_center: Mapped[float] = mapped_column(Float)

    catch_records: Mapped[list["CatchRecord"]] = relationship(back_populates="region")
    environmental_observations: Mapped[list["EnvironmentalObservation"]] = relationship(
        back_populates="region"
    )


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    scientific_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    catch_records: Mapped[list["CatchRecord"]] = relationship(back_populates="species")


class EnvironmentalObservation(Base):
    __tablename__ = "environmental_observations"
    __table_args__ = (UniqueConstraint("region_id", "obs_month", name="uq_env_region_month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    obs_month: Mapped[date] = mapped_column(Date, index=True)  # first day of the month
    sst: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    salinity: Mapped[float | None] = mapped_column(Float, nullable=True)

    region: Mapped["Region"] = relationship(back_populates="environmental_observations")


class CatchRecord(Base):
    __tablename__ = "catch_records"
    __table_args__ = (
        UniqueConstraint("region_id", "species_id", "catch_month", name="uq_catch_region_species_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    catch_month: Mapped[date] = mapped_column(Date, index=True)
    catch_kg: Mapped[float] = mapped_column(Float)  # converted from IOTC metric tons

    region: Mapped["Region"] = relationship(back_populates="catch_records")
    species: Mapped["Species"] = relationship(back_populates="catch_records")


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(32))  # "lstm" | "prophet"
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    trained_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    rmse: Mapped[float] = mapped_column(Float)
    mape: Mapped[float] = mapped_column(Float)
    is_best: Mapped[bool] = mapped_column(default=False)
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    species: Mapped["Species"] = relationship()


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    target_month: Mapped[date] = mapped_column(Date, index=True)
    predicted_catch_kg: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    region: Mapped["Region"] = relationship()
    species: Mapped["Species"] = relationship()


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filters_json: Mapped[dict] = mapped_column(JSON)
    file_format: Mapped[str] = mapped_column(String(8))  # "pdf" | "csv"
    file_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship()
