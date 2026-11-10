"""CRISP-DM 'Evaluation' step.

Combines the LSTM (national, per-species) and Prophet (per-region, per-species) metrics
written by train_lstm.py / train_prophet.py, decides which model serves predictions for
each (region, species) pair, and records everything in the model_runs table so
Admin > Monitor System & Model Performance (UC7) has real numbers to show.

Selection rule: for a given (region, species), compare that region's Prophet RMSE
against the species' national LSTM RMSE and keep whichever is lower. This is an
intentionally simple, transparent rule -- the RMSE values themselves (not a hidden
heuristic) decide it, and both numbers are stored either way.

The `is_best` column here is informational only (shown in the Admin metrics table);
the actual per-request routing in prediction_service.py re-does this same RMSE
comparison directly rather than trusting this flag, because a single LSTM row (one
national model, no region) can't have one boolean that's simultaneously "best" for one
region's comparison and "not best" for another's.
"""
from __future__ import annotations

import json
import logging

from app.core.config import ML_ARTIFACTS_DIR
from app.core.database import SessionLocal
from app.models.models import ModelRun, Species

logger = logging.getLogger(__name__)


def run() -> dict:
    with open(ML_ARTIFACTS_DIR / "lstm_metrics.json") as f:
        lstm_results = json.load(f)
    with open(ML_ARTIFACTS_DIR / "prophet_metrics.json") as f:
        prophet_results = json.load(f)

    lstm_by_species = {r["species"]: r for r in lstm_results}

    db = SessionLocal()
    best_choices = []
    try:
        species_by_name = {s.name: s for s in db.query(Species).all()}

        for r in lstm_results:
            species = species_by_name.get(r["species"])
            if species is None:
                continue
            db.add(
                ModelRun(
                    model_name="lstm",
                    species_id=species.id,
                    rmse=r["rmse"],
                    mape=r["mape"],
                    is_best=False,
                    params_json=r,
                )
            )

        for r in prophet_results:
            species = species_by_name.get(r["species"])
            if species is None:
                continue
            lstm_r = lstm_by_species.get(r["species"])
            is_best_prophet = lstm_r is None or r["rmse"] <= lstm_r["rmse"]
            db.add(
                ModelRun(
                    model_name="prophet",
                    species_id=species.id,
                    rmse=r["rmse"],
                    mape=r["mape"],
                    is_best=is_best_prophet,
                    params_json=r,
                )
            )
            best_choices.append(
                {
                    "region": r["region"],
                    "species": r["species"],
                    "best_model": "prophet" if is_best_prophet else "lstm",
                    "prophet_rmse": r["rmse"],
                    "lstm_rmse": lstm_r["rmse"] if lstm_r else None,
                }
            )

        # Mark the LSTM row as "best" (for display) when it actually wins the
        # comparison for at least one region -- or when the species has no Prophet
        # results at all (e.g. every region had too little data), so the LSTM is
        # implicitly the only option everywhere.
        for r in lstm_results:
            species = species_by_name.get(r["species"])
            if species is None:
                continue
            lstm_wins_at_least_one_region = any(
                c["species"] == r["species"] and c["best_model"] == "lstm" for c in best_choices
            ) or not any(c["species"] == r["species"] for c in best_choices)
            if lstm_wins_at_least_one_region:
                run_row = (
                    db.query(ModelRun)
                    .filter_by(model_name="lstm", species_id=species.id)
                    .order_by(ModelRun.id.desc())
                    .first()
                )
                if run_row:
                    run_row.is_best = True

        db.commit()
    finally:
        db.close()

    summary = {"per_region_species_choice": best_choices}
    with open(ML_ARTIFACTS_DIR / "metrics.json", "w") as f:
        json.dump({"lstm": lstm_results, "prophet": prophet_results, "summary": summary}, f, indent=2, default=str)
    logger.info("Wrote consolidated metrics.json with %s region/species selections", len(best_choices))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summary = run()
    for c in summary["per_region_species_choice"]:
        print(c)
