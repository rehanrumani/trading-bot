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
    
    def _generate_signature(self, method: str, path: str, query_string: str = "", body: str = "") -> str:
        """Generate HMAC SHA256 signature for 3Commas API"""
        if not self.api_secret:
            raise ValueError("API secret not configured")
        
        # Correct 3Commas signature format: method + path + body + query_string
        signature_base = method.upper() + path + body + query_string
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_base.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Signature base: {signature_base}")
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Optional[Dict]:
        """Make authenticated request to 3Commas API"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                query_string = ""
                if params:
                    query_string = urllib.parse.urlencode(params, safe='')
                
                signature = self._generate_signature('GET', endpoint, query_string)
                headers = {
                    'APIKEY': self.api_key,
                    'Signature': signature
                }
                response = requests.get(url, params=params, headers=headers, timeout=30)
            
            elif method.upper() == 'POST':
                body = ""
                if params:
                    body = json.dumps(params, separators=(',', ':'))
                
                signature = self._generate_signature('POST', endpoint, "", body)
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
    
    def create_smart_trade(self, signal_data: Dict) -> Dict:
        """Create a SmartTrade based on signal data"""
        try:
            pair = signal_data['pair']
            take_profit_pct = signal_data['take_profit'] * 100  # Convert to percentage
            stop_loss_pct = signal_data.get('stop_loss', 0.15) * 100
            base_order_size = signal_data.get('base_order_size', 50.0)
            
            # SmartTrade parameters
            if not self.account_id:
                raise ValueError("Account ID not configured")
            smart_trade_params = {
                "account_id": int(self.account_id),
                "pair": pair,
                "position": {
                    "type": "buy",
                    "order_type": "market",
                    "units": {
                        "value": str(base_order_size)
                    }
                },
                "take_profit": {
                    "enabled": True,
                    "steps": [
                        {
                            "order_type": "market",
                            "price": {
                                "value": str(take_profit_pct),
                                "type": "bid"
                            },
                            "volume": 100
                        }
                    ]
                },
                "stop_loss": {
                    "enabled": True,
                    "order_type": "market",
                    "conditional": {
                        "price": {
                            "value": str(stop_loss_pct),
                            "type": "ask"
                        }
                    }
                },
                "note": f"AI Generated Signal - Confidence: {signal_data.get('confidence', 0):.2f}"
            }
            
            endpoint = "/public/api/v2/smart_trades"
            result = self._make_request('POST', endpoint, smart_trade_params)
            
            if result:
                logger.info(f"SmartTrade created successfully: {result.get('id')}")
                return {
                    "success": True,
                    "trade_id": result.get('id'),
                    "message": "SmartTrade created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create SmartTrade"
                }
                
        except Exception as e:
            logger.error(f"Error creating SmartTrade: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_dca_bot(self, signal_data: Dict) -> Dict:
        """Create a DCA bot based on signal data"""
        try:
            pair = signal_data['pair']
            take_profit_pct = signal_data['take_profit'] * 100
            base_order_size = signal_data.get('base_order_size', 50.0)
            
            # DCA Bot parameters  
            if not self.account_id:
                raise ValueError("Account ID not configured")
            dca_params = {
                "account_id": int(self.account_id),
                "pair": pair,
                "base_order_volume": base_order_size,
                "base_order_volume_type": "quote_currency",
                "take_profit": take_profit_pct,
                "safety_order_volume": base_order_size * 0.5,  # 50% of base order
                "martingale_volume_coefficient": 1.05,
                "martingale_step_coefficient": 1.0,
                "max_safety_orders": 10,
                "active_safety_orders_count": 10,
                "safety_order_step_percentage": 2.5,
                "take_profit_type": "total",
                "strategy_list": [],
                "name": f"AI Bot - {pair} - {int(time.time())}",
                "bot_type": "Bot::MultiBot"
            }
            
            endpoint = "/public/api/ver1/bots/create_bot"
            result = self._make_request('POST', endpoint, dca_params)
            
            if result:
                # Enable the bot
                bot_id = result.get('id')
                enable_result = self._make_request('POST', f"/public/api/ver1/bots/{bot_id}/enable")
                
                if enable_result:
                    logger.info(f"DCA Bot created and enabled: {bot_id}")
                    return {
                        "success": True,
                        "trade_id": bot_id,
                        "message": "DCA Bot created and enabled successfully"
                    }
                else:
                    logger.warning(f"DCA Bot created but failed to enable: {bot_id}")
                    return {
                        "success": True,
                        "trade_id": bot_id,
                        "message": "DCA Bot created but not enabled"
                    }
            else:
                return {
                    "success": False,
                    "error": "Failed to create DCA Bot"
                }
                
        except Exception as e:
            logger.error(f"Error creating DCA Bot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_buy_signal(self, signal_data: Dict) -> Dict:
        """Execute a buy signal using SmartTrade (primary) or DCA Bot (fallback)"""
        try:
            logger.info(f"Executing BUY signal for {signal_data['pair']}")
            
            # Try SmartTrade first
            result = self.create_smart_trade(signal_data)
            
            if result['success']:
                return result
            else:
                logger.warning("SmartTrade failed, trying DCA Bot as fallback")
                return self.create_dca_bot(signal_data)
                
        except Exception as e:
            logger.error(f"Error executing buy signal: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trade history"""
        try:
            # Get SmartTrades
            endpoint = "/public/api/v2/smart_trades"
            params = {"account_id": self.account_id, "limit": limit}
            smart_trades = self._make_request('GET', endpoint, params)
            
            # Get DCA Bots
            endpoint = "/public/api/ver1/bots"
            params = {"account_id": self.account_id, "limit": limit}
            dca_bots = self._make_request('GET', endpoint, params)
            
            trades = []
            
            if smart_trades:
                for trade in smart_trades:
                    trades.append({
                        "type": "SmartTrade",
                        "id": trade.get('id'),
                        "pair": trade.get('pair'),
                        "status": trade.get('status'),
                        "created_at": trade.get('created_at'),
                        "profit": trade.get('profit', {})
                    })
            
            if dca_bots:
                for bot in dca_bots:
                    trades.append({
                        "type": "DCA Bot",
                        "id": bot.get('id'),
                        "pair": bot.get('pairs', [''])[0],
                        "status": bot.get('is_enabled'),
                        "created_at": bot.get('created_at'),
                        "profit": bot.get('usd_final_profit', 0)
                    })
            
            return sorted(trades, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return []
