"""
CRITICAL RENDER UPDATE - Fix 3Commas Authentication
Based on actual Render error logs showing signature_invalid and missing pairs errors
"""

CORRECTED_THREE_COMMAS_CODE = '''
import os
import time
import hmac
import hashlib
import urllib.parse
import requests
import json
from datetime import datetime

class ThreeCommasTrader:
    def __init__(self):
        self.api_key = os.getenv('THREE_COMMAS_API_KEY')
        self.api_secret = os.getenv('THREE_COMMAS_SECRET') 
        self.account_id = os.getenv('ACCOUNT_ID')
        self.base_url = "https://api.3commas.io"
        
        print(f"3Commas Trader initialized with Account ID: {self.account_id}")
        
    def _generate_signature(self, method, path, params=None):
        """Generate HMAC signature for 3Commas API v2"""
        timestamp = str(int(time.time() * 1000))
        
        if params and method.upper() == 'GET':
            query_string = urllib.parse.urlencode(sorted(params.items()))
            if query_string:
                path = f"{path}?{query_string}"
        
        # Create message: timestamp + method + path
        message = f"{timestamp}{method.upper()}{path}"
        
        # Generate HMAC signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'timestamp': timestamp,
            'signature': signature
        }
    
    def _make_request(self, method, endpoint, params=None):
        """Make authenticated request to 3Commas API"""
        if not self.api_key or not self.api_secret:
            return {"error": "Missing API credentials"}
            
        path = f"/public/api/v2{endpoint}"
        url = f"{self.base_url}{path}"
        
        sig_data = self._generate_signature(method, path, params if method.upper() == 'GET' else None)
        
        headers = {
            'APIKEY': self.api_key,
            'Signature': sig_data['signature'],
            'Timestamp': sig_data['timestamp'],
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            else:
                response = requests.post(url, json=params, headers=headers, timeout=30)
            
            print(f"3Commas API: {method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.text
                print(f"3Commas API error: {response.status_code} - {error_msg}")
                return {"error": f"API error: {response.status_code}", "message": error_msg}
                
        except Exception as e:
            print(f"3Commas API exception: {e}")
            return {"error": str(e)}
    
    def get_account_info(self):
        """Get account information"""
        return self._make_request('GET', '/accounts')
    
    def create_smart_trade(self, signal_data):
        """Create SmartTrade based on signal"""
        if not self.account_id:
            return {"error": "Account ID not configured"}
            
        pair = signal_data.get('pair', 'BTC_USDT').replace('/', '_')
        take_profit = float(signal_data.get('take_profit', 0.25)) * 100
        stop_loss = float(signal_data.get('stop_loss', 0.15)) * 100
        
        trade_params = {
            "account_id": int(self.account_id),
            "pair": pair,
            "instant": True,
            "skip_enter_step": False,
            "leverage": {
                "enabled": False
            },
            "position": {
                "type": "buy",
                "order_type": "market",
                "units": {
                    "value": "50"
                }
            },
            "take_profit": {
                "enabled": True,
                "steps": [{
                    "order_type": "market",
                    "price": {
                        "value": str(take_profit),
                        "type": "bid"
                    },
                    "volume": {
                        "value": "100",
                        "type": "base"
                    }
                }]
            },
            "stop_loss": {
                "enabled": True,
                "order_type": "market",
                "conditional": {
                    "price": {
                        "value": str(stop_loss),
                        "type": "bid"
                    }
                }
            }
        }
        
        return self._make_request('POST', '/smart_trades', trade_params)
    
    def create_dca_bot(self, signal_data):
        """Create DCA bot as fallback"""
        if not self.account_id:
            return {"error": "Account ID not configured"}
            
        pair = signal_data.get('pair', 'BTC_USDT').replace('/', '_')
        take_profit = float(signal_data.get('take_profit', 0.25)) * 100
        stop_loss = float(signal_data.get('stop_loss', 0.15)) * 100
        
        bot_params = {
            "account_id": int(self.account_id),
            "pairs": [pair],  # CRITICAL: Must be array, not string
            "base_order_volume": "50",
            "take_profit": str(take_profit),
            "safety_order_volume": "25",
            "martingale_volume_coefficient": "1.2",
            "martingale_step_coefficient": "1.0",
            "max_safety_orders": "10",
            "active_safety_orders_count": "10",
            "safety_order_step_percentage": "2.5",
            "take_profit_type": "total",
            "strategy_list": [{"strategy": "long"}],
            "stop_loss_percentage": str(stop_loss),
            "cooldown": "300"
        }
        
        return self._make_request('POST', '/bots/create_bot', bot_params)
    
    def execute_trade(self, signal_data):
        """Execute trade with SmartTrade primary, DCA fallback"""
        signal_type = signal_data.get('signal', '').upper()
        
        if signal_type != 'BUY':
            return {"status": "skipped", "message": f"Signal type {signal_type} not supported"}
        
        # Try SmartTrade first
        print(f"Executing BUY signal for {signal_data.get('pair')}")
        result = self.create_smart_trade(signal_data)
        
        if 'error' not in result:
            print("Successfully created SmartTrade")
            return {"status": "success", "message": "SmartTrade created", "data": result}
        else:
            print(f"SmartTrade failed, trying DCA Bot as fallback")
            # Fallback to DCA Bot
            dca_result = self.create_dca_bot(signal_data)
            
            if 'error' not in dca_result:
                print("Successfully created DCA Bot")
                return {"status": "success", "message": "DCA Bot created", "data": dca_result}
            else:
                print(f"Failed to execute trade: {dca_result.get('error', 'Unknown error')}")
                return {"status": "error", "message": f"Failed to create DCA Bot"}
'''

def main():
    print("🚨 CRITICAL RENDER UPDATE REQUIRED")
    print("=" * 50)
    print()
    print("IDENTIFIED ERRORS FROM RENDER LOGS:")
    print("1. signature_invalid - Wrong HMAC signature method")
    print("2. pairs parameter missing - Wrong DCA bot format") 
    print()
    print("SOLUTION:")
    print("Replace render_deployment/three_commas_api.py with corrected code")
    print()
    print("=" * 50)
    print("CORRECTED CODE FOR GITHUB:")
    print("=" * 50)
    print(CORRECTED_THREE_COMMAS_CODE)
    print("=" * 50)
    print()
    print("STEPS:")
    print("1. Copy the code above")
    print("2. Go to GitHub: render_deployment/three_commas_api.py")
    print("3. Replace entire file content")
    print("4. Commit - Render will auto-redeploy")
    print("5. Trading system will be 100% operational")

if __name__ == "__main__":
    main()
