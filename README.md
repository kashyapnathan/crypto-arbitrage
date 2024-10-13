# Crypto Arbitrage Bot

## Disclaimer

This Crypto Arbitrage Bot is for educational and research purposes only. Cryptocurrency trading carries a high level of risk, and may not be suitable for all investors. Before deciding to trade cryptocurrency, you should carefully consider your investment objectives, level of experience, and risk appetite. The possibility exists that you could sustain a loss of some or all of your initial investment and therefore you should not invest money that you cannot afford to lose. You should be aware of all the risks associated with cryptocurrency trading, and seek advice from an independent financial advisor if you have any doubts. This project is an educational exercise and not intended to be assumed as an actionable financial model.

## Overview
This project implements a **Crypto Arbitrage Bot** designed to detect and exploit price discrepancies between different cryptocurrency exchanges. The bot continuously monitors bid-ask spreads and executes arbitrage opportunities when favorable conditions arise. Specifically, this bot identifies inter-exchange arbitrage opportunities by analyzing price data in real-time from multiple exchanges such as **Coinbase** and **Bitfinex**.

The architecture leverages Python for real-time data collection, analysis, and multi-threaded execution of trades. It supports both **market orders** and **limit orders**, with detailed handling of exchange-specific APIs, fee structures, and latency challenges.

## Architecture

The bot is structured in the following components:

- **Data Collection Layer**: This module continuously fetches live price data, including bid/ask spreads, order book depth, and recent trade history. Data is collected using REST APIs provided by the exchanges. The data is synchronized and stored in-memory for rapid access by the arbitrage execution engine.
  
- **Arbitrage Detection Engine**: This module identifies arbitrage opportunities by calculating potential profits after accounting for fees, slippage, and latency. It looks for opportunities where the buy price on one exchange (e.g., **Coinbase**) is lower than the sell price on another exchange (e.g., **Bitfinex**).

- **Execution Engine**: The engine handles the execution of trades once an arbitrage opportunity is detected. It leverages multi-threading to reduce latency and simultaneously execute buy and sell orders on different exchanges. Order execution is done through the exchanges' APIs (via Python libraries), with support for handling errors such as timeouts, partial fills, or failed orders.

- **Backtesting Module**: The backtest functionality allows for testing the bot on historical data. It can simulate trades, calculate potential profits, and provide detailed metrics such as average trade duration, trade frequency, profit per trade, etc.

- **Risk Management Module**: This module ensures that risks associated with live trading are mitigated. It includes:
  - **Fee Calculation**: Considers both maker and taker fees for each trade and adjusts profitability calculations accordingly.
  - **Slippage and Spread Protection**: Monitors the spread between bid/ask prices to avoid executing trades where slippage would eliminate profit margins.
  - **Liquidity Check**: Ensures that the order sizes are within the depth of the order book to avoid significant market impact.

## Installation

### Prerequisites:
- Python 3.9 or later
- Virtualenv (Optional but recommended)
  
### Clone the Repository
```bash
git clone https://github.com/kashyapnathan/crypto-arbitrage.git
cd crypto-arbitrage-bot
```

### Install Dependencies
Make sure to install the required Python dependencies by running the following command:
```bash
pip install -r requirements.txt
```

### Environment Setup

You'll need to set up environment variables for your API keys for each exchange in a `.env` file in the root directory.

Example `.env` file:
```bash
COINBASE_API_KEY=your_coinbase_api_key
COINBASE_SECRET_KEY=your_coinbase_secret_key

BITFINEX_API_KEY=your_bitfinex_api_key
BITFINEX_SECRET_KEY=your_bitfinex_secret_key
```

### Configuration

The configuration for each exchange is stored in `config.json`. This file contains details such as API keys, fee structure, and trade parameters. Make sure to adjust the fees and API keys according to your account and exchanges.

Example `config.json`:
```json
{
  "exchanges": [
    {
      "name": "coinbase",
      "api_key_env": "COINBASE_API_KEY",
      "secret_key_env": "COINBASE_SECRET_KEY",
      "fees": {
        "taker": 0.005,
        "maker": 0.005
      }
    },
    {
      "name": "bitfinex",
      "api_key_env": "BITFINEX_API_KEY",
      "secret_key_env": "BITFINEX_SECRET_KEY",
      "fees": {
        "taker": 0.002,
        "maker": 0.001
      }
    }
  ],
  "trading_pairs": ["BTC/USD"],
  "trade_amount": 0.01,
  "max_open_trades": 10
}
```

### Running the Backtest

You can run the backtest to simulate trades over historical data. Ensure that the data files for each exchange are placed in the `data/` directory.

```bash
python backtest.py
```

#### Example Backtest Output:
```
Profit of $571.70 made in 0:31:00
----------------------------------
Total Profit:           $571.70
Number of Trades:       317
Time Frame:             31 minutes

Advanced Metrics:
-----------------
Avg Profit per Trade:   $1.80
Largest Single Profit:  $1.81
Largest Single Loss:    $1.75
Avg Trade Duration:     1.00 minutes
Total Return:           18.16%
```

### Running the Bot in Live Mode

To run the bot live in real markets, use the following command:
```bash
python arbitrage_bot.py
```
**Note**: Ensure you start with small trades to validate performance and check live profitability before scaling up.

### Key Functions

- **arbitrage_bot.py**: The main execution script for running live arbitrage trading.
- **backtest.py**: Script to run backtesting on historical data and validate performance of the arbitrage strategy.
- **data.py**: Handles data fetching from exchanges using API calls.
- **trade_log.csv**: Keeps a detailed log of trades made, including timestamp, exchanges, buy/sell prices, and profit.

### Error Handling

The bot has been designed with error handling mechanisms for common issues such as:
- **API Timeouts**: Automatically retries API calls with exponential backoff if requests time out.
- **Partial Fills**: Monitors the order book and adjusts for partially filled trades.
- **Connection Failures**: Gracefully handles network issues and continues execution.

## Future Enhancements

1. **Support for Additional Exchanges**: Adding support for more exchanges such as Binance, Kraken, or Huobi.
2. **More Sophisticated Arbitrage Models**: Incorporating triangular arbitrage and more complex trade routes across multiple trading pairs.
3. **Improved Risk Management**: Adding volatility-based risk management to avoid trading during extreme market conditions.
4. **Latency Optimization**: Improving multi-threading and reducing the latency of API calls to minimize execution risk.
5. **Order Book Analysis**: Implementing real-time order book analysis to ensure that liquidity constraints are dynamically managed.

## Risks & Limitations

- **Slippage**: While the bot accounts for slippage in backtesting, real-world conditions may lead to higher slippage than expected, especially during periods of high volatility.
- **Liquidity Constraints**: Large trade sizes could potentially move the market, resulting in suboptimal trade execution.
- **Latency**: Delays between exchanges and your bot can result in missed arbitrage opportunities.
- **Fees**: Transaction fees can erode profits, especially for smaller arbitrage margins. Make sure fees are factored in correctly.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
