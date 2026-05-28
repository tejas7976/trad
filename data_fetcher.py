"""
Fetch cryptocurrency data from CCXT with extended historical data
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
        self.exchange = self.exchange_class({'enableRateLimit': True})
        self.symbols = ['ETH/USDT', 'DOGE/USDT', 'BTC/USDT', 'ADA/USDT']
    
    def fetch_ohlcv_historical(self, symbol: str, timeframe: str = '5m', 
                               days_back: int = 90, limit: int = 500) -> pd.DataFrame:
        """
        Fetch OHLCV data for the specified period
        timeframe: '5m', '15m', '1h', etc.
        days_back: number of days to fetch (default 90 days = 3 months)
        limit: max candles per request (CCXT limit per API call)
        """
        try:
            all_data = []
            
            # Calculate start date
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            print(f"   Fetching {symbol} {timeframe} from {start_date.date()} to {end_date.date()}")
            
            # Fetch data in chunks
            current_date = start_date
            while current_date < end_date:
                since = int(current_date.timestamp() * 1000)
                
                try:
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                    
                    if not ohlcv:
                        break
                    
                    all_data.extend(ohlcv)
                    
                    # Move to next batch
                    last_timestamp = ohlcv[-1][0]
                    current_date = datetime.utcfromtimestamp(last_timestamp / 1000)
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"   ⚠️  Error fetching batch: {str(e)}")
                    break
            
            if not all_data:
                print(f"   ❌ No data retrieved for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(
                all_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['datetime'] = df['timestamp'].astype(str)
            df['symbol'] = symbol
            
            # Remove duplicates and sort
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            
            print(f"   ✅ Retrieved {len(df)} candles for {symbol}")
            print(f"   📅 Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
        
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_multiple_symbols(self, timeframe: str = '5m', days_back: int = 90, limit: int = 500) -> dict:
        """Fetch historical data for all symbols"""
        data = {}
        
        for symbol in self.symbols:
            print(f"📥 Fetching {symbol} {timeframe}...")
            df = self.fetch_ohlcv_historical(symbol, timeframe, days_back, limit)
            data[symbol] = df
        
        return data
    
    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save dataframe to CSV"""
        df.to_csv(filename, index=False)
        print(f"💾 Saved to {filename} ({len(df)} rows)")
    
    def load_from_csv(self, filename: str) -> pd.DataFrame:
        """Load data from CSV"""
        try:
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except FileNotFoundError:
            print(f"❌ File not found: {filename}")
            return pd.DataFrame()


def download_3months_data():
    """Download 3 months of data for backtesting"""
    print("\n" + "="*60)
    print("📊 DOWNLOADING 3 MONTHS OF HISTORICAL DATA")
    print("="*60 + "\n")
    
    fetcher = CryptoDataFetcher()
    
    # Fetch 5m data (90 days)
    print("🔄 Fetching 5-minute candles (3 months)...")
    data_5m = fetcher.fetch_multiple_symbols('5m', days_back=90, limit=500)
    print()
    
    # Fetch 15m data (90 days)
    print("🔄 Fetching 15-minute candles (3 months)...")
    data_15m = fetcher.fetch_multiple_symbols('15m', days_back=90, limit=500)
    print()
    
    # Save to CSV
    print("\n" + "="*60)
    print("💾 SAVING DATA TO FILES")
    print("="*60 + "\n")
    
    import os
    os.makedirs('data', exist_ok=True)
    
    for symbol, df in data_5m.items():
        if not df.empty:
            fetcher.save_to_csv(df, f"data/{symbol.replace('/', '_')}_5m_3months.csv")
    
    for symbol, df in data_15m.items():
        if not df.empty:
            fetcher.save_to_csv(df, f"data/{symbol.replace('/', '_')}_15m_3months.csv")
    
    print("\n✅ Data download complete!")
    return data_5m, data_15m


if __name__ == "__main__":
    download_3months_data()
