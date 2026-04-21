# Message Types & Data Layer Audit

## Message Flow Architecture

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 480" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <text x="440" y="25" text-anchor="middle" font-size="16" font-weight="bold" fill="#1a1a2e">Message Flow: Extension Host <-> Webview</text>

  <!-- Webview Side -->
  <rect x="20" y="50" width="380" height="410" rx="8" fill="#e3f2fd" stroke="#1565c0" stroke-width="1.5"/>
  <text x="210" y="75" text-anchor="middle" font-size="14" font-weight="bold" fill="#0d47a1">Webview (SpeechTab + App.tsx)</text>

  <!-- Outgoing messages -->
  <text x="35" y="100" font-weight="600" fill="#1565c0">Outgoing (WebviewMessage)</text>

  <rect x="35" y="110" width="350" height="25" rx="3" fill="#bbdefb" stroke="#64b5f6"/>
  <text x="45" y="127" fill="#0d47a1">requestSpeechSettings</text>
  <text x="330" y="127" fill="#4caf50" font-weight="600">IMPLEMENTED</text>

  <rect x="35" y="140" width="350" height="25" rx="3" fill="#bbdefb" stroke="#64b5f6"/>
  <text x="45" y="157" fill="#0d47a1">validateAzureKey { apiKey, region }</text>
  <text x="330" y="157" fill="#4caf50" font-weight="600">IMPLEMENTED</text>

  <rect x="35" y="170" width="350" height="25" rx="3" fill="#bbdefb" stroke="#64b5f6"/>
  <text x="45" y="187" fill="#0d47a1">updateSetting { key: "speech.*", value }</text>
  <text x="330" y="187" fill="#4caf50" font-weight="600">IMPLEMENTED</text>

  <!-- Incoming messages -->
  <text x="35" y="220" font-weight="600" fill="#1565c0">Incoming (ExtensionMessage)</text>

  <rect x="35" y="230" width="350" height="25" rx="3" fill="#c8e6c9" stroke="#81c784"/>
  <text x="45" y="247" fill="#1b5e20">speechSettingsLoaded { settings }</text>
  <text x="330" y="247" fill="#4caf50" font-weight="600">IMPLEMENTED</text>

  <rect x="35" y="260" width="350" height="25" rx="3" fill="#c8e6c9" stroke="#81c784"/>
  <text x="45" y="277" fill="#1b5e20">azureKeyValidationResult { valid, error? }</text>
  <text x="330" y="277" fill="#4caf50" font-weight="600">IMPLEMENTED</text>

  <!-- Source-only messages (excluded) -->
  <text x="35" y="315" font-weight="600" fill="#9e9e9e">Source-Only (Intentionally Excluded)</text>

  <rect x="35" y="325" width="350" height="20" rx="3" fill="#f5f5f5" stroke="#e0e0e0"/>
  <text x="45" y="339" fill="#9e9e9e" font-size="11">rvcHealth / rvcVoices / rvcSynthesize (RVC)</text>

  <rect x="35" y="350" width="350" height="20" rx="3" fill="#f5f5f5" stroke="#e0e0e0"/>
  <text x="45" y="364" fill="#9e9e9e" font-size="11">downloadRvcModel / openVoiceStudio (RVC)</text>

  <rect x="35" y="375" width="350" height="20" rx="3" fill="#f5f5f5" stroke="#e0e0e0"/>
  <text x="45" y="389" fill="#9e9e9e" font-size="11">fetchVoiceLibrary / fetchStoreModels (Voice Store)</text>

  <rect x="35" y="400" width="350" height="20" rx="3" fill="#f5f5f5" stroke="#e0e0e0"/>
  <text x="45" y="414" fill="#9e9e9e" font-size="11">downloadModel / cancelDownload / deleteModel</text>

  <rect x="35" y="425" width="350" height="20" rx="3" fill="#f5f5f5" stroke="#e0e0e0"/>
  <text x="45" y="439" fill="#9e9e9e" font-size="11">15+ more RVC/Browser/Store messages</text>

  <!-- Extension Host Side -->
  <rect x="460" y="50" width="400" height="280" rx="8" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="660" y="75" text-anchor="middle" font-size="14" font-weight="bold" fill="#2e7d32">Extension Host (KiloProvider.ts)</text>

  <text x="475" y="100" font-weight="600" fill="#2e7d32">Message Handlers</text>

  <rect x="475" y="110" width="370" height="40" rx="4" fill="white" stroke="#a5d6a7"/>
  <text x="485" y="128" font-weight="600" fill="#2e7d32">sendSpeechSettings()</text>
  <text x="485" y="143" font-size="10" fill="#616161">Reads 24 VS Code config keys -> posts to webview</text>

  <rect x="475" y="160" width="370" height="40" rx="4" fill="white" stroke="#a5d6a7"/>
  <text x="485" y="178" font-weight="600" fill="#2e7d32">validateAzureKey(apiKey, region)</text>
  <text x="485" y="193" font-size="10" fill="#616161">POST test SSML to Azure endpoint -> valid/invalid</text>

  <rect x="475" y="210" width="370" height="40" rx="4" fill="white" stroke="#a5d6a7"/>
  <text x="485" y="228" font-weight="600" fill="#2e7d32">handleUpdateSetting(key, value)</text>
  <text x="485" y="243" font-size="10" fill="#616161">Existing handler persists speech.* to VS Code config</text>

  <rect x="475" y="260" width="370" height="25" rx="4" fill="#fff9c4" stroke="#f9a825"/>
  <text x="485" y="277" font-weight="600" fill="#f57f17">Config change listener for speech.* (ADDED)</text>

  <!-- Arrows -->
  <line x1="400" y1="127" x2="460" y2="127" stroke="#1565c0" stroke-width="2" marker-end="url(#arrowBlue)"/>
  <line x1="400" y1="157" x2="460" y2="177" stroke="#1565c0" stroke-width="2" marker-end="url(#arrowBlue)"/>
  <line x1="460" y1="247" x2="400" y2="247" stroke="#43a047" stroke-width="2" marker-end="url(#arrowGreen)"/>
  <line x1="460" y1="277" x2="400" y2="277" stroke="#43a047" stroke-width="2" marker-end="url(#arrowGreen)"/>

  <!-- Config Store -->
  <rect x="460" y="350" width="400" height="110" rx="8" fill="#fff8e1" stroke="#ffa000" stroke-width="1.5"/>
  <text x="660" y="375" text-anchor="middle" font-size="14" font-weight="bold" fill="#e65100">VS Code Configuration Store</text>
  <text x="475" y="395" font-size="11" fill="#4e342e">kilo-code.new.speech.enabled = false</text>
  <text x="475" y="410" font-size="11" fill="#4e342e">kilo-code.new.speech.azure.voiceId = "en-GB-MaisieNeural"</text>
  <text x="475" y="425" font-size="11" fill="#4e342e">kilo-code.new.speech.tuning.pitch = 0</text>
  <text x="475" y="440" font-size="11" fill="#4e342e">... 24 total speech configuration properties</text>

  <line x1="660" y1="295" x2="660" y2="350" stroke="#ffa000" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrowOrange)"/>

  <defs>
    <marker id="arrowBlue" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="#1565c0"/>
    </marker>
    <marker id="arrowGreen" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="#43a047"/>
    </marker>
    <marker id="arrowOrange" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="#ffa000"/>
    </marker>
  </defs>
</svg>
```

## Message Type Counts

| Category | Source | Azure Edition | Delta |
|----------|:-----:|:------------:|:-----:|
| Speech settings request/response | 2 | 2 | 0 |
| Azure key validation | 0 (implicit) | 2 | +2 |
| RVC messages | 12 | 0 | -12 (intentional) |
| Voice store messages | 8 | 0 | -8 (intentional) |
| Browser TTS messages | 3 | 0 | -3 (intentional) |
| **Total** | **25** | **4** | -21 |

## Voice Data Comparison

| Field | Source | Azure Edition |
|-------|:-----:|:------------:|
| Voice count | 125 | 125 |
| Interface fields | 4 (id, locale, name, gender) | 6 (+description, +styles) |
| Edge TTS subset | 17 voices | Removed (no RVC) |
| Locale names map | -- | Added (14 locales) |
| DEFAULT_VOICE_ID | -- | "en-GB-MaisieNeural" |
| Voice styles data | -- | Per-voice style arrays |

## Package.json Settings Comparison

| Setting Group | Source Keys | Azure Edition Keys |
|--------------|:----------:|:-----------------:|
| Global (enabled, autoSpeak, volume...) | 6 | 8 (+interruptOnType, +multiVoiceMode) |
| Provider selection | 1 (provider enum) | 0 (Azure hardcoded) |
| Azure connection | 3 | 3 |
| RVC settings | 4 | 0 (removed) |
| Browser settings | 3 | 0 (removed) |
| Tuning (SSML) | 0 | 10 (new) |
| Favorites | 0 | 2 (new) |
| Presets | 0 | 1 (new) |
| **Total** | **17** | **24** |
