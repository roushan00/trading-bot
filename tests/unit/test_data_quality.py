from datetime import datetime, timedelta

from config.constants import IST
from data_ingestion.data_quality import DataQualityMonitor


def test_quality__no_gap__no_warning() -> None:
    monitor = DataQualityMonitor(gap_threshold_seconds=300)
    t1 = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    t2 = t1 + timedelta(seconds=60)
    monitor.on_tick("RELIANCE", t1)
    monitor.on_tick("RELIANCE", t2)
    assert monitor.get_gap_count("RELIANCE") == 0


def test_quality__gap_detected__logs_warning() -> None:
    monitor = DataQualityMonitor(gap_threshold_seconds=300)
    t1 = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    t2 = t1 + timedelta(minutes=6)
    monitor.on_tick("RELIANCE", t1)
    monitor.on_tick("RELIANCE", t2)
    assert monitor.get_gap_count("RELIANCE") == 1


def test_quality__multiple_gaps__counts_correctly() -> None:
    monitor = DataQualityMonitor(gap_threshold_seconds=300)
    base = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    monitor.on_tick("INFY", base)
    monitor.on_tick("INFY", base + timedelta(minutes=6))  # gap 1
    monitor.on_tick("INFY", base + timedelta(minutes=12))  # gap 2 (6 min from prev tick)
    assert monitor.get_gap_count("INFY") == 2


def test_quality__different_symbols__independent() -> None:
    monitor = DataQualityMonitor(gap_threshold_seconds=300)
    t1 = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    t2 = t1 + timedelta(minutes=10)
    monitor.on_tick("RELIANCE", t1)
    monitor.on_tick("RELIANCE", t2)
    monitor.on_tick("INFY", t1)
    monitor.on_tick("INFY", t1 + timedelta(seconds=60))
    assert monitor.get_gap_count("RELIANCE") == 1
    assert monitor.get_gap_count("INFY") == 0


def test_quality__reset__clears_state() -> None:
    monitor = DataQualityMonitor()
    t1 = datetime(2026, 5, 28, 10, 0, 0, tzinfo=IST)
    monitor.on_tick("X", t1)
    monitor.on_tick("X", t1 + timedelta(minutes=10))
    assert monitor.get_gap_count("X") == 1
    monitor.reset()
    assert monitor.get_gap_count("X") == 0
    assert monitor.get_last_tick_time("X") is None
