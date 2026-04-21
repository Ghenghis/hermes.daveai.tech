# Azure Voice Edition: End-to-End Implementation Guide

> Complete reverse engineering reference for recreating the Azure TTS integration from source.

## System Overview

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 700" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <text x="460" y="25" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a2e">Azure Voice Edition: Complete System Map</text>

  <!-- VS Code Extension Host -->
  <rect x="20" y="45" width="880" height="130" rx="10" fill="#e3f2fd" stroke="#1565c0" stroke-width="2"/>
  <text x="460" y="68" text-anchor="middle" font-size="14" font-weight="bold" fill="#0d47a1">VS Code Extension Host (Node.js)</text>

  <rect x="40" y="80" width="250" height="35" rx="4" fill="white" stroke="#90caf9"/>
  <text x="165" y="102" text-anchor="middle" fill="#1565c0" font-weight="600">KiloProvider.ts:536</text>
  <text x="165" y="112" text-anchor="middle" font-size="9" fill="#64b5f6">Message handler switch (141 cases)</text>

  <rect x="310" y="80" width="270" height="35" rx="4" fill="white" stroke="#90caf9"/>
  <text x="445" y="102" text-anchor="middle" fill="#1565c0" font-weight="600">sendSpeechSettings() :2199</text>
  <text x="445" y="112" text-anchor="middle" font-size="9" fill="#64b5f6">Reads 24 VS Code config keys</text>

  <rect x="600" y="80" width="280" height="35" rx="4" fill="white" stroke="#90caf9"/>
  <text x="740" y="102" text-anchor="middle" fill="#1565c0" font-weight="600">validateAzureKey() :2205</text>
  <text x="740" y="112" text-anchor="middle" font-size="9" fill="#64b5f6">POST test SSML to Azure endpoint</text>

  <rect x="40" y="125" width="400" height="30" rx="4" fill="#bbdefb" stroke="#64b5f6"/>
  <text x="240" y="145" text-anchor="middle" fill="#0d47a1">package.json: 24 speech settings under kilo-code.new.speech.*</text>

  <rect x="460" y="125" width="420" height="30" rx="4" fill="#bbdefb" stroke="#64b5f6"/>
  <text x="670" y="145" text-anchor="middle" fill="#0d47a1">messages.ts: WebviewMessage + ExtensionMessage unions</text>

  <!-- Webview -->
  <rect x="20" y="195" width="880" height="490" rx="10" fill="#e8f5e9" stroke="#43a047" stroke-width="2"/>
  <text x="460" y="218" text-anchor="middle" font-size="14" font-weight="bold" fill="#2e7d32">Webview (Solid.js - Browser Context)</text>

  <!-- Data Layer -->
  <rect x="40" y="230" width="420" height="90" rx="6" fill="white" stroke="#a5d6a7" stroke-width="1.5"/>
  <text x="250" y="250" text-anchor="middle" font-weight="700" fill="#2e7d32">Data Layer</text>
  <rect x="50" y="260" width="195" height="25" rx="3" fill="#c8e6c9"/>
  <text x="147" y="277" text-anchor="middle" font-size="11" fill="#1b5e20">azure-voices.ts (257 lines)</text>
  <rect x="255" y="260" width="195" height="25" rx="3" fill="#c8e6c9"/>
  <text x="352" y="277" text-anchor="middle" font-size="11" fill="#1b5e20">voice.ts types (90 lines)</text>
  <text x="147" y="305" text-anchor="middle" font-size="10" fill="#558b2f">125 voices + descriptions + styles</text>
  <text x="352" y="305" text-anchor="middle" font-size="10" fill="#558b2f">SpeechSettings + VoicePreset</text>

  <!-- TTS Engine -->
  <rect x="480" y="230" width="400" height="90" rx="6" fill="white" stroke="#a5d6a7" stroke-width="1.5"/>
  <text x="680" y="250" text-anchor="middle" font-weight="700" fill="#2e7d32">TTS Engine</text>
  <rect x="490" y="260" width="185" height="25" rx="3" fill="#c8e6c9"/>
  <text x="582" y="277" text-anchor="middle" font-size="11" fill="#1b5e20">tts-azure.ts (108 lines)</text>
  <rect x="685" y="260" width="185" height="25" rx="3" fill="#c8e6c9"/>
  <text x="777" y="277" text-anchor="middle" font-size="11" fill="#1b5e20">speech-playback.ts (119 lines)</text>
  <text x="582" y="305" text-anchor="middle" font-size="10" fill="#558b2f">SSML builder + Azure REST</text>
  <text x="777" y="305" text-anchor="middle" font-size="10" fill="#558b2f">Web Audio + LRU cache</text>

  <!-- Text Filter -->
  <rect x="40" y="335" width="420" height="50" rx="6" fill="#fff9c4" stroke="#f9a825" stroke-width="2"/>
  <text x="250" y="355" text-anchor="middle" font-weight="700" fill="#f57f17">speech-text-filter.ts (196 lines)</text>
  <text x="250" y="372" text-anchor="middle" font-size="10" fill="#f9a825">filterTextForSpeech() + detectSentiment() -- PORTED FROM SOURCE</text>

  <!-- UI Components -->
  <rect x="40" y="400" width="840" height="135" rx="6" fill="white" stroke="#a5d6a7" stroke-width="1.5"/>
  <text x="460" y="420" text-anchor="middle" font-weight="700" fill="#2e7d32">UI Components</text>

  <rect x="55" y="430" width="260" height="40" rx="4" fill="#e8f5e9" stroke="#66bb6a"/>
  <text x="185" y="448" text-anchor="middle" font-weight="600" fill="#2e7d32">SpeechTab.tsx (617 lines)</text>
  <text x="185" y="463" text-anchor="middle" font-size="10" fill="#43a047">3 sections: Connection + Browser + Tuning</text>

  <rect x="325" y="430" width="260" height="40" rx="4" fill="#e8f5e9" stroke="#66bb6a"/>
  <text x="455" y="448" text-anchor="middle" font-weight="600" fill="#2e7d32">Settings.tsx (modified)</text>
  <text x="455" y="463" text-anchor="middle" font-size="10" fill="#43a047">Speech tab trigger + content added</text>

  <rect x="595" y="430" width="270" height="40" rx="4" fill="#e8f5e9" stroke="#66bb6a"/>
  <text x="730" y="448" text-anchor="middle" font-weight="600" fill="#2e7d32">App.tsx (modified)</text>
  <text x="730" y="463" text-anchor="middle" font-size="10" fill="#43a047">Auto-speak + interrupt-on-type</text>

  <rect x="55" y="480" width="160" height="40" rx="4" fill="#f3e5f5" stroke="#ce93d8"/>
  <text x="135" y="498" text-anchor="middle" font-weight="600" fill="#7b1fa2">SettingsRow</text>
  <text x="135" y="513" text-anchor="middle" font-size="10" fill="#9c27b0">Layout wrapper</text>

  <rect x="225" y="480" width="120" height="40" rx="4" fill="#f3e5f5" stroke="#ce93d8"/>
  <text x="285" y="498" text-anchor="middle" font-weight="600" fill="#7b1fa2">Card</text>
  <text x="285" y="513" text-anchor="middle" font-size="10" fill="#9c27b0">kilo-ui</text>

  <rect x="355" y="480" width="120" height="40" rx="4" fill="#f3e5f5" stroke="#ce93d8"/>
  <text x="415" y="498" text-anchor="middle" font-weight="600" fill="#7b1fa2">Switch</text>
  <text x="415" y="513" text-anchor="middle" font-size="10" fill="#9c27b0">kilo-ui</text>

  <rect x="485" y="480" width="120" height="40" rx="4" fill="#f3e5f5" stroke="#ce93d8"/>
  <text x="545" y="498" text-anchor="middle" font-weight="600" fill="#7b1fa2">Select</text>
  <text x="545" y="513" text-anchor="middle" font-size="10" fill="#9c27b0">kilo-ui</text>

  <rect x="615" y="480" width="120" height="40" rx="4" fill="#f3e5f5" stroke="#ce93d8"/>
  <text x="675" y="498" text-anchor="middle" font-weight="600" fill="#7b1fa2">Button</text>
  <text x="675" y="513" text-anchor="middle" font-size="10" fill="#9c27b0">kilo-ui</text>

  <rect x="745" y="480" width="120" height="40" rx="4" fill="#f3e5f5" stroke="#ce93d8"/>
  <text x="805" y="498" text-anchor="middle" font-weight="600" fill="#7b1fa2">TextField</text>
  <text x="805" y="513" text-anchor="middle" font-size="10" fill="#9c27b0">kilo-ui</text>

  <!-- Azure Cloud -->
  <rect x="280" y="555" width="360" height="60" rx="8" fill="#e0f7fa" stroke="#00838f" stroke-width="2"/>
  <text x="460" y="578" text-anchor="middle" font-weight="700" font-size="14" fill="#006064">Azure Cognitive Services</text>
  <text x="460" y="598" text-anchor="middle" font-size="11" fill="#00838f">https://{region}.tts.speech.microsoft.com/cognitiveservices/v1</text>

  <!-- External connection arrow -->
  <line x1="460" y1="615" x2="460" y2="640" stroke="#00838f" stroke-width="0" />

  <!-- Legend -->
  <rect x="40" y="640" width="840" height="40" rx="4" fill="#fafafa" stroke="#e0e0e0"/>
  <text x="60" y="660" font-size="11" fill="#616161">Source locations: G:\Github\kilocode (reference) | G:\Github\kilocode-Azure2 (our build) | All paths relative to packages/kilo-vscode/</text>
  <text x="60" y="675" font-size="11" fill="#616161">Line numbers reference kilocode-Azure2 after all patches applied</text>
</svg>
```

---

## Complete File Inventory

### Source Files (G:\Github\kilocode) -> Azure Edition (G:\Github\kilocode-Azure2)

| # | Source Path | Azure Edition Path | Action | Lines |
|---|-----------|-------------------|--------|------:|
| 1 | `webview-ui/src/data/azure-voices.ts` | `webview-ui/src/data/azure-voices.ts` | Port + extend | 257 |
| 2 | *(new)* | `webview-ui/src/types/voice.ts` | Create | 90 |
| 3 | `webview-ui/src/types/messages.ts` | `webview-ui/src/types/messages.ts` | Modify | +26 |
| 4 | `packages/app/src/utils/tts-azure.ts` | `webview-ui/src/utils/tts-azure.ts` | Port + extend | 108 |
| 5 | `webview-ui/src/utils/speech-playback.ts` | `webview-ui/src/utils/speech-playback.ts` | Port (simplified) | 119 |
| 6 | `webview-ui/src/utils/speech-text-filter.ts` | `webview-ui/src/utils/speech-text-filter.ts` | Port (direct) | 196 |
| 7 | `webview-ui/src/components/settings/SpeechTab.tsx` | `webview-ui/src/components/settings/SpeechTab.tsx` | Rewrite | 617 |
| 8 | `webview-ui/src/components/settings/Settings.tsx` | `webview-ui/src/components/settings/Settings.tsx` | Modify | +11 |
| 9 | `src/KiloProvider.ts` | `src/KiloProvider.ts` | Modify | +25 |
| 10 | `package.json` | `package.json` | Modify | +147 |
| 11 | `webview-ui/src/App.tsx` | `webview-ui/src/App.tsx` | Modify | +99 |

---

## Azure TTS API Reference

### Endpoint
```
POST https://{region}.tts.speech.microsoft.com/cognitiveservices/v1
```

### Headers
```http
Ocp-Apim-Subscription-Key: {apiKey}
Content-Type: application/ssml+xml
X-Microsoft-OutputFormat: {audioFormat}
User-Agent: KiloCode-Azure
```

### Audio Formats
| Format ID | Quality | Sample Rate | Bitrate |
|-----------|---------|-------------|---------|
| `audio-16khz-32kbitrate-mono-mp3` | Low | 16 kHz | 32 kbps |
| `audio-24khz-48kbitrate-mono-mp3` | Standard | 24 kHz | 48 kbps |
| `audio-48khz-96kbitrate-mono-mp3` | High | 48 kHz | 96 kbps |

### SSML Template (Full Features)
```xml
<speak version="1.0"
       xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="https://www.w3.org/2001/mstts"
       xml:lang="en-US">
  <voice name="{voiceId}">
    <mstts:express-as style="{style}" styledegree="{styleDegree}">
      <prosody pitch="{pitch}%" rate="{rate}" volume="{volume}">
        <emphasis level="{emphasis}">
          <sub alias="{pronounceAs}">{word}</sub>
          {text}
        </emphasis>
      </prosody>
    </mstts:express-as>
  </voice>
</speak>
```

### Validation Endpoint (Same URL, Minimal SSML)
```xml
<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
  <voice name='en-GB-MaisieNeural'>test</voice>
</speak>
```

### Response
- **200 OK**: Binary audio blob (MP3)
- **400**: Invalid SSML
- **401**: Invalid API key
- **403**: Insufficient permissions
- **429**: Rate limited

---

## VS Code Configuration Schema

All settings under `kilo-code.new.speech.*`:

```
speech.enabled              boolean   false                              Enable voice output
speech.autoSpeak            boolean   false                              Auto-speak assistant replies
speech.volume               number    80       [0-100]                   Master volume
speech.interactionMode      string    "assist" [assist|conversation|minimal]
speech.interruptOnType      boolean   true                              Stop speech on keypress
speech.debugMode            boolean   false                              Verbose console logging
speech.sentimentIntensity   number    70       [0-100]                   Emotional modulation strength
speech.multiVoiceMode       boolean   false                              Distinct voice per agent
speech.azure.apiKey         string    ""                                 Azure Speech API key
speech.azure.region         string    "westus"                           Azure resource region
speech.azure.voiceId        string    "en-GB-MaisieNeural"              Selected voice ID
speech.tuning.pitch         number    0        [-50, 50]                 Pitch adjustment %
speech.tuning.rate          number    1.0      [0.5, 2.0]               Speech rate multiplier
speech.tuning.volume        number|null null                             Per-voice volume override
speech.tuning.style         string    "default"                          Speaking style
speech.tuning.styleDegree   number    1.0      [0.5, 2.0]               Style intensity
speech.tuning.sentencePause number    250      [0, 2000]                 Between-sentence pause (ms)
speech.tuning.paragraphBreak number   500      [0, 5000]                 Between-paragraph pause (ms)
speech.tuning.emphasis      string    "moderate" [none|reduced|moderate|strong]
speech.tuning.pronunciations array    []                                  Custom word substitutions
speech.tuning.audioFormat   string    "audio-24khz-48kbitrate-mono-mp3"  Output quality
speech.favorites.starredVoices array  ["en-GB-MaisieNeural"]             Starred voices
speech.favorites.order      array     ["en-GB-MaisieNeural"]             Display order
speech.presets              array     []                                  Saved voice+tuning configs
```

---

## Message Protocol

### Webview -> Extension Host

| Message Type | Payload | Handler |
|-------------|---------|---------|
| `requestSpeechSettings` | *(none)* | `sendSpeechSettings()` |
| `validateAzureKey` | `{ apiKey, region }` | `validateAzureKey()` |
| `updateSetting` | `{ key: "speech.*", value }` | `handleUpdateSetting()` |

### Extension Host -> Webview

| Message Type | Payload | Trigger |
|-------------|---------|---------|
| `speechSettingsLoaded` | `{ settings: SpeechSettings }` | On request / on reset |
| `azureKeyValidationResult` | `{ valid, error? }` | After key test |

---

## Voice Catalog Structure

### 125 Voices Across 14 English Locales

| Locale | Count | Example Voices |
|--------|:-----:|---------------|
| en-GB | 15 | Maisie (default), Sonia, Ryan, Libby, Abbi, Alfie... |
| en-US | 36 | Ava, Andrew, Emma, Brian, Jenny, Aria, Davis... |
| en-AU | 14 | Natasha, William, Annette, Carly, Darren... |
| en-IN | 8 | Neerja, Prabhat, Aarav, Aashi... |
| en-CA | 2 | Clara, Liam |
| en-IE | 2 | Connor, Emily |
| en-NZ | 2 | Mitchell, Molly |
| en-SG | 2 | Luna, Wayne |
| en-ZA | 2 | Leah, Luke |
| en-HK | 2 | Sam, Yan |
| en-KE | 2 | Asilia, Chilemba |
| en-NG | 2 | Abeo, Ezinne |
| en-PH | 2 | James, Rosa |
| en-TZ | 2 | Elimu, Imani |

### Voices with Style Support

| Voice | Styles |
|-------|--------|
| en-US-AriaNeural | chat, cheerful, customerservice, empathetic, excited, friendly, hopeful, narration-professional, newscast-casual, newscast-formal, sad, shouting, terrified, unfriendly, whispering, angry |
| en-US-DavisNeural | chat, cheerful, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering, angry |
| en-US-JennyNeural | chat, cheerful, customerservice, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering, angry |
| en-US-GuyNeural | newscast, angry, cheerful, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering |
| en-US-JasonNeural | chat, cheerful, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering, angry |
| en-US-NancyNeural | chat, cheerful, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering, angry |
| en-US-SaraNeural | chat, cheerful, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering, angry |
| en-US-TonyNeural | chat, cheerful, excited, friendly, hopeful, sad, shouting, terrified, unfriendly, whispering, angry |
| en-GB-SoniaNeural | cheerful, sad |
| en-GB-RyanNeural | chat, cheerful |
