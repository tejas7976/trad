"""
Fetch cryptocurrency data from CCXT
Supports: ETH, DOGE, BTC, ADA
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time


class CryptoDataFetcher:
    def __init__(self, exchange_name: str = 'binance'):
        """Initialize exchange connection"""
        self.exchange_class = getattr(ccxt, exchange_name)
        self.exchange = self.exchange_class()
        self.symbols = ['ETH/USDT', 'DOGE/USDT', 'BTC/USDT', 'ADA/USDT']
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 500) -> pd.DataFrame:
        """
        Fetch OHLCV data
        timeframe: '5m', '15m', '1h', etc.
        limit: number of candles to fetch
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['datetime'] = df['timestamp'].astype(str)
            df['symbol'] = symbol
            
            return df
        
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_multiple_symbols(self, timeframe: str = '5m', limit: int = 500) -> dict:
        """Fetch data for all symbols"""
        data = {}
        
        for symbol in self.symbols:
            print(f"📥 Fetching {symbol} {timeframe}...")
            df = self.fetch_ohlcv(symbol, timeframe, limit)
            data[symbol] = df
            time.sleep(0.5)  # Rate limiting
        
        return data
    
    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save dataframe to CSV"""
        df.to_csv(filename, index=False)
        print(f"✅ Saved to {filename}")
    
    def load_from_csv(self, filename: str) -> pd.DataFrame:
        """Load data from CSV"""
        try:
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
            return pd.DataFrame()


if __name__ == "__main__":
    fetcher = CryptoDataFetcher()
    
    # Fetch 5m data
    print("📊 Fetching crypto data...")
    data_5m = fetcher.fetch_multiple_symbols('5m', limit=500)
    
    # Fetch 15m data
    data_15m = fetcher.fetch_multiple_symbols('15m', limit=500)
    
    # Save locally
    for symbol, df in data_5m.items():
        if not df.empty:
            fetcher.save_to_csv(df, f"data/{symbol.replace('/', '_')}_5m.csv")
    
    for symbol, df in data_15m.items():
        if not df.empty:
            fetcher.save_to_csv(df, f"data/{symbol.replace('/', '_')}_15m.csv")
