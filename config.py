"""
Configuration settings for the AI-powered crypto trading system.
Contains trading pairs, intervals, and system parameters.
"""

import os

# Trading Configuration
TRADING_PAIRS = [
    "BTC/USDT",
    "ETH/USDT", 
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT"
]

# Signal generation interval in seconds
SIGNAL_INTERVAL = 45

# Trading Parameters
BASE_ORDER_SIZE = 50.0  # $50 base order
INITIAL_CAPITAL = 450.0  # $450 initial capital
MAX_SAFETY_ORDERS = 10
SAFETY_ORDER_MULTIPLIER = 0.5  # 50% of base order
SAFETY_ORDER_STEP_PERCENTAGE = 2.5

# Risk Management
DEFAULT_TAKE_PROFIT = 0.30  # 30%
DEFAULT_STOP_LOSS = 0.15   # 15%
MIN_TAKE_PROFIT = 0.25     # 25%
MAX_TAKE_PROFIT = 0.35     # 35%
MIN_STOP_LOSS = 0.10       # 10%
MAX_STOP_LOSS = 0.20       # 20%

# GPT Configuration
GPT_MODEL = "openai/gpt-4o"
GPT_TEMPERATURE = 0.3
GPT_MAX_TOKENS = 500
MIN_CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for BUY signals

# API Configuration
OPENROUTER_TIMEOUT = 30
RENDER_TIMEOUT = 30
THREE_COMMAS_TIMEOUT = 30

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# System Configuration
RESTART_DELAY = 10  # Seconds to wait before restarting on error
MAX_RETRIES = 3     # Maximum retries for API calls

# Environment Variables Validation
REQUIRED_ENV_VARS = [
    'OPENROUTER_API_KEY',
    'RENDER_ENDPOINT',
    'THREE_COMMAS_API_KEY',
    'THREE_COMMAS_SECRET',
    'ACCOUNT_ID'
]

def validate_environment():
    """Validate that all required environment variables are set"""
    missing_vars = []
    
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

# Trading Pair Validation
def validate_trading_pair(pair: str) -> bool:
    """Validate if a trading pair is supported"""
    return pair in TRADING_PAIRS

# Signal Validation
def validate_signal_parameters(signal: dict) -> bool:
    """Validate signal parameters are within acceptable ranges"""
    if 'take_profit' in signal:
        if not (MIN_TAKE_PROFIT <= signal['take_profit'] <= MAX_TAKE_PROFIT):
            return False
    
    if 'stop_loss' in signal:
        if not (MIN_STOP_LOSS <= signal['stop_loss'] <= MAX_STOP_LOSS):
            return False
    
    if 'confidence' in signal:
        if not (0.0 <= signal['confidence'] <= 1.0):
            return False
    
    return True

# System Status
SYSTEM_INFO = {
    "name": "AI-Powered Crypto Trading System",
    "version": "1.0.0",
    "description": "Automated cryptocurrency trading using GPT signals and 3Commas execution",
    "author": "AI Trading Bot",
    "supported_pairs": len(TRADING_PAIRS),
    "signal_interval": SIGNAL_INTERVAL,
    "base_order_size": BASE_ORDER_SIZE
}
