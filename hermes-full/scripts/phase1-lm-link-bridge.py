#!/usr/bin/env python3
# Phase 1, Task 1.2: LM Link Bridge Setup
# This script configures the LM Link bridge for multi-GPU connectivity

import requests
import json
from typing import Dict, List
import time

class LMLinkBridge:
    def __init__(self):
        # Configuration - update with actual Tailscale IPs
        self.gpus = {
            'rtx3090': {
                'url': 'http://<TAILSCALE_IP_RTX>:11434',  # Update this
                'type': 'primary',
                'memory': '24GB',
                'models': []
            },
            'amd7800': {
                'url': 'http://<TAILSCALE_IP_AMD>:11434',  # Update this
                'type': 'secondary',
                'memory': '16GB',
                'models': []
            }
        }
    
    def test_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all GPUs"""
        print("Testing GPU connectivity...")
        results = {}
        
        for gpu_name, gpu_info in self.gpus.items():
            try:
                print(f"  Testing {gpu_name} at {gpu_info['url']}...")
                response = requests.get(f"{gpu_info['url']}/api/tags", timeout=5)
                if response.status_code == 200:
                    results[gpu_name] = True
                    print(f"    ✅ Connected")
                else:
                    results[gpu_name] = False
                    print(f"    ❌ Failed (status: {response.status_code})")
            except Exception as e:
                results[gpu_name] = False
                print(f"    ❌ Failed ({str(e)})")
        
        return results
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Query all GPUs for available models"""
        print("Querying available models...")
        models = {}
        
        for gpu_name, gpu_info in self.gpus.items():
            try:
                response = requests.get(f"{gpu_info['url']}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models[gpu_name] = [m['name'] for m in data.get('models', [])]
                    print(f"  {gpu_name}: {len(models[gpu_name])} models")
                    for model in models[gpu_name][:5]:  # Show first 5
                        print(f"    - {model}")
                    if len(models[gpu_name]) > 5:
                        print(f"    ... and {len(models[gpu_name]) - 5} more")
                else:
                    models[gpu_name] = []
                    print(f"  {gpu_name}: Failed to query")
            except Exception as e:
                models[gpu_name] = []
                print(f"  {gpu_name}: Error ({str(e)})")
        
        return models
    
    def route_request(self, model: str, prompt: str) -> str:
        """Route request to appropriate GPU (simplified)"""
        # Check if model is available on primary GPU
        if model in self.gpus['rtx3090']['models']:
            return self._execute_on_gpu('rtx3090', model, prompt)
        elif model in self.gpus['amd7800']['models']:
            return self._execute_on_gpu('amd7800', model, prompt)
        else:
            return f"Model {model} not found on any GPU"
    
    def _execute_on_gpu(self, gpu_name: str, model: str, prompt: str) -> str:
        """Execute request on specific GPU"""
        url = self.gpus[gpu_name]['url']
        try:
            response = requests.post(
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

def main():
    print("=== Phase 1.2: LM Link Bridge Setup ===")
    print()
    
    bridge = LMLinkBridge()
    
    # Test connectivity
    connectivity = bridge.test_connectivity()
    print()
    
    # Get available models
    models = bridge.get_available_models()
    print()
    
    # Summary
    print("=== Summary ===")
    connected_count = sum(1 for v in connectivity.values() if v)
    print(f"GPPs Connected: {connected_count}/{len(connectivity)}")
    
    if connected_count == len(connectivity):
        print("✅ All GPUs connected successfully")
        print()
        print("Next steps:")
        print("1. Update Tailscale IPs in script")
        print("2. Load models on each GPU (Task 1.3)")
        return 0
    else:
        print("❌ Some GPUs not connected")
        print("Please check:")
        print("- Tailscale is running on both PCs")
        print("- LM Studio is running on both PCs")
        print("- Firewall allows port 11434")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
