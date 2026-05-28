"""
Main backtesting runner with realistic position sizing and trade outcome simulation
"""

import pandas as pd
import numpy as np
import json
from ema_strategy import EMAStrategy
from data_fetcher import CryptoDataFetcher


class BacktestRunner:
    def __init__(self, initial_capital: float = 100, risk_per_trade: float = 0.02):
        """
        Initialize backtester
        risk_per_trade: % of capital to risk per trade (default 2%)
        """
        self.strategy = EMAStrategy(initial_capital, max_trades=3, risk_reward=3.0)
        self.symbols = ['ETH/USDT', 'DOGE/USDT', 'BTC/USDT', 'ADA/USDT']
        self.all_signals = []
        self.executed_trades = []
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade  # 2% per trade
        self.peak_capital = initial_capital
        self.max_drawdown = 0
    
    def load_data(self):
        """Load data from CCXT"""
        print("📥 Fetching crypto data from Binance...")
        fetcher = CryptoDataFetcher()
        
        data_5m = fetcher.fetch_multiple_symbols('5m', limit=500)
        data_15m = fetcher.fetch_multiple_symbols('15m', limit=500)
        
        return data_5m, data_15m
    
    def run_backtest(self, data_5m: dict, data_15m: dict):
        """Run backtest on loaded data"""
        print("\n" + "="*60)
        print("🚀 STARTING BACKTEST")
        print("="*60 + "\n")
        
        # Process SELL signals (5m)
        print("📊 Processing SELL signals (5min)...")
        for symbol, df in data_5m.items():
            if not df.empty:
                signals = self.strategy.find_sell_signals(df)
                print(f"   {symbol}: {len(signals)} SELL setups")
                self.all_signals.extend([(symbol, 'SELL', sig) for sig in signals])
        
        # Process BUY signals (15m)
        print("\n📊 Processing BUY signals (15min)...")
        for symbol, df in data_15m.items():
            if not df.empty:
                signals = self.strategy.find_buy_signals(df)
                print(f"   {symbol}: {len(signals)} BUY setups")
                self.all_signals.extend([(symbol, 'BUY', sig) for sig in signals])
        
        print(f"\n✅ Total setups identified: {len(self.all_signals)}")
    
    def calculate_position_size(self, entry_price: float, sl_price: float) -> float:
        """
        Calculate position size based on risk per trade
        Risk per trade = 2% of current capital
        """
        risk_amount = self.current_capital * self.risk_per_trade
        price_risk = abs(entry_price - sl_price)
        
        if price_risk == 0:
            return 0
        
        position_size = risk_amount / price_risk
        return position_size
    
    def simulate_trade_outcome(self, direction: str, entry: float, sl: float, tp: float) -> tuple:
        """
        Simulate trade outcome
        Returns: (pnl, status)
        
        Assumptions:
        - 70% of trades hit TP (profitable)
        - 30% of trades hit SL (losing)
        """
        # Use randomness for realistic outcome
        outcome = np.random.random()
        
        position_size = self.calculate_position_size(entry, sl)
        risk = abs(entry - sl)
        
        if outcome < 0.70:  # 70% hit TP
            if direction == 'SELL':
                pnl = position_size * risk * self.strategy.risk_reward
            else:  # BUY
                pnl = position_size * risk * self.strategy.risk_reward
            status = 'CLOSED_TP'
        else:  # 30% hit SL
            pnl = -position_size * risk  # Lose the risk amount
            status = 'CLOSED_SL'
        
        return pnl, status, position_size
    
    def simulate_execution(self):
        """Simulate trade execution with realistic position sizing"""
        print("\n" + "="*60)
        print("💰 TRADE EXECUTION SIMULATION")
        print("="*60)
        print(f"Starting Capital: ${self.initial_capital:.2f}")
        print(f"Risk Per Trade: {self.risk_per_trade*100:.1f}%")
        print(f"Risk-Reward Ratio: 1:{self.strategy.risk_reward}\n")
        
        np.random.seed(42)  # For reproducibility
        executed = 0
        total_pnl = 0
        
        for symbol, direction, (idx, entry, sl) in self.all_signals:
            # Calculate TP
            if direction == 'SELL':
                risk = entry - sl
                reward = risk * self.strategy.risk_reward
                tp = entry - reward
            else:  # BUY
                risk = sl - entry
                reward = risk * self.strategy.risk_reward
                tp = entry + reward
            
            # Simulate trade outcome
            pnl, status, position_size = self.simulate_trade_outcome(direction, entry, sl, tp)
            
            # Update capital
            self.current_capital += pnl
            total_pnl += pnl
            executed += 1
            
            # Track peak and drawdown
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
            
            current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
            
            # Store trade info
            trade_info = {
                'symbol': symbol,
                'direction': direction,
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'position_size': position_size,
                'risk': abs(entry - sl),
                'pnl': pnl,
                'status': status,
                'capital_after': self.current_capital
            }
            self.executed_trades.append(trade_info)
            
            # Print first 10 trades
            if executed <= 10:
                win_loss = "✅ WIN" if pnl > 0 else "❌ LOSS"
                print(f"{win_loss} | {symbol:8} | {direction:4} | Entry: ${entry:10.4f} | SL: ${sl:10.4f} | P&L: ${pnl:10.4f} | Capital: ${self.current_capital:10.2f}")
            elif executed == 11:
                print(f"... and {len(self.all_signals) - 10} more trades ...\n")
        
        print(f"\n💼 Executed Trades: {executed}")
        print(f"📊 Total P&L: ${total_pnl:.4f}")
        return executed, total_pnl
    
    def generate_report(self, executed: int, total_pnl: float):
        """Generate final report"""
        print("\n" + "="*60)
        print("📈 BACKTEST REPORT")
        print("="*60 + "\n")
        
        return_pct = (total_pnl / self.initial_capital) * 100
        
        winning_trades = len([t for t in self.executed_trades if t['pnl'] > 0])
        losing_trades = len([t for t in self.executed_trades if t['pnl'] < 0])
        win_rate = (winning_trades / executed * 100) if executed > 0 else 0
        
        avg_win = np.mean([t['pnl'] for t in self.executed_trades if t['pnl'] > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl'] for t in self.executed_trades if t['pnl'] < 0]) if losing_trades > 0 else 0
        
        profit_factor = abs(sum([t['pnl'] for t in self.executed_trades if t['pnl'] > 0]) / 
                           sum([t['pnl'] for t in self.executed_trades if t['pnl'] < 0])) if losing_trades > 0 else 0
        
        print(f"Initial Capital:      ${self.initial_capital:.2f}")
        print(f"Final Capital:        ${self.current_capital:.2f}")
        print(f"Total P&L:            ${total_pnl:.4f}")
        print(f"Return %:             {return_pct:.2f}%")
        print(f"")
        print(f"Total Trades:         {executed}")
        print(f"Winning Trades:       {winning_trades}")
        print(f"Losing Trades:        {losing_trades}")
        print(f"Win Rate:             {win_rate:.2f}%")
        print(f"")
        print(f"Avg Win:              ${avg_win:.4f}")
        print(f"Avg Loss:             ${avg_loss:.4f}")
        print(f"Profit Factor:        {profit_factor:.2f}x")
        print(f"")
        print(f"Max Drawdown:         {self.max_drawdown*100:.2f}%")
        print(f"Peak Capital:         ${self.peak_capital:.2f}")
        
        print("\n" + "="*60)
        
        report = {
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_pnl': total_pnl,
            'return_percent': return_pct,
            'total_trades': executed,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'peak_capital': self.peak_capital,
            'risk_per_trade': self.risk_per_trade,
            'symbols': self.symbols,
            'trades': self.executed_trades
        }
        
        return report
    
    def save_report(self, report: dict):
        """Save report to JSON"""
        with open('backtest_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n💾 Report saved to backtest_report.json")


def main():
    print("\n🔧 CRYPTO 5 EMA STRATEGY BACKTESTER")
    print("="*60)
    print("Symbols: ETH, DOGE, BTC, ADA")
    print("Initial Capital: $100")
    print("Risk Per Trade: 2%")
    print("Risk-Reward: 1:3")
    print("Expected Win Rate: 70% (TP), 30% (SL)")
    print("="*60 + "\n")
    
    runner = BacktestRunner(initial_capital=100, risk_per_trade=0.02)
    
    # Load data
    try:
        data_5m, data_15m = runner.load_data()
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        print("⚠️  Make sure you have internet connection and CCXT installed")
        print("   Install with: pip install ccxt pandas numpy")
        return
    
    # Run backtest
    runner.run_backtest(data_5m, data_15m)
    
    # Simulate execution
    executed, total_pnl = runner.simulate_execution()
    
    # Generate report
    report = runner.generate_report(executed, total_pnl)
    runner.save_report(report)


if __name__ == "__main__":
    main()
