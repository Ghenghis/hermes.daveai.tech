#!/usr/bin/env python3
# Phase 1, Task 1.4: Cloud API Configuration
# This script configures and tests cloud API endpoints

import requests
import json
from typing import Dict

# Configuration
MINIMAX_CONFIG = {
    'api_key': 'YOUR_MINIMAX_API_KEY',  # Get from https://platform.minimaxi.chat
    'base_url': 'https://api.minimaxi.chat/v1',
    'models': {
        'highspeed_27': 'minimax/minimax-m2.5',
        '25': 'minimax/minimax-m2.5',
        '20': 'minimax/minimax-m2.0'
    },
    'tps_limit': 100
}

SILICONFLOW_CONFIG = {
    'api_keys': [
        'YOUR_SILICONFLOW_API_KEY_1',  # Get from https://siliconflow.cn
        'YOUR_SILICONFLOW_API_KEY_2'
    ],
    'base_url': 'https://api.siliconflow.com/v1',
    'models': {
        'deepseek_v3': 'deepseek-ai/DeepSeek-V3',
        'qwen_72b': 'Qwen/Qwen2.5-72B-Instruct',
        'qwen_7b': 'Qwen/Qwen2.5-7B-Instruct'
    }
}

def test_minimax() -> bool:
    """Test MiniMax API"""
    print("Testing MiniMax API...")
    
    try:
        response = requests.post(
            f"{MINIMAX_CONFIG['base_url']}/chat/completions",
            headers={
                'Authorization': f"Bearer {MINIMAX_CONFIG['api_key']}",
                'Content-Type': 'application/json'
            },
            json={
                'model': MINIMAX_CONFIG['models']['highspeed_27'],
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 50
            },
            timeout=30
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:50]}...")
            print("  ✅ MiniMax API working")
            return True
        else:
            print(f"  Error: {response.text}")
            print("  ❌ MiniMax API failed")
            return False
            
    except Exception as e:
        print(f"  Exception: {str(e)}")
        print("  ❌ MiniMax API failed")
        return False

def test_siliconflow() -> bool:
    """Test SiliconFlow API"""
    print("Testing SiliconFlow API...")
    
    for i, api_key in enumerate(SILICONFLOW_CONFIG['api_keys'], 1):
        print(f"  Testing API key {i}...")
        
        try:
            response = requests.post(
                f"{SILICONFLOW_CONFIG['base_url']}/chat/completions",
                headers={
                    'Authorization': f"Bearer {api_key}",
                    'Content-Type': 'application/json'
                },
                json={
                    'model': SILICONFLOW_CONFIG['models']['deepseek_v3'],
                    'messages': [{'role': 'user', 'content': 'Hello'}],
                    'max_tokens': 50
                },
                timeout=30
            )
            
            print(f"    Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"    Response: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:50]}...")
                print(f"  ✅ SiliconFlow API key {i} working")
                return True
            else:
                print(f"    Error: {response.text}")
                
        except Exception as e:
            print(f"    Exception: {str(e)}")
    
    print("  ❌ SiliconFlow API failed")
    return False

def save_configs():
    """Save configurations to files"""
    print("Saving configurations...")
    
    # Save MiniMax config
    with open('/opt/hermes-gateway/minimax_config.json', 'w') as f:
        json.dump(MINIMAX_CONFIG, f, indent=2)
    print("  ✅ MiniMax config saved to /opt/hermes-gateway/minimax_config.json")
    
    # Save SiliconFlow config
    with open('/opt/hermes-gateway/siliconflow_config.json', 'w') as f:
        json.dump(SILICONFLOW_CONFIG, f, indent=2)
    print("  ✅ SiliconFlow config saved to /opt/hermes-gateway/siliconflow_config.json")

def main():
    print("=== Phase 1.4: Cloud API Configuration ===")
    print()
    
    # Test APIs
    minimax_ok = test_minimax()
    print()
    siliconflow_ok = test_siliconflow()
    print()
    
    # Save configurations
    save_configs()
    print()
    
    # Summary
    print("=== Summary ===")
    print(f"MiniMax API: {'✅ Working' if minimax_ok else '❌ Failed'}")
    print(f"SiliconFlow API: {'✅ Working' if siliconflow_ok else '❌ Failed'}")
    
    if minimax_ok and siliconflow_ok:
        print()
        print("✅ All cloud APIs configured successfully")
        print()
        print("Next steps:")
        print("1. Configure TPS budget in Agent Gateway")
        print("2. Set up model fallback chain")
        return 0
    else:
        print()
        print("❌ Some APIs failed")
        print("Please check:")
        print("- API keys are correct")
        print("- Network connectivity")
        print("- API quota limits")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
