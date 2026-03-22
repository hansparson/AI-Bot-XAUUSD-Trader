# AI-Bot-XAUUSD-Trader

Automated AI-driven trading bot for XAUUSD (Gold) integrated with MetaTrader 5.

## 🚀 Overview

**AI-Bot-XAUUSD-Trader** is a sophisticated trading system that combines the power of AI analysis with the robust execution of MetaTrader 5. It specializes in XAUUSD (Gold) trading, utilizing advanced evaluation models to confirm signals before execution.

## ✨ Key Features

- **MT5 Bridge**: Direct integration with MetaTrader 5 terminal for low-latency execution.
- **AI Signal Evaluation**: Supports both local (Ollama/Qwen) and cloud-based (Gemini) AI models for trade validation.
- **Automated Trading**: End-to-end automation from market monitoring to trade exit.
- **SQLite Logging**: Comprehensive tracking of every AI decision and trade result in a local database.
- **Dynamic Configuration**: Easily switch between DEMO and LIVE accounts via `.env`.

## 🛠️ Setup & Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/hansparson/AI-Bot-XAUUSD-Trader.git
    cd AI-Bot-XAUUSD-Trader
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file based on your MT5 credentials:
    ```ini
    ACCOUNT_MODE=DEMO
    MT5_DEMO_LOGIN=your_login
    MT5_DEMO_PASSWORD=your_password
    MT5_DEMO_SERVER=your_server
    SYMBOL=XAUUSD.m
    AI_MODE=LOCAL # or CLOUD
    GEMINI_API_KEY=your_api_key
    ```

4.  **Run the Bot**:
    - Build the database: `python scripts/db_setup.py`
    - Start the engine: `python main.py`

## 📊 Project Structure

- `core/`: Core trading logic and AI evaluation modules.
- `scripts/`: Utility scripts for database setup and manual tools.
- `utils/`: Common helper functions.
- `data/`: Local SQLite database storage.

## ⚠️ Disclaimer

Trading involves significant risk. This bot is for educational and research purposes. Always test on a DEMO account before considering live deployment. The author is not responsible for any financial losses incurred.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
