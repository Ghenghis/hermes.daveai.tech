# SpeechTab UI Audit: Source vs Azure Voice Edition

## UI Section Layout

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <text x="450" y="25" text-anchor="middle" font-size="16" font-weight="bold" fill="#1a1a2e">SpeechTab UI Layout Comparison</text>

  <!-- Source Layout (Left) -->
  <rect x="20" y="45" width="400" height="540" rx="8" fill="#fafafa" stroke="#bdbdbd" stroke-width="1.5"/>
  <text x="220" y="70" text-anchor="middle" font-size="14" font-weight="bold" fill="#424242">Source: 918 lines (3 providers)</text>

  <!-- Provider Tabs -->
  <rect x="35" y="85" width="370" height="35" rx="4" fill="#e3f2fd" stroke="#1565c0"/>
  <rect x="40" y="90" width="80" height="25" rx="3" fill="#bbdefb"/>
  <text x="80" y="107" text-anchor="middle" font-size="11" fill="#0d47a1">Browser</text>
  <rect x="125" y="90" width="80" height="25" rx="3" fill="#1976d2"/>
  <text x="165" y="107" text-anchor="middle" font-size="11" fill="white" font-weight="600">Azure</text>
  <rect x="210" y="90" width="80" height="25" rx="3" fill="#bbdefb"/>
  <text x="250" y="107" text-anchor="middle" font-size="11" fill="#0d47a1">RVC</text>
  <circle cx="315" cy="102" r="5" fill="#4caf50"/>
  <circle cx="335" cy="102" r="5" fill="#ff9800"/>
  <circle cx="355" cy="102" r="5" fill="#f44336"/>
  <text x="380" y="107" font-size="9" fill="#757575">health</text>

  <!-- Settings -->
  <rect x="35" y="130" width="370" height="110" rx="4" fill="white" stroke="#e0e0e0"/>
  <text x="45" y="148" font-weight="600" fill="#424242">Global Settings</text>
  <text x="45" y="165" font-size="11" fill="#757575">Enable Speech / Auto-Speak / Volume</text>
  <text x="45" y="180" font-size="11" fill="#757575">Interaction Mode / Debug</text>
  <text x="45" y="195" font-size="11" fill="#757575">Sentiment Intensity / Multi-Voice</text>
  <text x="45" y="215" font-size="11" fill="#757575">Stop on Typing</text>
  <text x="45" y="232" font-size="11" fill="#ff5722" font-weight="600">Provider: [Browser | Azure | RVC]</text>

  <!-- Azure Panel -->
  <rect x="35" y="250" width="370" height="80" rx="4" fill="white" stroke="#e0e0e0"/>
  <text x="45" y="268" font-weight="600" fill="#424242">Azure Panel</text>
  <text x="45" y="285" font-size="11" fill="#757575">API Key (masked) + Test button</text>
  <text x="45" y="300" font-size="11" fill="#757575">Region / Voice dropdown</text>
  <text x="45" y="315" font-size="11" fill="#757575">Azure key status badge</text>

  <!-- RVC Panel -->
  <rect x="35" y="340" width="370" height="80" rx="4" fill="#ffebee" stroke="#ef9a9a"/>
  <text x="45" y="358" font-weight="600" fill="#c62828">RVC Panel (NOT in Azure Edition)</text>
  <text x="45" y="375" font-size="11" fill="#c62828">Docker port / Edge TTS voice</text>
  <text x="45" y="390" font-size="11" fill="#c62828">RVC Pitch Shift / Auto-setup</text>
  <text x="45" y="405" font-size="11" fill="#c62828">Model download + voice list</text>

  <!-- Speech Log -->
  <rect x="35" y="430" width="370" height="50" rx="4" fill="#fff3e0" stroke="#ffcc80"/>
  <text x="45" y="450" font-weight="600" fill="#e65100">Speech Activity Log</text>
  <text x="45" y="465" font-size="11" fill="#e65100">Last 5 events with provider + status</text>

  <!-- Preview -->
  <rect x="35" y="490" width="370" height="40" rx="4" fill="white" stroke="#e0e0e0"/>
  <text x="45" y="510" font-weight="600" fill="#424242">Preview: text + Play + Compare All</text>
  <text x="45" y="522" font-size="11" fill="#757575">Preview status feedback (error/fallback/ok)</text>

  <!-- Azure Edition Layout (Right) -->
  <rect x="460" y="45" width="420" height="540" rx="8" fill="#f1f8e9" stroke="#7cb342" stroke-width="2"/>
  <text x="670" y="70" text-anchor="middle" font-size="14" font-weight="bold" fill="#33691e">Azure Edition: 617 lines (Azure only)</text>

  <!-- Section 1 -->
  <rect x="475" y="85" width="390" height="150" rx="4" fill="white" stroke="#66bb6a" stroke-width="1.5"/>
  <rect x="475" y="85" width="390" height="28" rx="4" fill="#e8f5e9"/>
  <text x="485" y="103" font-weight="700" fill="#2e7d32">Section 1: Connection + Global Settings</text>
  <circle cx="845" cy="99" r="5" fill="#4caf50"/>
  <text x="485" y="123" font-size="11" fill="#424242">API Key (masked) + Test + Region</text>
  <text x="485" y="138" font-size="11" fill="#424242">Enable / Auto-Speak / Volume slider</text>
  <text x="485" y="153" font-size="11" fill="#424242">Interaction Mode / Stop on Typing</text>
  <text x="485" y="168" font-size="11" fill="#424242">Sentiment Intensity / Multi-Voice</text>
  <text x="485" y="183" font-size="11" fill="#424242">Debug Mode</text>
  <text x="770" y="123" font-size="10" fill="#7cb342" font-style="italic">collapsible</text>

  <!-- Section 2 -->
  <rect x="475" y="245" width="390" height="170" rx="4" fill="white" stroke="#66bb6a" stroke-width="1.5"/>
  <rect x="475" y="245" width="390" height="28" rx="4" fill="#e8f5e9"/>
  <text x="485" y="263" font-weight="700" fill="#2e7d32">Section 2: Voice Browser + Favorites</text>

  <text x="485" y="283" font-size="11" fill="#2e7d32" font-weight="600">Favorites chips bar (starred + presets)</text>
  <text x="485" y="298" font-size="11" fill="#424242">Search input + Locale filter dropdown</text>
  <text x="485" y="313" font-size="11" fill="#424242">Preview textarea (multi-line)</text>
  <text x="485" y="333" font-size="11" fill="#2e7d32" font-weight="600">Voice cards list (scrollable, 320px)</text>
  <text x="495" y="348" font-size="10" fill="#757575">Name | Gender | Locale | Description | Styles</text>
  <text x="495" y="363" font-size="10" fill="#757575">Star toggle | Preview button per voice</text>
  <text x="485" y="383" font-size="11" fill="#424242">Voice count + selected voice indicator</text>
  <text x="485" y="398" font-size="11" fill="#2e7d32" font-weight="600">NEW: Voice descriptions + style tags</text>
  <text x="770" y="283" font-size="10" fill="#7cb342" font-style="italic">always open</text>

  <!-- Section 3 -->
  <rect x="475" y="425" width="390" height="150" rx="4" fill="white" stroke="#66bb6a" stroke-width="1.5"/>
  <rect x="475" y="425" width="390" height="28" rx="4" fill="#e8f5e9"/>
  <text x="485" y="443" font-weight="700" fill="#2e7d32">Section 3: Voice Fine-Tuning</text>

  <text x="485" y="463" font-size="11" fill="#424242">Pitch slider (-50% to +50%)</text>
  <text x="485" y="478" font-size="11" fill="#424242">Rate slider (0.5x to 2.0x)</text>
  <text x="485" y="493" font-size="11" fill="#424242">Per-voice volume + "Use global" checkbox</text>
  <text x="485" y="508" font-size="11" fill="#2e7d32" font-weight="600">Style chips (voice-dependent) + intensity</text>
  <text x="485" y="523" font-size="11" fill="#424242">Sentence pause / Paragraph break sliders</text>
  <text x="485" y="538" font-size="11" fill="#2e7d32" font-weight="600">Custom pronunciations table + Presets</text>
  <text x="485" y="553" font-size="11" fill="#424242">Audio quality selector + Play/Stop</text>
  <text x="485" y="568" font-size="11" fill="#2e7d32" font-weight="600">Save as Preset + Preset list (load/delete)</text>
  <text x="770" y="463" font-size="10" fill="#7cb342" font-style="italic">collapsible</text>
</svg>
```

## Features Intentionally Excluded (Azure-Only Design)

| Source Feature | Why Excluded | Impact |
|---------------|-------------|--------|
| Provider tabs (Browser/Azure/RVC) | Azure-only edition | None - single provider |
| RVC Docker panel | No RVC in this edition | None |
| Browser voice selector | No browser TTS | None |
| Voice comparison across providers | Single provider | N/A |
| RVC auto-setup wizard | No RVC | None |
| Edge TTS voice selector | No RVC dependency | None |
| Provider health dashboard | Single provider | Replaced by connection badge |

## Features Unique to Azure Voice Edition

| Feature | Description |
|---------|-------------|
| Voice Browser with descriptions | 125 voices with characterization text |
| Voice style tags | Shows available speaking styles per voice |
| Favorites chips bar | Quick-access starred voices + presets |
| Locale filter dropdown | Filter by 14 English locales |
| Voice fine-tuning section | Pitch, rate, style, emphasis, pauses |
| Custom pronunciations | Word-level SSML substitution rules |
| Preset save/load system | Save complete voice+tuning configurations |
| Audio quality selector | 16kHz / 24kHz / 48kHz output |
| Per-voice volume override | Independent volume with "use global" option |
