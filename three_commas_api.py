"""
3Commas API integration for executing cryptocurrency trades.
Handles SmartTrade and DCA bot operations.
"""

import hashlib
import hmac
import time
import urllib.parse
import requests
import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ThreeCommasTrader:
    def __init__(self):
        self.api_key = os.getenv('THREE_COMMAS_API_KEY')
        self.api_secret = os.getenv('THREE_COMMAS_SECRET')
        self.account_id = os.getenv('ACCOUNT_ID')
        self.base_url = "https://api.3commas.io"
        
        if not all([self.api_key, self.api_secret, self.account_id]):
            logger.error("Missing 3Commas API credentials in environment variables")
    
    def _generate_signature(self, path: str, query_string: str = "", body: str = "") -> str:
        """Generate HMAC SHA256 signature for 3Commas API"""
        if not self.api_secret:
            raise ValueError("API secret not configured")
        
        # For 3Commas API: signature = HMAC-SHA256(secret, path + query_string + body)
        if query_string and not query_string.startswith('?'):
            query_string = '?' + query_string
        
        signature_base = path + query_string + body
        
        return hmac.new(
            self.api_secret.encode('utf-8'),
            signature_base.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Optional[Dict]:
        """Make authenticated request to 3Commas API"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                query_string = ""
                if params:
                    query_string = urllib.parse.urlencode(params)
                
                signature = self._generate_signature(endpoint, query_string)
                headers = {
                    'APIKEY': self.api_key,
                    'Signature': signature
                }
                response = requests.get(url, params=params, headers=headers, timeout=30)
            
            elif method.upper() == 'POST':
                body = ""
                if params:
                    body = json.dumps(params, separators=(',', ':'))
                
                signature = self._generate_signature(endpoint, "", body)
                headers = {
                    'APIKEY': self.api_key,
                    'Signature': signature,
                    'Content-Type': 'application/json'
                }
                
                if params:
                    response = requests.post(url, data=body, headers=headers, timeout=30)
                else:
                    response = requests.post(url, headers=headers, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"3Commas API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to 3Commas API: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in 3Commas API call: {str(e)}")
            return None
    
    def get_account_status(self) -> Dict:
        """Get account information and balance"""
        try:
            endpoint = f"/public/api/ver1/accounts/{self.account_id}"
            result = self._make_request('GET', endpoint)
            
            if result:
                return {
                    "account_id": result.get('id'),
                    "name": result.get('name'),
                    "market_code": result.get('market_code'),
                    "currency_code": result.get('currency_code'),
                    "balance": result.get('day_profit_percentage'),
                    "status": "active"
                }
            else:
                return {"status": "error", "message": "Failed to get account info"}
                
        except Exception as e:
            logger.error(f"Error getting account status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def create_dca_bot(self, signal_data: Dict) -> Dict:
        """Create DCA bot from trading signal"""
        try:
            # Map signal data to 3Commas DCA bot parameters
            pair = signal_data.get('pair', 'BTC_USDT').replace('/', '_')
            base_order_size = signal_data.get('base_order_size', 50)
            take_profit = signal_data.get('take_profit', 0.25) * 100  # Convert to percentage
            stop_loss = signal_data.get('stop_loss', 0.15) * 100
            
            bot_params = {
                "name": f"MARCO_GLITCH_{pair}_{int(time.time())}",
                "account_id": int(self.account_id),
                "pairs": [pair],
                "base_order_volume": base_order_size,
                "take_profit": take_profit,
                "safety_order_volume": base_order_size * 0.5,
                "martingale_volume_coefficient": 1.0,
                "martingale_step_coefficient": 1.0,
                "max_safety_orders": 10,
                "safety_order_step_percentage": 2.5,
                "take_profit_type": "total",
                "strategy_list": [{
                    "strategy": "nonstop"
                }],
                "stop_loss_percentage": stop_loss,
                "cooldown": 600
            }
            
            endpoint = "/public/api/ver1/bots/create_bot"
            result = self._make_request('POST', endpoint, bot_params)
            
            if result:
                bot_id = result.get('id')
                # Start the bot immediately
                start_endpoint = f"/public/api/ver1/bots/{bot_id}/start"
                start_result = self._make_request('POST', start_endpoint)
                
                return {
                    "success": True,
                    "bot_id": bot_id,
                    "message": f"DCA Bot created and started for {pair}",
                    "take_profit": take_profit,
                    "stop_loss": stop_loss
                }
            else:
                return {"success": False, "message": "Failed to create DCA Bot"}
                
        except Exception as e:
            logger.error(f"Error creating DCA bot: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_active_bots(self) -> List[Dict]:
        """Get list of active trading bots"""
        try:
            endpoint = "/public/api/ver1/bots"
            params = {"account_id": self.account_id}
            result = self._make_request('GET', endpoint, params)
            
            if result and isinstance(result, list):
                active_bots = [bot for bot in result if bot.get('is_enabled')]
                return active_bots
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting active bots: {str(e)}")
            return []
