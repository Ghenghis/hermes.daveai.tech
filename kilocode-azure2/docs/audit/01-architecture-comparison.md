# Architecture Comparison: Source vs Azure Voice Edition

## System Architecture

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 520" font-family="Segoe UI, Arial, sans-serif" font-size="13">
  <!-- Title -->
  <text x="450" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a2e">Source (kilocode) vs Azure Voice Edition Architecture</text>

  <!-- Source Architecture (Left) -->
  <rect x="20" y="50" width="400" height="450" rx="8" fill="#f8f9fa" stroke="#dee2e6" stroke-width="1.5"/>
  <text x="220" y="75" text-anchor="middle" font-size="15" font-weight="bold" fill="#495057">Source: Multi-Provider (kilocode)</text>

  <!-- Provider boxes -->
  <rect x="40" y="95" width="110" height="50" rx="6" fill="#e3f2fd" stroke="#1976d2" stroke-width="1.5"/>
  <text x="95" y="118" text-anchor="middle" font-weight="600" fill="#1565c0">Browser TTS</text>
  <text x="95" y="133" text-anchor="middle" font-size="10" fill="#1976d2">Web Speech API</text>

  <rect x="160" y="95" width="110" height="50" rx="6" fill="#e8f5e9" stroke="#388e3c" stroke-width="1.5"/>
  <text x="215" y="118" text-anchor="middle" font-weight="600" fill="#2e7d32">Azure TTS</text>
  <text x="215" y="133" text-anchor="middle" font-size="10" fill="#388e3c">REST API + SSML</text>

  <rect x="280" y="95" width="110" height="50" rx="6" fill="#fce4ec" stroke="#c62828" stroke-width="1.5"/>
  <text x="335" y="118" text-anchor="middle" font-weight="600" fill="#b71c1c">RVC Docker</text>
  <text x="335" y="133" text-anchor="middle" font-size="10" fill="#c62828">Voice Cloning</text>

  <!-- Fallback chain -->
  <rect x="40" y="165" width="350" height="40" rx="6" fill="#fff3e0" stroke="#e65100" stroke-width="1.5"/>
  <text x="215" y="190" text-anchor="middle" font-weight="600" fill="#e65100">Fallback Chain + Exponential Backoff (3 retries)</text>

  <!-- Speech Engine -->
  <rect x="40" y="225" width="350" height="35" rx="6" fill="#f3e5f5" stroke="#7b1fa2" stroke-width="1.5"/>
  <text x="215" y="247" text-anchor="middle" font-weight="600" fill="#6a1b9a">SpeechEngine (903 lines) - Chunked Playback + VAD</text>

  <!-- Text Filter -->
  <rect x="40" y="280" width="170" height="35" rx="6" fill="#e0f7fa" stroke="#00838f" stroke-width="1.5"/>
  <text x="125" y="302" text-anchor="middle" font-weight="600" fill="#006064">speech-text-filter</text>

  <!-- Sentiment -->
  <rect x="220" y="280" width="170" height="35" rx="6" fill="#e0f7fa" stroke="#00838f" stroke-width="1.5"/>
  <text x="305" y="302" text-anchor="middle" font-weight="600" fill="#006064">detectSentiment</text>

  <!-- UI -->
  <rect x="40" y="335" width="350" height="35" rx="6" fill="#e8eaf6" stroke="#283593" stroke-width="1.5"/>
  <text x="215" y="357" text-anchor="middle" font-weight="600" fill="#1a237e">SpeechTab (918 lines) - 3 Provider Tabs + Health</text>

  <!-- Messages -->
  <rect x="40" y="390" width="350" height="35" rx="6" fill="#efebe9" stroke="#4e342e" stroke-width="1.5"/>
  <text x="215" y="412" text-anchor="middle" font-weight="600" fill="#3e2723">25+ Message Types (RVC, Azure, Browser, Voice Store)</text>

  <!-- Commands -->
  <rect x="40" y="445" width="350" height="35" rx="6" fill="#eceff1" stroke="#455a64" stroke-width="1.5"/>
  <text x="215" y="467" text-anchor="middle" font-weight="600" fill="#37474f">VS Code Commands: openVoiceStudio, switchVoice</text>

  <!-- Azure Voice Edition (Right) -->
  <rect x="460" y="50" width="420" height="450" rx="8" fill="#f1f8e9" stroke="#7cb342" stroke-width="2"/>
  <text x="670" y="75" text-anchor="middle" font-size="15" font-weight="bold" fill="#33691e">Azure Voice Edition (kilocode-Azure2)</text>

  <!-- Single Provider -->
  <rect x="530" y="95" width="220" height="50" rx="6" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2"/>
  <text x="640" y="118" text-anchor="middle" font-weight="700" font-size="14" fill="#1b5e20">Azure TTS Only</text>
  <text x="640" y="133" text-anchor="middle" font-size="10" fill="#388e3c">REST API + Advanced SSML</text>

  <!-- Direct playback -->
  <rect x="480" y="165" width="380" height="40" rx="6" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="670" y="190" text-anchor="middle" font-weight="600" fill="#2e7d32">Direct Playback - No Fallback Needed (Single Provider)</text>

  <!-- Speech Playback -->
  <rect x="480" y="225" width="380" height="35" rx="6" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="670" y="247" text-anchor="middle" font-weight="600" fill="#2e7d32">speech-playback (119 lines) + LRU Cache (32 entries)</text>

  <!-- Text Filter -->
  <rect x="480" y="280" width="175" height="35" rx="6" fill="#fff9c4" stroke="#f9a825" stroke-width="1.5"/>
  <text x="567" y="302" text-anchor="middle" font-weight="600" fill="#f57f17">speech-text-filter</text>
  <text x="567" y="312" text-anchor="middle" font-size="9" fill="#f57f17">ADDED IN AUDIT</text>

  <!-- SSML Fine-Tuning -->
  <rect x="665" y="280" width="195" height="35" rx="6" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="762" y="302" text-anchor="middle" font-weight="600" fill="#2e7d32">SSML Fine-Tuning Engine</text>

  <!-- UI -->
  <rect x="480" y="335" width="380" height="35" rx="6" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="670" y="357" text-anchor="middle" font-weight="600" fill="#1b5e20">SpeechTab (617 lines) - 3 Sections + Voice Browser</text>

  <!-- Messages -->
  <rect x="480" y="390" width="380" height="35" rx="6" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="670" y="412" text-anchor="middle" font-weight="600" fill="#2e7d32">4 Message Types (Speech Settings + Azure Validation)</text>

  <!-- Unique features -->
  <rect x="480" y="445" width="185" height="35" rx="6" fill="#c8e6c9" stroke="#2e7d32" stroke-width="1.5"/>
  <text x="572" y="467" text-anchor="middle" font-weight="600" fill="#1b5e20">Voice Presets</text>

  <rect x="675" y="445" width="185" height="35" rx="6" fill="#c8e6c9" stroke="#2e7d32" stroke-width="1.5"/>
  <text x="767" y="467" text-anchor="middle" font-weight="600" fill="#1b5e20">Custom Pronunciations</text>
</svg>
```

## Key Architectural Decisions

| Decision | Source | Azure Voice Edition | Rationale |
|----------|--------|-------------------|-----------|
| Voice Providers | 3 (Browser, Azure, RVC) | 1 (Azure only) | Simplified, premium-quality focus |
| Fallback Chain | Yes (3 retries + backoff) | No (direct Azure) | Single provider = no fallback needed |
| Text Filtering | `speech-text-filter.ts` | Ported from source | Critical for natural speech |
| SSML Fine-Tuning | Basic (no prosody/style) | Advanced (prosody, styles, emphasis) | Azure Edition advantage |
| Voice Catalog | 125 voices, basic data | 125 voices + descriptions + styles | Enhanced browsing experience |
| Default Voice | en-US-JennyNeural | en-GB-MaisieNeural | UK Maisie as brand voice |
| Presets System | Not present | Full preset save/load | Azure Edition exclusive |
| Custom Pronunciations | Not present | SSML `<sub>` aliases | Azure Edition exclusive |
