"""
5 EMA Trading Strategy Backtester
For: ETH, DOGE, BTC, ADA
Starting Capital: $100
Max Concurrent Trades: 3
Risk-Reward Ratio: 1:3
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import json


@dataclass
class Trade:
    """Represents a single trade"""
    symbol: str
    entry_price: float
    entry_time: int
    exit_price: float = 0
    exit_time: int = 0
    sl_price: float = 0
    tp_price: float = 0
    direction: str = ""  # "SELL" or "BUY"
    status: str = "OPEN"  # OPEN, CLOSED, SL_HIT
    pnl: float = 0
    pnl_percent: float = 0
    alert_candle_idx: int = 0
    entry_candle_idx: int = 0


class EMAStrategy:
    """
    5 EMA Trading Strategy
    SELL: 5min timeframe - candle closes above EMA, low doesn't touch EMA
    BUY: 15min timeframe - candle closes below EMA, high doesn't touch EMA
    """

    def __init__(self, initial_capital: float = 100, max_trades: int = 3, risk_reward: float = 3.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_trades = max_trades
        self.risk_reward = risk_reward
        self.trades: List[Trade] = []
        self.open_trades: Dict[str, Trade] = {}
        self.ema_period = 5
        self.trade_count = 0

    def calculate_ema(self, prices: np.ndarray, period: int = 5) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.full_like(prices, np.nan)
        
        ema = np.zeros_like(prices, dtype=float)
        multiplier = 2 / (period + 1)
        
        # First EMA is SMA
        ema[period - 1] = np.mean(prices[:period])
        
        for i in range(period, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i - 1] * (1 - multiplier)
        
        return ema

    def find_sell_signals(self, df: pd.DataFrame) -> List[Tuple[int, float, float]]:
        """
        Find SELL signals (5min timeframe)
        Return: List of (index, entry_price, sl_price)
        """
        signals = []
        
        close = df['close'].values
        low = df['low'].values
        high = df['high'].values
        ema = self.calculate_ema(close, self.ema_period)
        
        for i in range(self.ema_period + 1, len(df)):
            current_close = close[i]
            current_low = low[i]
            current_high = high[i]
            current_ema = ema[i]
            prev_close = close[i - 1]
            prev_ema = ema[i - 1]
            
            # Alert candle: closes above EMA and low doesn't touch EMA
            if (prev_close > prev_ema and 
                current_low > current_ema and 
                current_close > current_ema):
                
                # Check if next candle low breaks below current low (entry confirmation)
                if i + 1 < len(df):
                    next_low = low[i + 1]
                    next_close = close[i + 1]
                    next_ema = ema[i + 1]
                    
                    # Entry: next candle low breaks below alert candle low
                    if next_low < current_low and next_close < current_ema:
                        entry_price = current_low
                        sl_price = current_high
                        signals.append((i + 1, entry_price, sl_price))
        
        return signals

    def find_buy_signals(self, df: pd.DataFrame) -> List[Tuple[int, float, float]]:
        """
        Find BUY signals (15min timeframe)
        Return: List of (index, entry_price, sl_price)
        """
        signals = []
        
        close = df['close'].values
        low = df['low'].values
        high = df['high'].values
        ema = self.calculate_ema(close, self.ema_period)
        
        for i in range(self.ema_period + 1, len(df)):
            current_close = close[i]
            current_high = high[i]
            current_low = low[i]
            current_ema = ema[i]
            prev_close = close[i - 1]
            prev_ema = ema[i - 1]
            
            # Alert candle: closes below EMA and high doesn't touch EMA
            if (prev_close < prev_ema and 
                current_high < current_ema and 
                current_close < current_ema):
                
                # Check if next candle high breaks above current high (entry confirmation)
                if i + 1 < len(df):
                    next_high = high[i + 1]
                    next_close = close[i + 1]
                    next_ema = ema[i + 1]
                    
                    # Entry: next candle high breaks above alert candle high
                    if next_high > current_high and next_close > current_ema:
                        entry_price = current_high
                        sl_price = current_low
                        signals.append((i + 1, entry_price, sl_price))
        
        return signals

    def execute_sell_trade(self, symbol: str, signal_idx: int, entry_price: float, 
                          sl_price: float, current_price: float, timestamp: int) -> Trade:
        """Execute a SELL trade"""
        risk = entry_price - sl_price
        target_profit = risk * self.risk_reward
        tp_price = entry_price - target_profit
        
        position_size = self.capital / (self.max_trades * entry_price)
        
        trade = Trade(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=timestamp,
            sl_price=sl_price,
            tp_price=tp_price,
            direction="SELL",
            status="OPEN",
            alert_candle_idx=signal_idx - 1,
            entry_candle_idx=signal_idx
        )
        
        return trade

    def execute_buy_trade(self, symbol: str, signal_idx: int, entry_price: float, 
                         sl_price: float, current_price: float, timestamp: int) -> Trade:
        """Execute a BUY trade"""
        risk = sl_price - entry_price
        target_profit = risk * self.risk_reward
        tp_price = entry_price + target_profit
        
        position_size = self.capital / (self.max_trades * entry_price)
        
        trade = Trade(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=timestamp,
            sl_price=sl_price,
            tp_price=tp_price,
            direction="BUY",
            status="OPEN",
            alert_candle_idx=signal_idx - 1,
            entry_candle_idx=signal_idx
        )
        
        return trade

    def backtest_symbol(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List[Trade]:
        """Backtest strategy on a single symbol"""
        trades = []
        
        if timeframe == "5m":
            signals = self.find_sell_signals(df)
            for signal_idx, entry_price, sl_price in signals:
                if len(self.open_trades) < self.max_trades:
                    timestamp = df.iloc[signal_idx]['timestamp'] if 'timestamp' in df else signal_idx
                    current_price = df.iloc[signal_idx]['close']
                    
                    trade = self.execute_sell_trade(symbol, signal_idx, entry_price, sl_price, current_price, timestamp)
                    self.open_trades[f"{symbol}_SELL_{signal_idx}"] = trade
                    
        elif timeframe == "15m":
            signals = self.find_buy_signals(df)
            for signal_idx, entry_price, sl_price in signals:
                if len(self.open_trades) < self.max_trades:
                    timestamp = df.iloc[signal_idx]['timestamp'] if 'timestamp' in df else signal_idx
                    current_price = df.iloc[signal_idx]['close']
                    
                    trade = self.execute_buy_trade(symbol, signal_idx, entry_price, sl_price, current_price, timestamp)
                    self.open_trades[f"{symbol}_BUY_{signal_idx}"] = trade
        
        return trades

    def close_trade(self, trade: Trade, exit_price: float, exit_time: int, reason: str = "TP"):
        """Close a trade and calculate P&L"""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        
        if trade.direction == "SELL":
            trade.pnl = (trade.entry_price - exit_price) * 1  # 1 unit for simplicity
            trade.pnl_percent = ((trade.entry_price - exit_price) / trade.entry_price) * 100
        else:  # BUY
            trade.pnl = (exit_price - trade.entry_price) * 1
            trade.pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        
        trade.status = "CLOSED" if reason == "TP" else "SL_HIT"
        self.trades.append(trade)
        self.capital += trade.pnl
        
        return trade

    def get_backtest_report(self) -> Dict:
        """Generate backtest report"""
        if not self.trades:
            return {"error": "No trades executed"}
        
        trades_df = pd.DataFrame([
            {
                'symbol': t.symbol,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'sl_price': t.sl_price,
                'tp_price': t.tp_price,
                'pnl': t.pnl,
                'pnl_percent': t.pnl_percent,
                'status': t.status
            }
            for t in self.trades
        ])
        
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = len([t for t in self.trades if t.pnl < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum([t.pnl for t in self.trades])
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        avg_pnl_percent = sum([t.pnl_percent for t in self.trades]) / total_trades if total_trades > 0 else 0
        
        report = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_pnl': total_pnl,
            'total_pnl_percent': (total_pnl / self.initial_capital) * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_pnl_percent': avg_pnl_percent,
            'max_profit': max([t.pnl for t in self.trades]) if self.trades else 0,
            'max_loss': min([t.pnl for t in self.trades]) if self.trades else 0,
            'trades': trades_df.to_dict('records')
        }
        
        return report


if __name__ == "__main__":
    strategy = EMAStrategy(initial_capital=100, max_trades=3, risk_reward=3.0)
    print("✅ EMA Strategy Initialized")
    print(f"📊 Initial Capital: ${strategy.initial_capital}")
    print(f"📈 Max Concurrent Trades: {strategy.max_trades}")
    print(f"🎯 Risk-Reward Ratio: 1:{strategy.risk_reward}")
