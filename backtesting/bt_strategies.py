from collections import deque
from datetime import datetime
from decimal import Decimal

import backtrader as bt
import pandas as pd


class BTEMACrossover(bt.Strategy):
    params = (
        ("fast_period", 9),
        ("slow_period", 21),
    )

    def __init__(self) -> None:
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.p.fast_period)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)
        self.order = None

    def next(self) -> None:
        if self.order:
            return
        if not self.position:
            if self.crossover > 0:
                if self.data.close[0] > self.ema_fast[0] and self.data.close[0] > self.ema_slow[0]:
                    self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.sell()

    def notify_order(self, order: bt.Order) -> None:
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


class BTRSIReversal(bt.Strategy):
    params = (
        ("rsi_period", 14),
        ("bb_period", 20),
        ("bb_std", 2.0),
        ("rsi_oversold", 30.0),
        ("rsi_overbought", 70.0),
    )

    def __init__(self) -> None:
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.bbands = bt.indicators.BollingerBands(
            self.data.close, period=self.p.bb_period, devfactor=self.p.bb_std
        )
        self.order = None

    def next(self) -> None:
        if self.order:
            return
        if not self.position:
            if self.rsi[-1] <= self.p.rsi_oversold and self.rsi[0] > self.p.rsi_oversold:
                if self.data.close[0] <= self.bbands.bot[0] * 1.01:
                    self.order = self.buy()
        else:
            if self.rsi[-1] >= self.p.rsi_overbought and self.rsi[0] < self.p.rsi_overbought:
                self.order = self.sell()

    def notify_order(self, order: bt.Order) -> None:
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


class BTOpeningRangeBreakout(bt.Strategy):
    params = (
        ("orb_start_hour", 9),
        ("orb_start_min", 15),
        ("orb_end_hour", 9),
        ("orb_end_min", 30),
        ("volume_multiplier", 1.5),
    )

    def __init__(self) -> None:
        self.order = None
        self.range_high = None
        self.range_low = None
        self.range_set = False
        self.volumes: list[float] = []
        self.current_date = None
        self.signal_fired = False

    def next(self) -> None:
        if self.order:
            return

        dt = self.data.datetime.datetime(0)
        current_date = dt.date()

        if current_date != self.current_date:
            self.current_date = current_date
            self.range_high = None
            self.range_low = None
            self.range_set = False
            self.volumes = []
            self.signal_fired = False

        orb_start = dt.replace(hour=self.p.orb_start_hour, minute=self.p.orb_start_min, second=0)
        orb_end = dt.replace(hour=self.p.orb_end_hour, minute=self.p.orb_end_min, second=0)

        if orb_start <= dt < orb_end:
            if self.range_high is None or self.data.high[0] > self.range_high:
                self.range_high = self.data.high[0]
            if self.range_low is None or self.data.low[0] < self.range_low:
                self.range_low = self.data.low[0]
            self.volumes.append(self.data.volume[0])
            return

        if dt < orb_end:
            return

        if not self.range_set and self.range_high is not None:
            self.range_set = True

        if not self.range_set or self.signal_fired:
            return

        avg_vol = sum(self.volumes) / len(self.volumes) if self.volumes else 0

        if not self.position:
            if self.data.close[0] > self.range_high and self.data.volume[0] > avg_vol * self.p.volume_multiplier:
                self.order = self.buy()
                self.signal_fired = True
            elif self.data.close[0] < self.range_low and self.data.volume[0] > avg_vol * self.p.volume_multiplier:
                self.order = self.sell()
                self.signal_fired = True
        elif self.position.size > 0 and self.data.close[0] < self.range_low:
            self.order = self.close()
        elif self.position.size < 0 and self.data.close[0] > self.range_high:
            self.order = self.close()

    def notify_order(self, order: bt.Order) -> None:
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None


STRATEGY_MAP = {
    "ema_crossover": BTEMACrossover,
    "rsi_reversal": BTRSIReversal,
    "orb": BTOpeningRangeBreakout,
}
