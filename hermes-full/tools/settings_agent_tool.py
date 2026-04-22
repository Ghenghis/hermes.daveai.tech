"""
SettingsAgent Tool - Hermes Agent accessible settings completion tool

This tool allows agents to:
- Query current settings state
- Discover available API keys  
- Auto-fill settings from discovered keys
- Update settings with recommended values
- Get suggestions for optimal settings
"""

import json
import os
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class SettingsResult:
    success: bool
    data: Any = None
    error: Optional[str] = None


class SettingsAgentTool:
    """Tool for agent-accessible settings completion"""
    
    name = "settings_agent"
    description = """Manage KiloCode settings - query, auto-fill, and update settings.
Use this tool when you need to:
- Check what API keys are configured
- Auto-fill missing settings from discovered API keys
- Get suggestions for optimal settings
- Complete settings configuration for users"""

    def __init__(self):
        self.api_keys_path = os.path.expanduser("~/Downloads/api")

    def discover_api_keys(self) -> SettingsResult:
        """Discover API keys from common locations"""
        try:
            keys = {
                "azure": {"apiKey": None, "region": None},
                "siliconflow": [],
                "minimax": None,
                "github": None,
                "huggingface": None,
                "google": None,
                "openai": None,
                "elevenlabs": None,
                "polly": {"accessKeyId": None, "region": None},
            }
            
            if not os.path.exists(self.api_keys_path):
                return SettingsResult(success=True, data=keys)
            
            # Scan .env files
            for filename in os.listdir(self.api_keys_path):
                if not filename.startswith(".") and not filename.endswith(".txt"):
                    continue
                    
                filepath = os.path.join(self.api_keys_path, filename)
                if os.path.isfile(filepath):
                    with open(filepath, "r") as f:
                        content = f.read()
                    
                    # Extract keys
                    if "AZURE_SPEECH_KEY" in content or "VITE_AZURE_SPEECH_KEY" in content:
                        for line in content.split("\n"):
                            if line.startswith("AZURE_SPEECH_KEY="):
                                keys["azure"]["apiKey"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("AZURE_SPEECH_REGION="):
                                keys["azure"]["region"] = line.split("=", 1)[1].strip().strip('"').strip("'") or "westus"
                            elif line.startswith("VITE_AZURE_SPEECH_KEY="):
                                keys["azure"]["apiKey"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    
                    if "SILICONFLOW_API_KEY" in content:
                        for line in content.split("\n"):
                            if line.startswith("SILICONFLOW_API_KEY="):
                                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if key and key not in keys["siliconflow"]:
                                    keys["siliconflow"].append(key)
                    
                    if "MINIMAX_API_KEY" in content:
                        for line in content.split("\n"):
                            if line.startswith("MINIMAX_API_KEY="):
                                keys["minimax"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    
                    if "GITHUB_TOKEN=" in content or "ghp_" in content:
                        for line in content.split("\n"):
                            if line.startswith("GITHUB_TOKEN="):
                                keys["github"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.strip().startswith("ghp_"):
                                keys["github"] = line.strip().strip('"').strip("'")
                    
                    if "HF_TOKEN=" in content or "HUGGINGFACE_TOKEN" in content:
                        for line in content.split("\n"):
                            if line.startswith("HF_TOKEN=") or line.startswith("HUGGINGFACE_TOKEN="):
                                keys["huggingface"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            
            # Summary without exposing actual keys
            summary = {
                "available": {
                    "azure": keys["azure"]["apiKey"] is not None,
                    "siliconflow": len(keys["siliconflow"]) > 0,
                    "minimax": keys["minimax"] is not None,
                    "github": keys["github"] is not None,
                    "huggingface": keys["huggingface"] is not None,
                    "google": keys["google"] is not None,
                    "openai": keys["openai"] is not None,
                    "elevenlabs": keys["elevenlabs"] is not None,
                    "polly": keys["polly"]["accessKeyId"] is not None,
                },
                "count": sum([
                    1 if keys["azure"]["apiKey"] else 0,
                    len(keys["siliconflow"]) if keys["siliconflow"] else 0,
                    1 if keys["minimax"] else 0,
                    1 if keys["github"] else 0,
                    1 if keys["huggingface"] else 0,
                    1 if keys["google"] else 0,
                    1 if keys["openai"] else 0,
                    1 if keys["elevenlabs"] else 0,
                    1 if keys["polly"]["accessKeyId"] else 0,
                ])
            }
            
            return SettingsResult(success=True, data=summary)
            
        except Exception as e:
            return SettingsResult(success=False, error=str(e))

    def get_settings_suggestions(self) -> SettingsResult:
        """Get suggestions for optimal settings based on available keys"""
        try:
            discovery = self.discover_api_keys()
            if not discovery.success:
                return discovery
            
            available = discovery.data["available"]
            suggestions = []
            
            if available.get("azure"):
                suggestions.append({
                    "category": "Speech",
                    "setting": "speech.azure.apiKey",
                    "action": "auto_fill",
                    "reason": "Azure API key found - recommended for high-quality neural voices",
                    "suggested_provider": "azure",
                })
            
            if available.get("huggingface"):
                suggestions.append({
                    "category": "Training",
                    "setting": "training.huggingface",
                    "action": "auto_fill", 
                    "reason": "HuggingFace token found - enables model training and deployment",
                })
            
            if available.get("siliconflow"):
                suggestions.append({
                    "category": "Providers",
                    "setting": "provider.siliconflow",
                    "action": "auto_fill",
                    "reason": "SiliconFlow API key(s) found - recommended for cost-effective inference",
                })
            
            if available.get("minimax"):
                suggestions.append({
                    "category": "Providers",
                    "setting": "provider.minimax",
                    "action": "auto_fill",
                    "reason": "MiniMax API key found - recommended for video generation",
                })
            
            if available.get("github"):
                suggestions.append({
                    "category": "Git Operations",
                    "setting": "provider.github",
                    "action": "auto_fill",
                    "reason": "GitHub token found - enables git operations and GitHub integration",
                })
            
            return SettingsResult(success=True, data=suggestions)
            
        except Exception as e:
            return SettingsResult(success=False, error=str(e))

    def auto_fill_setting(self, setting: str) -> SettingsResult:
        """Auto-fill a specific setting from discovered API keys
        
        Args:
            setting: One of: speech.azure, speech.google, speech.openai, speech.elevenlabs,
                    speech.polly, provider.github, training.huggingface
        """
        try:
            # Discover keys
            keys = {"azure": {"apiKey": None}, "google": None, "openai": None, 
                   "elevenlabs": None, "polly": {"accessKeyId": None}, 
                   "github": None, "huggingface": None, "siliconflow": []}
            
            if os.path.exists(self.api_keys_path):
                for filename in os.listdir(self.api_keys_path):
                    if not filename.startswith("."):
                        continue
                    filepath = os.path.join(self.api_keys_path, filename)
                    if os.path.isfile(filepath):
                        with open(filepath, "r") as f:
                            content = f.read()
                        
                        for line in content.split("\n"):
                            if line.startswith("AZURE_SPEECH_KEY=") and not keys["azure"]["apiKey"]:
                                keys["azure"]["apiKey"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("VITE_AZURE_SPEECH_KEY=") and not keys["azure"]["apiKey"]:
                                keys["azure"]["apiKey"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("GOOGLE_API_KEY=") and not keys["google"]:
                                keys["google"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("OPENAI_API_KEY=") and not keys["openai"]:
                                keys["openai"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("ELEVENLABS_API_KEY=") and not keys["elevenlabs"]:
                                keys["elevenlabs"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("GITHUB_TOKEN=") and not keys["github"]:
                                keys["github"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("HF_TOKEN=") and not keys["huggingface"]:
                                keys["huggingface"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("AWS_ACCESS_KEY_ID=") and not keys["polly"]["accessKeyId"]:
                                keys["polly"]["accessKeyId"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("SILICONFLOW_API_KEY="):
                                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if key:
                                    keys["siliconflow"].append(key)
            
            # Check requested setting
            setting_map = {
                "speech.azure": ("azure", keys["azure"]["apiKey"]),
                "speech.google": ("google", keys["google"]),
                "speech.openai": ("openai", keys["openai"]),
                "speech.elevenlabs": ("elevenlabs", keys["elevenlabs"]),
                "speech.polly": ("aws", keys["polly"]["accessKeyId"]),
                "provider.github": ("github", keys["github"]),
                "training.huggingface": ("huggingface", keys["huggingface"]),
            }
            
            if setting not in setting_map:
                return SettingsResult(success=False, error=f"Unknown setting: {setting}")
            
            provider, key_value = setting_map[setting]
            
            if not key_value:
                return SettingsResult(success=False, error=f"No {provider} API key found")
            
            return SettingsResult(
                success=True,
                data={
                    "setting": setting,
                    "provider": provider,
                    "status": "ready_to_fill",
                    "message": f"{provider.title()} API key discovered - ready to fill. Agent should use VS Code extension API to complete the fill.",
                }
            )
            
        except Exception as e:
            return SettingsResult(success=False, error=str(e))

    def execute(self, action: str, **kwargs) -> str:
        """Execute a settings action
        
        Args:
            action: One of: discover_api_keys, get_suggestions, auto_fill_setting
        """
        if action == "discover_api_keys":
            result = self.discover_api_keys()
        elif action == "get_suggestions":
            result = self.get_settings_suggestions()
        elif action == "auto_fill_setting":
            setting = kwargs.get("setting")
            if not setting:
                return json.dumps({"success": False, "error": "setting is required"})
            result = self.auto_fill_setting(setting)
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})
        
        if result.success:
            return json.dumps({"success": True, "data": result.data})
        else:
            return json.dumps({"success": False, "error": result.error})


# Global instance
settings_agent_tool = SettingsAgentTool()


def handle_function_call(name: str, args: dict, task_id: Optional[str] = None) -> str:
    """Handle function calls from the agent"""
    if name != "settings_agent":
        return json.dumps({"success": False, "error": f"Unknown tool: {name}"})
    
    action = args.get("action")
    if not action:
        return json.dumps({"success": False, "error": "action is required"})
    
    return settings_agent_tool.execute(action, **args)


# Tool schema for registry
SETTINGS_AGENT_SCHEMA = {
    "name": "settings_agent",
    "description": """Manage KiloCode settings - query, auto-fill, and update settings.

Use this tool when you need to:
- Check what API keys are configured or discoverable
- Auto-fill missing settings from discovered API keys  
- Get suggestions for optimal settings based on available keys
- Complete settings configuration for users seamlessly

This tool helps agents assist users with settings configuration by discovering
API keys from common locations and providing intelligent suggestions.""",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to perform",
                "enum": ["discover_api_keys", "get_suggestions", "auto_fill_setting"]
            },
            "setting": {
                "type": "string",
                "description": "The setting to auto-fill (required for auto_fill_setting action)",
                "enum": [
                    "speech.azure", "speech.google", "speech.openai", 
                    "speech.elevenlabs", "speech.polly",
                    "provider.siliconflow", "provider.minimax", "provider.github", 
                    "training.huggingface"
                ]
            }
        },
        "required": ["action"]
    }
}


# Register the tool
from tools.registry import registry

registry.register(
    name="settings_agent",
    toolset="settings",
    schema=SETTINGS_AGENT_SCHEMA,
    handler=lambda args, **kw: handle_function_call("settings_agent", args, kw.get("task_id") or None),
    check_fn=lambda: True,  # Always available
    description="Manage and auto-fill KiloCode settings",
    emoji="⚙️",
)