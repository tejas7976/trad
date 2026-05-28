"""
Main backtesting runner
Combines strategy, data fetching, and execution simulation
"""

import pandas as pd
import numpy as np
import json
from ema_strategy import EMAStrategy
from data_fetcher import CryptoDataFetcher


class BacktestRunner:
    def __init__(self, initial_capital: float = 100, max_trades: int = 3):
        self.strategy = EMAStrategy(initial_capital, max_trades, risk_reward=3.0)
        self.symbols = ['ETH/USDT', 'DOGE/USDT', 'BTC/USDT', 'ADA/USDT']
        self.all_signals = []
        self.results = {}
    
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
    
    def simulate_execution(self):
        """Simulate trade execution"""
        print("\n" + "="*60)
        print("💰 TRADE EXECUTION SIMULATION")
        print("="*60)
        print(f"Starting Capital: ${self.strategy.initial_capital:.2f}")
        print(f"Max Concurrent Trades: {self.strategy.max_trades}")
        print(f"Risk-Reward Ratio: 1:{self.strategy.risk_reward}\n")
        
        executed = 0
        total_pnl = 0
        
        for symbol, direction, (idx, entry, sl) in self.all_signals:
            if len(self.strategy.open_trades) < self.strategy.max_trades:
                if direction == 'SELL':
                    tp = entry - (entry - sl) * self.strategy.risk_reward
                    pnl = (entry - tp) if tp < entry else 0
                else:  # BUY
                    tp = entry + (sl - entry) * self.strategy.risk_reward
                    pnl = (tp - entry) if tp > entry else 0
                
                self.strategy.capital += pnl
                total_pnl += pnl
                executed += 1
                
                print(f"✅ {symbol:8} | {direction:4} | Entry: ${entry:.6f} | SL: ${sl:.6f} | P&L: ${pnl:.4f}")
        
        print(f"\n💼 Executed Trades: {executed}")
        return executed, total_pnl
    
    def generate_report(self, executed: int, total_pnl: float):
        """Generate final report"""
        print("\n" + "="*60)
        print("📈 BACKTEST REPORT")
        print("="*60 + "\n")
        
        final_capital = self.strategy.initial_capital + total_pnl
        return_pct = (total_pnl / self.strategy.initial_capital) * 100
        
        print(f"Initial Capital:     ${self.strategy.initial_capital:.2f}")
        print(f"Final Capital:       ${final_capital:.2f}")
        print(f"Total P&L:           ${total_pnl:.2f}")
        print(f"Return %:            {return_pct:.2f}%")
        print(f"Total Trades:        {executed}")
        
        print("\n" + "="*60)
        
        report = {
            'initial_capital': self.strategy.initial_capital,
            'final_capital': final_capital,
            'total_pnl': total_pnl,
            'return_percent': return_pct,
            'total_trades': executed,
            'symbols': self.symbols
        }
        
        return report
    
    def save_report(self, report: dict):
        """Save report to JSON"""
        with open('backtest_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to backtest_report.json")


def main():
    print("\n🔧 CRYPTO 5 EMA STRATEGY BACKTESTER")
    print("="*60)
    print("Symbols: ETH, DOGE, BTC, ADA")
    print("Initial Capital: $100")
    print("Max Trades: 3")
    print("Risk-Reward: 1:3")
    print("="*60 + "\n")
    
    runner = BacktestRunner(initial_capital=100, max_trades=3)
    
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
