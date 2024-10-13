# arbitrage_bot.py

import ccxt.async_support as ccxt  # Asynchronous CCXT
import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

load_dotenv()

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def load_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        required_keys = ['exchanges', 'symbol', 'min_profit_percent',
                         'trade_amount', 'max_trade_amount', 'trade_currency']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config parameter: {key}")
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        exit(1)


config = load_config()

# Configure logging with level from config
log_level_str = config.get('log_level', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f'arbitrage_bot_{
                          datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Add console handler to logging
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'))
logging.getLogger().addHandler(console_handler)

# Extract configuration parameters
exchanges_config = config['exchanges']
symbol = config['symbol']
min_profit_percent = config['min_profit_percent']
trade_amount = config['trade_amount']
max_trade_amount = config['max_trade_amount']
trade_currency = config['trade_currency']
check_interval = config.get('check_interval', 5)
symbols = config.get('symbols', [symbol])

exchange_symbol_map = {
    'binance': symbol,  # Binance uses standard symbol format
    'kraken': symbol.replace('BTC', 'XBT'),  # Kraken uses 'XBT'
    'coinbasepro': symbol,  # Coinbase Pro uses standard symbol format
    'bitfinex': symbol,  # Bitfinex uses standard symbol format
    'huobipro': symbol.replace('USD', 'USDT'),  # Huobi Pro uses 'USDT' pairs
    'bittrex': symbol,  # Bittrex uses standard symbol format
    'poloniex': symbol,  # Poloniex uses standard symbol format
    'bitstamp': symbol,  # Bitstamp uses standard symbol format
    'gemini': symbol,  # Gemini uses standard symbol format
    'okx': symbol.replace('USD', 'USDT'),  # OKEx uses 'USDT' pairs
    'kucoin': symbol.replace('USD', 'USDT'),  # KuCoin uses 'USDT' pairs
}


async def init_exchanges():
    exchange_instances = {}
    for ex_conf in exchanges_config:
        exchange_id = ex_conf['name']
        api_key_env = ex_conf.get('api_key_env')
        secret_key_env = ex_conf.get('secret_key_env')
        api_key = os.getenv(api_key_env)
        secret_key = os.getenv(secret_key_env)
        if not api_key or not secret_key:
            logging.warning(
                f"API keys for {exchange_id} not found. Skipping this exchange.")
            continue
        exchange_class = getattr(ccxt.async_support, exchange_id)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'timeout': 30000,
        })
        try:
            await exchange.load_markets()
            # Map symbols if necessary
            ex_symbol = exchange_symbol_map.get(exchange_id, symbol)
            if ex_symbol not in exchange.symbols:
                logging.error(f"Symbol {ex_symbol} not available on {
                              exchange_id}. Skipping.")
                continue
            exchange_instances[exchange_id] = {
                'instance': exchange,
                'fees': ex_conf['fees'],
                'symbol': ex_symbol
            }
            logging.info(f"Initialized exchange: {
                         exchange_id} with symbol: {ex_symbol}")
        except Exception as e:
            logging.error(f"Failed to initialize {exchange_id}: {
                          type(e).__name__} - {e}")
    return exchange_instances


async def fetch_order_books(exchanges):
    tasks = []
    for name, ex in exchanges.items():
        tasks.append(fetch_order_book(ex['instance'], ex['symbol'], name))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    order_books = {}
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error fetching order book: {result}")
        elif result:
            name, data = result
            if data:
                order_books[name] = data
    return order_books


async def fetch_order_book(exchange, symbol, name):
    try:
        order_book = await exchange.fetch_order_book(symbol)
        bid = order_book['bids'][0][0] if order_book['bids'] else None
        ask = order_book['asks'][0][0] if order_book['asks'] else None
        return name, {'bid': bid, 'ask': ask}
    except Exception as e:
        logging.error(f"Error fetching order book from {
                      name}: {type(e).__name__} - {e}")
        return None


def calculate_profit(buy_price, sell_price, buy_fee, sell_fee, amount):
    buy_cost = buy_price * amount * (1 + buy_fee)
    sell_revenue = sell_price * amount * (1 - sell_fee)
    profit = sell_revenue - buy_cost
    profit_percent = (profit / buy_cost) * 100
    return profit_percent, profit


async def check_arbitrage_opportunities(exchanges, order_books):
    opportunities = []
    exchange_names = list(order_books.keys())
    for buy_ex_name in exchange_names:
        for sell_ex_name in exchange_names:
            if buy_ex_name == sell_ex_name:
                continue
            buy_price = order_books[buy_ex_name]['ask']
            sell_price = order_books[sell_ex_name]['bid']
            if buy_price and sell_price and buy_price < sell_price:
                buy_fee = exchanges[buy_ex_name]['fees']['taker']
                sell_fee = exchanges[sell_ex_name]['fees']['taker']
                amount = min(trade_amount, max_trade_amount)
                profit_percent, profit = calculate_profit(
                    buy_price, sell_price, buy_fee, sell_fee, amount
                )
                if profit_percent >= min_profit_percent:
                    opportunity = {
                        'buy_exchange': buy_ex_name,
                        'sell_exchange': sell_ex_name,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'profit_percent': profit_percent,
                        'profit': profit,
                        'amount': amount,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    opportunities.append(opportunity)
    return opportunities


async def check_balance(exchange, currency, amount):
    try:
        balance = await exchange.fetch_balance()
        available = balance.get(currency, {}).get('free', 0)
        if available >= amount:
            return True
        else:
            logging.warning(f"Insufficient balance on {exchange.id}: needed {
                            amount}, available {available}")
            return False
    except Exception as e:
        logging.error(f"Failed to fetch balance from {
                      exchange.id}: {type(e).__name__} - {e}")
        return False


async def execute_trade(buy_exchange_info, sell_exchange_info, opportunity):
    buy_exchange = buy_exchange_info['instance']
    sell_exchange = sell_exchange_info['instance']
    amount = opportunity['amount']
    buy_price = opportunity['buy_price']
    sell_price = opportunity['sell_price']
    buy_symbol = buy_exchange_info['symbol']
    sell_symbol = sell_exchange_info['symbol']

    # Place buy order
    try:
        buy_order = await buy_exchange.create_limit_buy_order(buy_symbol, amount, buy_price)
        logging.info(f"Buy order placed on {
                     buy_exchange.id}: {buy_order['id']}")
    except Exception as e:
        logging.error(f"Failed to place buy order on {
                      buy_exchange.id}: {type(e).__name__} - {e}")
        return False

    # Place sell order
    try:
        sell_order = await sell_exchange.create_limit_sell_order(sell_symbol, amount, sell_price)
        logging.info(f"Sell order placed on {
                     sell_exchange.id}: {sell_order['id']}")
    except Exception as e:
        logging.error(f"Failed to place sell order on {
                      sell_exchange.id}: {type(e).__name__} - {e}")
        # Attempt to cancel buy order
        try:
            await buy_exchange.cancel_order(buy_order['id'], buy_symbol)
            logging.info(f"Buy order {buy_order['id']} canceled on {
                         buy_exchange.id}")
        except Exception as cancel_e:
            logging.error(f"Failed to cancel buy order {buy_order['id']} on {
                          buy_exchange.id}: {type(cancel_e).__name__} - {cancel_e}")
        return False

    # Monitor order statuses
    buy_filled = await monitor_order(buy_exchange, buy_order['id'], buy_symbol)
    sell_filled = await monitor_order(sell_exchange, sell_order['id'], sell_symbol)

    if buy_filled and sell_filled:
        logging.info("Both buy and sell orders fully executed.")
        return True
    else:
        logging.warning(
            "Order execution incomplete. Manual intervention may be required.")
        return False


async def monitor_order(exchange, order_id, symbol, timeout=60):
    """Monitor an order until it is filled or timeout occurs."""
    start_time = datetime.utcnow()
    while (datetime.utcnow() - start_time).seconds < timeout:
        try:
            order = await exchange.fetch_order(order_id, symbol)
            if order['status'] == 'closed':
                return True
            elif order['status'] == 'canceled':
                logging.warning(f"Order {order_id} on {
                                exchange.id} was canceled.")
                return False
        except Exception as e:
            logging.error(f"Error fetching order status {order_id} on {
                          exchange.id}: {type(e).__name__} - {e}")
        await asyncio.sleep(5)
    logging.warning(f"Order {order_id} on {
                    exchange.id} not filled within timeout.")
    return False


async def main():
    exchanges = await init_exchanges()
    if not exchanges:
        logging.error("No exchanges initialized. Exiting.")
        return

    try:
        while True:
            order_books = await fetch_order_books(exchanges)
            if not order_books:
                logging.warning("No order books fetched. Retrying...")
                await asyncio.sleep(check_interval)
                continue

            opportunities = await check_arbitrage_opportunities(exchanges, order_books)
            if opportunities:
                for opp in opportunities:
                    logging.info(f"Arbitrage opportunity detected: {opp}")
                    buy_ex_info = exchanges[opp['buy_exchange']]
                    sell_ex_info = exchanges[opp['sell_exchange']]

                    buy_currency = trade_currency
                    sell_currency = trade_currency

                    buy_balance_ok = await check_balance(
                        buy_ex_info['instance'],
                        buy_currency,
                        opp['buy_price'] * opp['amount'] *
                        (1 + buy_ex_info['fees']['taker'])
                    )
                    sell_balance_ok = await check_balance(
                        sell_ex_info['instance'],
                        opp['amount_symbol'] if 'amount_symbol' in opp else trade_currency,
                        opp['amount']
                    )

                    if buy_balance_ok and sell_balance_ok:
                        success = await execute_trade(
                            buy_exchange_info=buy_ex_info,
                            sell_exchange_info=sell_ex_info,
                            opportunity=opp
                        )
                        if success:
                            logging.info(
                                "Arbitrage trade executed successfully.")
                        else:
                            logging.warning(
                                "Arbitrage trade execution failed.")
                    else:
                        logging.warning(
                            "Insufficient balance to execute arbitrage trade.")
            else:
                logging.info("No arbitrage opportunities at this time.")
            await asyncio.sleep(check_interval)
    except Exception as e:
        logging.error(f"An error occurred in the main loop: {
                      type(e).__name__} - {e}")
    finally:
        await close_exchanges(exchanges)


async def close_exchanges(exchanges):
    for ex in exchanges.values():
        await ex['instance'].close()
    logging.info("All exchanges closed.")

if __name__ == '__main__':
    asyncio.run(main())
