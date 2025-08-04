"""
3Commas API integration for executing cryptocurrency trades.
Handles SmartTrade and DCA bot operations with proper v2 API authentication.
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
        
        logger.info(f"3Commas Trader initialized with Account ID: {self.account_id}")
        if not all([self.api_key, self.api_secret, self.account_id]):
            logger.error("Missing 3Commas API credentials in environment variables")
    
    def _generate_signature(self, method: str, path: str, params: Optional[dict] = None) -> Dict[str, str]:
        """Generate HMAC SHA256 signature for 3Commas API v2 with timestamp"""
        if not self.api_secret:
            raise ValueError("API secret not configured")
        
        timestamp = str(int(time.time() * 1000))
        
        # Build query string for GET requests
        if params and method.upper() == 'GET':
            query_string = urllib.parse.urlencode(sorted(params.items()))
            if query_string:
                path = f"{path}?{query_string}"
        
        # Create signature message: timestamp + method + path
        message = f"{timestamp}{method.upper()}{path}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'timestamp': timestamp,
            'signature': signature
        }
    
    def _make_request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Optional[Dict]:
        """Make authenticated request to 3Commas API v2"""
        try:
            path = f"/public/api/v2{endpoint}"
            url = f"{self.base_url}{path}"
            
            # Generate signature with timestamp
            sig_data = self._generate_signature(method, path, params if method.upper() == 'GET' else None)
            
            headers = {
                'APIKEY': self.api_key,
                'Signature': sig_data['signature'],
                'Timestamp': sig_data['timestamp'],
                'Content-Type': 'application/json'
            }
            
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=params, headers=headers, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            logger.info(f"3Commas API: {method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.text
                logger.error(f"3Commas API error: {response.status_code} - {error_msg}")
                return {"error": f"API error: {response.status_code}", "message": error_msg}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to 3Commas API: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in 3Commas API call: {str(e)}")
            return {"error": str(e)}
    
    def get_account_info(self) -> Dict:
        """Get account information and balance"""
        try:
            result = self._make_request('GET', '/accounts')
            
            if result and not result.get('error'):
                # Find the account with matching ID
                accounts = result if isinstance(result, list) else [result]
                for account in accounts:
                    if str(account.get('id')) == str(self.account_id):
                        return {
                            "account_id": account.get('id'),
                            "name": account.get('name'),
                            "market_code": account.get('market_code'),
                            "currency_code": account.get('currency_code'),
                            "status": "active"
                        }
                return {"status": "error", "message": "Account not found"}
            else:
                return {"status": "error", "message": "Failed to get account info"}
                
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
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
            pair = signal_data.get('pair', 'BTC_USDT').replace('/', '_')
            take_profit_pct = float(signal_data.get('take_profit', 0.25)) * 100
            stop_loss_pct = float(signal_data.get('stop_loss', 0.15)) * 100
            base_order_size = signal_data.get('base_order_size', 50.0)
            
            # CRITICAL FIX: DCA Bot parameters with proper pairs array format
            if not self.account_id:
                raise ValueError("Account ID not configured")
            dca_params = {
                "account_id": int(self.account_id),
                "pairs": [pair],  # CRITICAL: Must be array, not string
                "base_order_volume": str(base_order_size),
                "take_profit": str(take_profit_pct),
                "safety_order_volume": str(base_order_size * 0.5),
                "martingale_volume_coefficient": "1.2",
                "martingale_step_coefficient": "1.0",
                "max_safety_orders": "10",
                "active_safety_orders_count": "10",
                "safety_order_step_percentage": "2.5",
                "take_profit_type": "total",
                "strategy_list": [{"strategy": "long"}],
                "stop_loss_percentage": str(stop_loss_pct),
                "cooldown": "300",
                "name": f"AI-Bot-{pair}-{int(time.time())}"
            }
            
            logger.info(f"Creating DCA Bot for {pair} with pairs: {dca_params['pairs']}")
            result = self._make_request('POST', '/bots/create_bot', dca_params)
            
            if result and not result.get('error'):
                bot_id = result.get('id')
                logger.info(f"DCA Bot created successfully: {bot_id}")
                return {
                    "success": True,
                    "trade_id": bot_id,
                    "message": "DCA Bot created successfully"
                }
            else:
                error_msg = result.get('message', 'Failed to create DCA Bot') if result else 'Failed to create DCA Bot'
                logger.error(f"DCA Bot creation failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Error creating DCA Bot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_trade(self, signal_data: Dict) -> Dict:
        """Execute a trade signal using SmartTrade (primary) or DCA Bot (fallback)"""
        try:
            signal_type = signal_data.get('signal', '').upper()
            
            if signal_type != 'BUY':
                return {"status": "skipped", "message": f"Signal type {signal_type} not supported"}
            
            logger.info(f"Executing BUY signal for {signal_data.get('pair')}")
            
            # Try SmartTrade first
            result = self.create_smart_trade(signal_data)
            
            if result.get('success'):
                logger.info("Successfully created SmartTrade")
                return {"status": "success", "message": "SmartTrade created", "data": result}
            else:
                logger.warning("SmartTrade failed, trying DCA Bot as fallback")
                # Fallback to DCA Bot
                dca_result = self.create_dca_bot(signal_data)
                
                if dca_result.get('success'):
                    logger.info("Successfully created DCA Bot")
                    return {"status": "success", "message": "DCA Bot created", "data": dca_result}
                else:
                    error_msg = dca_result.get('error', 'Unknown error')
                    logger.error(f"Failed to execute trade: {error_msg}")
                    return {"status": "error", "message": f"Failed to create DCA Bot"}
                
        except Exception as e:
            logger.error(f"Error executing trade signal: {str(e)}")
            return {
                "status": "error", 
                "message": str(e)
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
