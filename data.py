# data.py

import ccxt
import pandas as pd
import time
import os
import logging
from datetime import datetime, timezone

# Ensure data directory exists
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Configure logging
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Set up logging
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f'data_collection_{
                          datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Add a console handler to see logs in real-time
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

exchanges = [
    'binanceus', 'coinbase', 'kraken', 'bitfinex', 'gemini',
    'kucoin', 'okx', 'poloniex', 'bitstamp'
]
symbol = 'BTC/USD'

exchange_symbol_map = {
    'binanceus': 'BTC/USD',
    'coinbase': 'BTC/USD',
    'kraken': 'BTC/USD',
    'bitfinex': 'BTC/USD',
    'gemini': 'BTC/USD',
    'kucoin': 'BTC/USDT',
    'okx': 'BTC/USDT',
    'poloniex': 'BTC/USDT',
    'bitstamp': 'BTC/USD',
}

start_date = '2021-01-01T00:00:00Z'
end_date = '2021-01-08T00:00:00Z'


def collect_data():
    for exchange_id in exchanges:
        logging.info(f"Starting data collection for {exchange_id}")
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({'enableRateLimit': True})

            ex_symbol = exchange_symbol_map.get(exchange_id, symbol)
            logging.info(f"Using symbol {ex_symbol} for {exchange_id}")

            try:
                markets = exchange.load_markets()
                logging.info(f"Successfully loaded markets for {exchange_id}")
            except Exception as e:
                logging.error(f"Failed to load markets for {exchange_id}: {e}")
                continue

            if ex_symbol not in markets:
                logging.error(f"{ex_symbol} not available on {exchange_id}")
                continue

            all_tickers = []
            since = exchange.parse8601(start_date)
            end_time = exchange.parse8601(end_date)
            timeframe = '1m'
            limit = 1000

            logging.info(f"Fetching data from {
                         exchange_id} for {ex_symbol}...")
            logging.info(f"Start date: {start_date}, End date: {end_date}")

            while since < end_time:
                try:
                    ohlcv = exchange.fetch_ohlcv(
                        ex_symbol, timeframe=timeframe, since=since, limit=limit)
                    if not ohlcv:
                        logging.warning(f"No OHLCV data returned for {
                                        exchange_id} at timestamp {since}")
                        break

                    for entry in ohlcv:
                        timestamp = entry[0]
                        if timestamp >= end_time:
                            logging.info(f"Reached end time for {exchange_id}")
                            break

                        ticker = exchange.fetch_ticker(ex_symbol)
                        all_tickers.append({
                            'timestamp': datetime.fromtimestamp(timestamp / 1000, timezone.utc),
                            'bid': ticker['bid'],
                            'ask': ticker['ask']
                        })

                    since = ohlcv[-1][0] + \
                        exchange.parse_timeframe(timeframe) * 1000
                    logging.info(f"Fetched data for {exchange_id} up to {
                                 datetime.fromtimestamp(since / 1000, timezone.utc)}")
                    time.sleep(exchange.rateLimit / 1000)

                except Exception as e:
                    logging.error(f"Error fetching data from {
                                  exchange_id} at timestamp {since}: {e}")
                    break

            if all_tickers:
                df = pd.DataFrame(all_tickers)
                df.set_index('timestamp', inplace=True)

                filename = f"{
                    DATA_DIR}/{exchange_id}_{ex_symbol.replace('/', '')}.csv"
                df.to_csv(filename)
                logging.info(f"Data saved to {
                             filename}. Total records: {len(df)}")
            else:
                logging.warning(f"No data collected for {exchange_id}")

        except Exception as e:
            logging.error(f"Unexpected error collecting data from {
                          exchange_id}: {e}")
            continue

        logging.info(f"Completed data collection for {exchange_id}")


if __name__ == '__main__':
    logging.info("Starting data collection process")
    collect_data()
    logging.info("Data collection process completed")
