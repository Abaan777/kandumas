"""Unit tests for the env-data gap-filling logic -- specifically the trailing-gap
carry-forward that fixes forecasts anchoring to a stale date (see preprocess.py
_ffill_trailing_gap for the full rationale)."""
import pandas as pd

from app.ml.pipeline.preprocess import _ffill_trailing_gap


def _series(values):
    idx = pd.period_range("2023-01", periods=len(values), freq="M").to_timestamp()
    return pd.Series(values, index=idx)


def test_carries_the_last_real_value_through_a_trailing_gap():
    s = _series([1.0, 2.0, 3.0, None, None, None])
    result = _ffill_trailing_gap(s)
    assert result.tolist() == [1.0, 2.0, 3.0, 3.0, 3.0, 3.0]


def test_does_not_touch_a_series_with_no_trailing_gap():
    s = _series([1.0, 2.0, 3.0])
    result = _ffill_trailing_gap(s)
    assert result.tolist() == [1.0, 2.0, 3.0]


def test_leaves_a_leading_gap_as_real_nan_not_fabricated():
    s = _series([None, None, 5.0, 6.0])
    result = _ffill_trailing_gap(s)
    assert result.iloc[0] is None or pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.tolist()[2:] == [5.0, 6.0]


def test_an_all_missing_series_stays_all_missing():
    s = _series([None, None, None])
    result = _ffill_trailing_gap(s)
    assert result.isna().all()


def test_does_not_paper_over_an_interior_gap():
    """This function only fills the trailing gap (after the last real value) -- an
    interior gap is left for the short-range interpolate() step (or real NaN) to
    handle, same as before this function was introduced."""
    s = _series([1.0, None, None, 4.0, None])
    result = _ffill_trailing_gap(s)
    assert pd.isna(result.iloc[1])
    assert pd.isna(result.iloc[2])
    assert result.iloc[3] == 4.0
    assert result.iloc[4] == 4.0  # the trailing gap after the last real value (index 3)
