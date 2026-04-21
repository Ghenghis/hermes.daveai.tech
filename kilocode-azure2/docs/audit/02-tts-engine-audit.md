# TTS Engine Audit: Azure Synthesis & Playback

## SSML Pipeline Comparison

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 400" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <text x="440" y="25" text-anchor="middle" font-size="16" font-weight="bold" fill="#1a1a2e">SSML Generation Pipeline</text>

  <!-- Source Pipeline (Top) -->
  <text x="20" y="60" font-size="13" font-weight="bold" fill="#c62828">Source (38 lines - Basic)</text>
  <rect x="20" y="70" width="120" height="40" rx="5" fill="#ffcdd2" stroke="#c62828"/>
  <text x="80" y="95" text-anchor="middle" fill="#b71c1c">Raw Text</text>
  <line x1="140" y1="90" x2="170" y2="90" stroke="#c62828" stroke-width="2" marker-end="url(#arrowRed)"/>
  <rect x="170" y="70" width="120" height="40" rx="5" fill="#ffcdd2" stroke="#c62828"/>
  <text x="230" y="95" text-anchor="middle" fill="#b71c1c">XML Escape</text>
  <line x1="290" y1="90" x2="320" y2="90" stroke="#c62828" stroke-width="2" marker-end="url(#arrowRed)"/>
  <rect x="320" y="70" width="160" height="40" rx="5" fill="#ffcdd2" stroke="#c62828"/>
  <text x="400" y="88" text-anchor="middle" fill="#b71c1c">Wrap in &lt;voice&gt;</text>
  <text x="400" y="102" text-anchor="middle" font-size="10" fill="#c62828">(no prosody/style)</text>
  <line x1="480" y1="90" x2="510" y2="90" stroke="#c62828" stroke-width="2" marker-end="url(#arrowRed)"/>
  <rect x="510" y="70" width="120" height="40" rx="5" fill="#ffcdd2" stroke="#c62828"/>
  <text x="570" y="95" text-anchor="middle" fill="#b71c1c">Azure REST</text>

  <!-- Azure Edition Pipeline (Bottom) -->
  <text x="20" y="155" font-size="13" font-weight="bold" fill="#2e7d32">Azure Edition (108 lines - Advanced)</text>

  <rect x="20" y="165" width="100" height="40" rx="5" fill="#c8e6c9" stroke="#2e7d32"/>
  <text x="70" y="190" text-anchor="middle" fill="#1b5e20">Raw Text</text>

  <line x1="120" y1="185" x2="140" y2="185" stroke="#2e7d32" stroke-width="2"/>
  <rect x="140" y="165" width="100" height="40" rx="5" fill="#c8e6c9" stroke="#2e7d32"/>
  <text x="190" y="190" text-anchor="middle" fill="#1b5e20">XML Escape</text>

  <line x1="240" y1="185" x2="260" y2="185" stroke="#2e7d32" stroke-width="2"/>
  <rect x="260" y="165" width="120" height="40" rx="5" fill="#a5d6a7" stroke="#2e7d32" stroke-width="2"/>
  <text x="320" y="183" text-anchor="middle" font-weight="600" fill="#1b5e20">Pronunciations</text>
  <text x="320" y="197" text-anchor="middle" font-size="10" fill="#2e7d32">&lt;sub alias&gt;</text>

  <line x1="380" y1="185" x2="400" y2="185" stroke="#2e7d32" stroke-width="2"/>
  <rect x="400" y="165" width="100" height="40" rx="5" fill="#a5d6a7" stroke="#2e7d32" stroke-width="2"/>
  <text x="450" y="183" text-anchor="middle" font-weight="600" fill="#1b5e20">Emphasis</text>
  <text x="450" y="197" text-anchor="middle" font-size="10" fill="#2e7d32">&lt;emphasis&gt;</text>

  <line x1="500" y1="185" x2="520" y2="185" stroke="#2e7d32" stroke-width="2"/>
  <rect x="520" y="165" width="100" height="40" rx="5" fill="#a5d6a7" stroke="#2e7d32" stroke-width="2"/>
  <text x="570" y="183" text-anchor="middle" font-weight="600" fill="#1b5e20">Prosody</text>
  <text x="570" y="197" text-anchor="middle" font-size="10" fill="#2e7d32">pitch/rate/vol</text>

  <line x1="620" y1="185" x2="640" y2="185" stroke="#2e7d32" stroke-width="2"/>
  <rect x="640" y="165" width="100" height="40" rx="5" fill="#a5d6a7" stroke="#2e7d32" stroke-width="2"/>
  <text x="690" y="183" text-anchor="middle" font-weight="600" fill="#1b5e20">Style</text>
  <text x="690" y="197" text-anchor="middle" font-size="10" fill="#2e7d32">express-as</text>

  <line x1="740" y1="185" x2="760" y2="185" stroke="#2e7d32" stroke-width="2"/>
  <rect x="760" y="165" width="100" height="40" rx="5" fill="#c8e6c9" stroke="#2e7d32"/>
  <text x="810" y="190" text-anchor="middle" fill="#1b5e20">Azure REST</text>

  <!-- Playback Comparison -->
  <text x="440" y="250" text-anchor="middle" font-size="16" font-weight="bold" fill="#1a1a2e">Playback Engine Comparison</text>

  <!-- Source Playback -->
  <rect x="20" y="265" width="400" height="120" rx="6" fill="#fff3e0" stroke="#e65100" stroke-width="1.5"/>
  <text x="220" y="285" text-anchor="middle" font-weight="bold" fill="#bf360c">Source: SpeechEngine (903 lines)</text>
  <text x="30" y="305" font-size="11" fill="#4e342e">- Chunked playback (splits text >200 chars)</text>
  <text x="30" y="320" font-size="11" fill="#4e342e">- VAD (Voice Activity Detection) mic pause</text>
  <text x="30" y="335" font-size="11" fill="#4e342e">- AudioCritic quality validation (score >= 60)</text>
  <text x="30" y="350" font-size="11" fill="#4e342e">- Provider stats tracking + fallback ordering</text>
  <text x="30" y="365" font-size="11" fill="#4e342e">- Error/stop callbacks for UI feedback</text>
  <text x="30" y="380" font-size="11" fill="#4e342e">- 3-provider fallback with exponential backoff</text>

  <!-- Azure Edition Playback -->
  <rect x="460" y="265" width="400" height="120" rx="6" fill="#e8f5e9" stroke="#2e7d32" stroke-width="1.5"/>
  <text x="660" y="285" text-anchor="middle" font-weight="bold" fill="#1b5e20">Azure Edition: speech-playback (119 lines)</text>
  <text x="470" y="305" font-size="11" fill="#1b5e20">- Web Audio API (AudioContext + BufferSource)</text>
  <text x="470" y="320" font-size="11" fill="#1b5e20">- LRU synthesis cache (32 entries)</text>
  <text x="470" y="335" font-size="11" fill="#1b5e20">- AbortController for cancel support</text>
  <text x="470" y="350" font-size="11" fill="#1b5e20">- Real-time volume control via GainNode</text>
  <text x="470" y="365" font-size="11" fill="#1b5e20">- Session character counter</text>
  <text x="470" y="380" font-size="11" fill="#1b5e20">- Empty audio detection (blob.size >= 100)</text>

  <defs>
    <marker id="arrowRed" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="#c62828"/>
    </marker>
  </defs>
</svg>
```

## Feature Matrix

| Feature | Source | Azure Edition | Notes |
|---------|:-----:|:------------:|-------|
| Azure REST API synthesis | Basic | **Advanced** | Our version adds SSML fine-tuning |
| Prosody control (pitch/rate/volume) | -- | **Yes** | SSML `<prosody>` element |
| Speaking styles (express-as) | -- | **Yes** | SSML `<mstts:express-as>` |
| Emphasis levels | -- | **Yes** | SSML `<emphasis>` |
| Custom pronunciations | -- | **Yes** | SSML `<sub alias>` |
| Configurable audio format | Hardcoded | **Selectable** | 16/24/48 kHz |
| Empty audio detection | -- | **Yes** | Validates blob.size >= 100 |
| AbortSignal support | -- | **Yes** | Cancel in-flight requests |
| LRU synthesis cache | -- | **Yes** | 32-entry cache |
| Web Audio API playback | Yes | **Yes** | Equivalent |
| Chunked playback | Yes | -- | Not needed for single provider |
| VAD mic detection | Yes | -- | Out of scope for V1 |
| Fallback chain | Yes | -- | Single provider, not applicable |
| Provider stats | Yes | -- | Single provider, not applicable |

## Verdict

The Azure Edition TTS engine is **purpose-built for Azure** with significantly more advanced SSML generation than the source. Features removed (chunking, VAD, fallback) are multi-provider concerns that don't apply to an Azure-only edition.
