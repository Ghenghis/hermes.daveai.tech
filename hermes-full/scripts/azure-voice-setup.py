#!/usr/bin/env python3
# Azure Speech Services Setup Script
# Configures Azure voice integration for Hermes chat interface

import os
import json
from typing import Dict

# Azure Speech Configuration
AZURE_CONFIG = {
    'speech_key': 'YOUR_AZURE_SPEECH_KEY',  # Get from https://portal.azure.com
    'speech_region': 'eastus'
}

# Agent Voice Configurations (3 Females with diverse accents, 2 Males en-US)
AGENT_VOICES = {
    'hermes1': {
        'voice': 'en-GB-MaisieNeural',
        'style': 'customerservice',
        'rate': '1.0',
        'pitch': 'medium',
        'description': 'Planning Strategist (FEMALE en-GB) - Natural, warm British accent'
    },
    'hermes2': {
        'voice': 'en-AU-CarlyNeural',
        'style': 'cheerful',
        'rate': '1.1',
        'pitch': '+10%',
        'description': 'Creative Brainstormer (FEMALE en-AU) - Casual, relaxed Australian voice'
    },
    'hermes3': {
        'voice': 'en-KE-AsiliaNeural',
        'style': 'calm',
        'rate': '0.95',
        'pitch': 'medium',
        'description': 'System Architect (FEMALE en-KE) - Warm, expressive Kenyan English voice'
    },
    'hermes4': {
        'voice': 'en-US-TonyNeural',
        'style': 'empathetic',
        'rate': '0.9',
        'pitch': 'medium',
        'description': 'Bug Triage Specialist (MALE en-US) - Analytical, methodical'
    },
    'hermes5': {
        'voice': 'en-US-ChristopherNeural',
        'style': 'serious',
        'rate': '0.85',
        'pitch': '-10%',
        'description': 'Root Cause Analyst (MALE en-US) - Investigative, deep'
    }
}

# User Voice Configuration
USER_VOICE_CONFIG = {
    'default_voice': 'en-US-JennyNeural',
    'default_language': 'en-US',
    'mode': 'text_only',
    'auto_detect_language': True
}

# Available Voices (Azure Neural Voices - Comprehensive Catalog)
AVAILABLE_VOICES = {
    'en-GB': [
        {'id': 'en-GB-MaisieNeural', 'gender': 'Female', 'description': 'Natural, warm British accent'},
        {'id': 'en-GB-SoniaNeural', 'gender': 'Female', 'description': 'Clear, professional British voice'},
        {'id': 'en-GB-LibbyNeural', 'gender': 'Female', 'description': 'Friendly, approachable British voice'},
        {'id': 'en-GB-AbbiNeural', 'gender': 'Female', 'description': 'Young, lively British voice'},
        {'id': 'en-GB-BellaNeural', 'gender': 'Female', 'description': 'Soft, gentle British voice'},
        {'id': 'en-GB-HollieNeural', 'gender': 'Female', 'description': 'Bright, energetic British voice'},
        {'id': 'en-GB-OliviaNeural', 'gender': 'Female', 'description': 'Elegant, refined British voice'},
        {'id': 'en-GB-MiaNeural', 'gender': 'Female', 'description': 'Cheerful, modern British voice'},
        {'id': 'en-GB-RyanNeural', 'gender': 'Male', 'description': 'Warm, conversational British male'},
        {'id': 'en-GB-AlfieNeural', 'gender': 'Male', 'description': 'Youthful British male voice'},
        {'id': 'en-GB-ElliotNeural', 'gender': 'Male', 'description': 'Calm, articulate British male'},
        {'id': 'en-GB-EthanNeural', 'gender': 'Male', 'description': 'Confident, clear British male'},
        {'id': 'en-GB-NoahNeural', 'gender': 'Male', 'description': 'Friendly, natural British male'},
        {'id': 'en-GB-OliverNeural', 'gender': 'Male', 'description': 'Warm, polished British male'},
        {'id': 'en-GB-ThomasNeural', 'gender': 'Male', 'description': 'Mature, authoritative British male'}
    ],
    'en-US': [
        {'id': 'en-US-AvaNeural', 'gender': 'Female', 'description': 'Natural, expressive American voice'},
        {'id': 'en-US-AndrewNeural', 'gender': 'Male', 'description': 'Warm, natural American male'},
        {'id': 'en-US-EmmaNeural', 'gender': 'Female', 'description': 'Clear, friendly American voice'},
        {'id': 'en-US-BrianNeural', 'gender': 'Male', 'description': 'Deep, confident American male'},
        {'id': 'en-US-JennyNeural', 'gender': 'Female', 'description': 'Versatile, conversational American voice'},
        {'id': 'en-US-GuyNeural', 'gender': 'Male', 'description': 'Casual, newscast-style American male'},
        {'id': 'en-US-AriaNeural', 'gender': 'Female', 'description': 'Expressive, multi-style American voice'},
        {'id': 'en-US-DavisNeural', 'gender': 'Male', 'description': 'Rich, versatile American male'},
        {'id': 'en-US-AmberNeural', 'gender': 'Female', 'description': 'Warm, soothing American voice'},
        {'id': 'en-US-AnaNeural', 'gender': 'Female', 'description': 'Young, child-like American voice'},
        {'id': 'en-US-AshleyNeural', 'gender': 'Female', 'description': 'Bright, youthful American voice'},
        {'id': 'en-US-BrandonNeural', 'gender': 'Male', 'description': 'Strong, clear American male'},
        {'id': 'en-US-ChristopherNeural', 'gender': 'Male', 'description': 'Professional, steady American male'},
        {'id': 'en-US-CoraNeural', 'gender': 'Female', 'description': 'Calm, composed American voice'},
        {'id': 'en-US-ElizabethNeural', 'gender': 'Female', 'description': 'Elegant, refined American voice'},
        {'id': 'en-US-EricNeural', 'gender': 'Male', 'description': 'Friendly, approachable American male'},
        {'id': 'en-US-JacobNeural', 'gender': 'Male', 'description': 'Young, energetic American male'},
        {'id': 'en-US-JaneNeural', 'gender': 'Female', 'description': 'Mature, professional American voice'},
        {'id': 'en-US-JasonNeural', 'gender': 'Male', 'description': 'Confident, dynamic American male'},
        {'id': 'en-US-MichelleNeural', 'gender': 'Female', 'description': 'Warm, nurturing American voice'},
        {'id': 'en-US-MonicaNeural', 'gender': 'Female', 'description': 'Smooth, pleasant American voice'},
        {'id': 'en-US-NancyNeural', 'gender': 'Female', 'description': 'Articulate, polished American voice'},
        {'id': 'en-US-RogerNeural', 'gender': 'Male', 'description': 'Deep, broadcast-quality American male'},
        {'id': 'en-US-RyanNeural', 'gender': 'Male', 'description': 'Casual, relatable American male'},
        {'id': 'en-US-SaraNeural', 'gender': 'Female', 'description': 'Sweet, gentle American voice'},
        {'id': 'en-US-SteffanNeural', 'gender': 'Male', 'description': 'Calm, measured American male'},
        {'id': 'en-US-TonyNeural', 'gender': 'Male', 'description': 'Lively, engaging American male'},
        {'id': 'en-US-AlloyNeural', 'gender': 'Male', 'description': 'Balanced, neutral American voice'},
        {'id': 'en-US-EchoNeural', 'gender': 'Male', 'description': 'Smooth, resonant American male'},
        {'id': 'en-US-FableNeural', 'gender': 'Male', 'description': 'Storytelling, narrative American male'},
        {'id': 'en-US-NovaNeural', 'gender': 'Female', 'description': 'Modern, bright American voice'},
        {'id': 'en-US-OnyxNeural', 'gender': 'Male', 'description': 'Deep, authoritative American male'},
        {'id': 'en-US-ShimmerNeural', 'gender': 'Female', 'description': 'Light, sparkling American voice'},
        {'id': 'en-US-BlueNeural', 'gender': 'Female', 'description': 'Fresh, contemporary American voice'},
        {'id': 'en-US-KaiNeural', 'gender': 'Male', 'description': 'Modern, youthful American male'},
        {'id': 'en-US-LunaNeural', 'gender': 'Female', 'description': 'Soft, dreamy American voice'}
    ],
    'en-AU': [
        {'id': 'en-AU-NatashaNeural', 'gender': 'Female', 'description': 'Clear, professional Australian voice'},
        {'id': 'en-AU-WilliamNeural', 'gender': 'Male', 'description': 'Warm, friendly Australian male'},
        {'id': 'en-AU-AnnetteNeural', 'gender': 'Female', 'description': 'Bright, cheerful Australian voice'},
        {'id': 'en-AU-CarlyNeural', 'gender': 'Female', 'description': 'Casual, relaxed Australian voice'},
        {'id': 'en-AU-DarrenNeural', 'gender': 'Male', 'description': 'Strong, confident Australian male'},
        {'id': 'en-AU-DuncanNeural', 'gender': 'Male', 'description': 'Deep, mature Australian male'},
        {'id': 'en-AU-ElsieNeural', 'gender': 'Female', 'description': 'Gentle, soothing Australian voice'},
        {'id': 'en-AU-FreyaNeural', 'gender': 'Female', 'description': 'Youthful, vibrant Australian voice'},
        {'id': 'en-AU-JoanneNeural', 'gender': 'Female', 'description': 'Warm, motherly Australian voice'},
        {'id': 'en-AU-KenNeural', 'gender': 'Male', 'description': 'Easygoing, natural Australian male'},
        {'id': 'en-AU-KimNeural', 'gender': 'Female', 'description': 'Polished, professional Australian voice'},
        {'id': 'en-AU-NeilNeural', 'gender': 'Male', 'description': 'Calm, steady Australian male'},
        {'id': 'en-AU-TimNeural', 'gender': 'Male', 'description': 'Energetic, upbeat Australian male'},
        {'id': 'en-AU-TinaNeural', 'gender': 'Female', 'description': 'Friendly, approachable Australian voice'}
    ],
    'en-CA': [
        {'id': 'en-CA-ClaraNeural', 'gender': 'Female', 'description': 'Clear, pleasant Canadian voice'},
        {'id': 'en-CA-LiamNeural', 'gender': 'Male', 'description': 'Friendly, natural Canadian male'}
    ],
    'en-IE': [
        {'id': 'en-IE-ConnorNeural', 'gender': 'Male', 'description': 'Warm, melodic Irish male'},
        {'id': 'en-IE-EmilyNeural', 'gender': 'Female', 'description': 'Soft, charming Irish voice'}
    ],
    'en-IN': [
        {'id': 'en-IN-NeerjaNeural', 'gender': 'Female', 'description': 'Clear, professional Indian English voice'},
        {'id': 'en-IN-PrabhatNeural', 'gender': 'Male', 'description': 'Warm, articulate Indian English male'},
        {'id': 'en-IN-AaravNeural', 'gender': 'Male', 'description': 'Young, energetic Indian English male'},
        {'id': 'en-IN-AashiNeural', 'gender': 'Female', 'description': 'Bright, lively Indian English voice'},
        {'id': 'en-IN-AnanyaNeural', 'gender': 'Female', 'description': 'Gentle, pleasant Indian English voice'},
        {'id': 'en-IN-KavyaNeural', 'gender': 'Female', 'description': 'Smooth, melodic Indian English voice'},
        {'id': 'en-IN-KunalNeural', 'gender': 'Male', 'description': 'Confident, clear Indian English male'},
        {'id': 'en-IN-RehaanNeural', 'gender': 'Male', 'description': 'Calm, composed Indian English male'}
    ],
    'en-NZ': [
        {'id': 'en-NZ-MitchellNeural', 'gender': 'Male', 'description': 'Friendly, natural New Zealand male'},
        {'id': 'en-NZ-MollyNeural', 'gender': 'Female', 'description': 'Warm, inviting New Zealand voice'}
    ],
    'en-SG': [
        {'id': 'en-SG-LunaNeural', 'gender': 'Female', 'description': 'Clear, modern Singaporean voice'},
        {'id': 'en-SG-WayneNeural', 'gender': 'Male', 'description': 'Professional Singaporean English male'}
    ],
    'en-ZA': [
        {'id': 'en-ZA-LeahNeural', 'gender': 'Female', 'description': 'Warm, distinctive South African voice'},
        {'id': 'en-ZA-LukeNeural', 'gender': 'Male', 'description': 'Strong, clear South African male'}
    ],
    'en-HK': [
        {'id': 'en-HK-SamNeural', 'gender': 'Male', 'description': 'Professional Hong Kong English male'},
        {'id': 'en-HK-YanNeural', 'gender': 'Female', 'description': 'Clear, articulate Hong Kong English voice'}
    ],
    'en-KE': [
        {'id': 'en-KE-AsiliaNeural', 'gender': 'Female', 'description': 'Warm, expressive Kenyan English voice'},
        {'id': 'en-KE-ChilembaNeural', 'gender': 'Male', 'description': 'Rich, resonant Kenyan English male'}
    ],
    'en-NG': [
        {'id': 'en-NG-AbeoNeural', 'gender': 'Male', 'description': 'Strong, vibrant Nigerian English male'},
        {'id': 'en-NG-EzinneNeural', 'gender': 'Female', 'description': 'Bright, lively Nigerian English voice'}
    ],
    'en-PH': [
        {'id': 'en-PH-JamesNeural', 'gender': 'Male', 'description': 'Friendly, clear Philippine English male'},
        {'id': 'en-PH-RosaNeural', 'gender': 'Female', 'description': 'Warm, pleasant Philippine English voice'}
    ],
    'en-TZ': [
        {'id': 'en-TZ-ElimuNeural', 'gender': 'Male', 'description': 'Clear, composed Tanzanian English male'},
        {'id': 'en-TZ-ImaniNeural', 'gender': 'Female', 'description': 'Gentle, warm Tanzanian English voice'}
    ]
}

def create_config_files():
    """Create configuration files for Azure voice integration"""
    print("Creating configuration files...")
    
    # Create directory
    os.makedirs('/opt/hermes-gateway/config', exist_ok=True)
    
    # Save Azure config
    with open('/opt/hermes-gateway/config/azure_config.json', 'w') as f:
        json.dump(AZURE_CONFIG, f, indent=2)
    print("  ✅ Azure config saved")
    
    # Save agent voices
    with open('/opt/hermes-gateway/config/agent_voices.json', 'w') as f:
        json.dump(AGENT_VOICES, f, indent=2)
    print("  ✅ Agent voices saved")
    
    # Save user voice config
    with open('/opt/hermes-gateway/config/user_voice_config.json', 'w') as f:
        json.dump(USER_VOICE_CONFIG, f, indent=2)
    print("  ✅ User voice config saved")
    
    # Save available voices
    with open('/opt/hermes-gateway/config/available_voices.json', 'w') as f:
        json.dump(AVAILABLE_VOICES, f, indent=2)
    print("  ✅ Available voices saved")

def create_python_module():
    """Create Python module for Azure voice integration"""
    print("Creating Python module...")
    
    os.makedirs('/opt/hermes-gateway/app', exist_ok=True)
    
    # Create azure_speech.py
    azure_speech_code = '''import azure.cognitiveservices.speech as speechsdk
import json
from typing import Optional
import os

class AzureSpeechService:
    def __init__(self):
        config_path = '/opt/hermes-gateway/config/azure_config.json'
        with open(config_path) as f:
            config = json.load(f)
        
        self.speech_config = speechsdk.SpeechConfig(
            subscription=config['speech_key'],
            region=config['speech_region']
        )
    
    def speech_to_text(self, audio_data: bytes, language: str = "en-US") -> str:
        """Convert speech to text"""
        stream = speechsdk.audio.PushAudioInputStream()
        stream.write(audio_data)
        stream.close()
        
        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        speech_config = self.speech_config
        speech_config.speech_recognition_language = language
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        result = recognizer.recognize_once_async().get()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        else:
            return ""
    
    def text_to_speech(
        self,
        text: str,
        voice: str = "en-US-AriaNeural",
        style: str = "calm",
        rate: str = "medium",
        pitch: str = "medium"
    ) -> bytes:
        """Convert text to speech"""
        speech_config = self.speech_config
        speech_config.speech_synthesis_voice_name = voice
        
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice}">
                <mstts:express-as style="{style}" xmlns:mstts="https://www.w3.org/2001/mstts">
                    <prosody rate="{rate}" pitch="{pitch}">
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None
        )
        
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        else:
            return b""
'''
    
    with open('/opt/hermes-gateway/app/azure_speech.py', 'w') as f:
        f.write(azure_speech_code)
    print("  ✅ azure_speech.py created")
    
    # Create voice_config.py
    voice_config_code = '''import json
from typing import Dict

class VoiceConfigManager:
    def __init__(self):
        with open('/opt/hermes-gateway/config/agent_voices.json') as f:
            self.agent_config = json.load(f)
        
        with open('/opt/hermes-gateway/config/user_voice_config.json') as f:
            self.user_config = json.load(f)
        
        with open('/opt/hermes-gateway/config/available_voices.json') as f:
            self.available_voices = json.load(f)
    
    def get_agent_voice(self, agent_id: str) -> Dict:
        return self.agent_config.get(agent_id, self.agent_config['hermes1'])
    
    def set_agent_voice(self, agent_id: str, voice: str, style: str = None):
        if agent_id in self.agent_config:
            self.agent_config[agent_id]['voice'] = voice
            if style:
                self.agent_config[agent_id]['style'] = style
            # Save changes
            with open('/opt/hermes-gateway/config/agent_voices.json', 'w') as f:
                json.dump(self.agent_config, f, indent=2)
    
    def get_user_voice(self) -> Dict:
        return self.user_config
    
    def set_user_voice_mode(self, mode: str):
        valid_modes = ['text_only', 'voice_input', 'voice_output', 'full_voice']
        if mode in valid_modes:
            self.user_config['mode'] = mode
            with open('/opt/hermes-gateway/config/user_voice_config.json', 'w') as f:
                json.dump(self.user_config, f, indent=2)
    
    def list_available_voices(self) -> Dict:
        return self.available_voices
'''
    
    with open('/opt/hermes-gateway/app/voice_config.py', 'w') as f:
        f.write(voice_config_code)
    print("  ✅ voice_config.py created")

def create_voice_coordinator():
    """Create voice coordinator module"""
    print("Creating voice coordinator...")
    
    voice_coordinator_code = '''from .azure_speech import AzureSpeechService
from .voice_config import VoiceConfigManager
from typing import Optional

class VoiceCoordinator:
    def __init__(self):
        self.azure_speech = AzureSpeechService()
        self.voice_config = VoiceConfigManager()
    
    async def process_user_input(self, audio_data: bytes, mode: str) -> Optional[str]:
        if mode in ['voice_input', 'full_voice']:
            text = self.azure_speech.speech_to_text(audio_data)
            return text
        return None
    
    async def generate_agent_response(
        self,
        text: str,
        agent_id: str,
        mode: str
    ) -> Optional[bytes]:
        if mode in ['voice_output', 'full_voice']:
            voice_config = self.voice_config.get_agent_voice(agent_id)
            audio = self.azure_speech.text_to_speech(
                text=text,
                voice=voice_config['voice'],
                style=voice_config['style'],
                rate=voice_config['rate'],
                pitch=voice_config['pitch']
            )
            return audio
        return None
    
    async def switch_agent_voice(self, agent_id: str, new_voice: str):
        self.voice_config.set_agent_voice(agent_id, new_voice)
    
    async def switch_user_mode(self, mode: str):
        self.voice_config.set_user_voice_mode(mode)
'''
    
    with open('/opt/hermes-gateway/app/voice_coordinator.py', 'w') as f:
        f.write(voice_coordinator_code)
    print("  ✅ voice_coordinator.py created")

def update_requirements():
    """Update requirements.txt with Azure dependencies"""
    print("Updating requirements.txt...")
    
    requirements_path = '/opt/hermes-gateway/requirements.txt'
    
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            existing = f.read()
        
        if 'azure-cognitiveservices-speech' not in existing:
            with open(requirements_path, 'a') as f:
                f.write('azure-cognitiveservices-speech==1.34.0\\n')
            print("  ✅ Azure Speech SDK added to requirements.txt")
        else:
            print("  ℹ️  Azure Speech SDK already in requirements.txt")
    else:
        with open(requirements_path, 'w') as f:
            f.write('azure-cognitiveservices-speech==1.34.0\\n')
        print("  ✅ requirements.txt created with Azure Speech SDK")

def update_environment():
    """Update environment variables"""
    print("Updating environment variables...")
    
    env_path = '/opt/hermes-gateway/.env'
    
    env_vars = f'''
AZURE_SPEECH_KEY={AZURE_CONFIG['speech_key']}
AZURE_SPEECH_REGION={AZURE_CONFIG['speech_region']}
'''
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            existing = f.read()
        
        if 'AZURE_SPEECH_KEY' not in existing:
            with open(env_path, 'a') as f:
                f.write(env_vars)
            print("  ✅ Azure environment variables added")
        else:
            print("  ℹ️  Azure environment variables already present")
    else:
        with open(env_path, 'w') as f:
            f.write(env_vars)
        print("  ✅ .env created with Azure environment variables")

def display_summary():
    """Display configuration summary"""
    print("\\n" + "="*60)
    print("Azure Voice Integration - Configuration Summary")
    print("="*60)
    print()
    print("Agent Voice Assignments:")
    for agent_id, config in AGENT_VOICES.items():
        print(f"  {agent_id}:")
        print(f"    Voice: {config['voice']}")
        print(f"    Style: {config['style']}")
        print(f"    Description: {config['description']}")
        print()
    
    print("User Voice Modes:")
    print("  - text_only: No voice, text chat only")
    print("  - voice_input: User speaks, agent responds with text")
    print("  - voice_output: User types, agent responds with voice")
    print("  - full_voice: User speaks, agent responds with voice")
    print()
    print("Configuration Files Created:")
    print("  - /opt/hermes-gateway/config/azure_config.json")
    print("  - /opt/hermes-gateway/config/agent_voices.json")
    print("  - /opt/hermes-gateway/config/user_voice_config.json")
    print("  - /opt/hermes-gateway/config/available_voices.json")
    print()
    print("Python Modules Created:")
    print("  - /opt/hermes-gateway/app/azure_speech.py")
    print("  - /opt/hermes-gateway/app/voice_config.py")
    print("  - /opt/hermes-gateway/app/voice_coordinator.py")
    print()
    print("Next Steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Test Azure Speech Services connection")
    print("  3. Integrate voice coordinator into Agent Gateway")
    print("  4. Add voice controls UI to Open WebUI")
    print("  5. Test voice input/output with each agent")
    print()

def main():
    print("=== Azure Voice Integration Setup ===")
    print()
    
    create_config_files()
    print()
    create_python_module()
    print()
    create_voice_coordinator()
    print()
    update_requirements()
    print()
    update_environment()
    print()
    display_summary()
    
    print("✅ Azure Voice Integration setup complete!")

if __name__ == "__main__":
    main()
