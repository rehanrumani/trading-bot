"""
Flask application for receiving trading signals and executing trades via 3Commas API.
This runs on Render and receives signals from the Replit signal generator.
"""

from flask import Flask, request, jsonify
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from three_commas_api import ThreeCommasTrader
from config import TRADING_PAIRS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_execution.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize 3Commas trader
trader = ThreeCommasTrader()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "crypto-trading-executor"
    })

@app.route('/tv_signal', methods=['POST'])
def receive_trading_signal():
    """Receive and process trading signals from Replit"""
    try:
        # Get signal data
        signal_data = request.get_json()
        
        if not signal_data:
            logger.error("No JSON data received")
            return jsonify({"error": "No data provided"}), 400
        
        logger.info(f"Received trading signal: {signal_data}")
        
        # Validate required fields
        required_fields = ['signal', 'pair', 'take_profit', 'stop_loss']
        missing_fields = [field for field in required_fields if field not in signal_data]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({"error": f"Missing fields: {missing_fields}"}), 400
        
        # Validate pair
        if signal_data['pair'] not in TRADING_PAIRS:
            logger.error(f"Invalid trading pair: {signal_data['pair']}")
            return jsonify({"error": "Invalid trading pair"}), 400
        
        # Process signal
        if signal_data['signal'] == 'BUY':
            result = trader.execute_trade(signal_data)
            
            if result.get('status') == 'success':
                logger.info(f"Successfully executed BUY for {signal_data['pair']}")
                return jsonify({
                    "status": "success",
                    "message": result.get('message', 'Trade executed successfully'),
                    "trade_id": result.get('data', {}).get('trade_id'),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Failed to execute trade: {error_msg}")
                return jsonify({
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        elif signal_data['signal'] == 'HOLD':
            logger.info(f"HOLD signal received for {signal_data['pair']} - no action taken")
            return jsonify({
                "status": "acknowledged",
                "message": "HOLD signal received, no action taken",
                "timestamp": datetime.now().isoformat()
            })
        
        elif signal_data['signal'] == 'TEST':
            logger.info("Test signal received")
            return jsonify({
                "status": "test_acknowledged",
                "message": "Test signal received successfully",
                "timestamp": datetime.now().isoformat()
            })
        
        else:
            logger.error(f"Invalid signal type: {signal_data['signal']}")
            return jsonify({"error": "Invalid signal type"}), 400
    
    except Exception as e:
        logger.error(f"Error processing trading signal: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get trading bot status and statistics"""
    try:
        status = trader.get_account_status()
        
        return jsonify({
            "status": "operational",
            "account_info": status,
            "timestamp": datetime.now().isoformat(),
            "supported_pairs": TRADING_PAIRS
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/trades', methods=['GET'])
def get_recent_trades():
    """Get recent trade history"""
    try:
        trades = trader.get_recent_trades()
        
        return jsonify({
            "trades": trades,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    # Verify environment variables
    required_vars = ['THREE_COMMAS_API_KEY', 'THREE_COMMAS_SECRET', 'ACCOUNT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    logger.info("Starting crypto trading execution service on Render")
    logger.info(f"Supported trading pairs: {', '.join(TRADING_PAIRS)}")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
