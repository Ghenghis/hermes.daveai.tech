# Auto-Speak Integration & Text Filtering Audit

## Auto-Speak Pipeline

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 520" font-family="Segoe UI, Arial, sans-serif" font-size="12">
  <text x="450" y="25" text-anchor="middle" font-size="16" font-weight="bold" fill="#1a1a2e">Auto-Speak Pipeline: Session Idle -> Voice Output</text>

  <!-- Trigger -->
  <rect x="30" y="50" width="160" height="50" rx="6" fill="#e3f2fd" stroke="#1565c0" stroke-width="2"/>
  <text x="110" y="72" text-anchor="middle" font-weight="700" fill="#0d47a1">Session Status</text>
  <text x="110" y="88" text-anchor="middle" font-size="11" fill="#1565c0">busy -> idle</text>

  <line x1="190" y1="75" x2="220" y2="75" stroke="#424242" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Check settings -->
  <rect x="220" y="50" width="140" height="50" rx="6" fill="#fff9c4" stroke="#f9a825" stroke-width="1.5"/>
  <text x="290" y="72" text-anchor="middle" font-weight="600" fill="#e65100">Check Settings</text>
  <text x="290" y="88" text-anchor="middle" font-size="10" fill="#f57f17">enabled && autoSpeak</text>

  <line x1="360" y1="75" x2="390" y2="75" stroke="#424242" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Find message -->
  <rect x="390" y="50" width="150" height="50" rx="6" fill="#e8eaf6" stroke="#3949ab" stroke-width="1.5"/>
  <text x="465" y="72" text-anchor="middle" font-weight="600" fill="#283593">Find Last</text>
  <text x="465" y="88" text-anchor="middle" font-size="10" fill="#3949ab">Assistant Message</text>

  <line x1="540" y1="75" x2="570" y2="75" stroke="#424242" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Extract text -->
  <rect x="570" y="50" width="140" height="50" rx="6" fill="#e0f2f1" stroke="#00897b" stroke-width="1.5"/>
  <text x="640" y="72" text-anchor="middle" font-weight="600" fill="#004d40">Extract Text</text>
  <text x="640" y="88" text-anchor="middle" font-size="10" fill="#00897b">parts.type === "text"</text>

  <line x1="710" y1="75" x2="740" y2="75" stroke="#424242" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Filter -->
  <rect x="740" y="50" width="140" height="50" rx="6" fill="#fce4ec" stroke="#c62828" stroke-width="2"/>
  <text x="810" y="72" text-anchor="middle" font-weight="700" fill="#b71c1c">Text Filter</text>
  <text x="810" y="88" text-anchor="middle" font-size="10" fill="#c62828">CRITICAL STEP</text>

  <!-- Filter detail -->
  <line x1="810" y1="100" x2="810" y2="125" stroke="#c62828" stroke-width="2" marker-end="url(#arrowRed)"/>

  <!-- Text Filter Pipeline -->
  <rect x="20" y="130" width="860" height="170" rx="8" fill="#fff3e0" stroke="#e65100" stroke-width="1.5"/>
  <text x="450" y="155" text-anchor="middle" font-size="14" font-weight="bold" fill="#bf360c">Text Filter Pipeline (speech-text-filter.ts - 196 lines)</text>

  <!-- Layer boxes -->
  <rect x="35" y="170" width="155" height="55" rx="4" fill="white" stroke="#ff8a65"/>
  <text x="112" y="188" text-anchor="middle" font-weight="600" font-size="11" fill="#d84315">Layer 1: Code Removal</text>
  <text x="112" y="203" text-anchor="middle" font-size="9" fill="#8d6e63">Fenced blocks, inline</text>
  <text x="112" y="215" text-anchor="middle" font-size="9" fill="#8d6e63">code, indented blocks</text>

  <rect x="200" y="170" width="155" height="55" rx="4" fill="white" stroke="#ff8a65"/>
  <text x="277" y="188" text-anchor="middle" font-weight="600" font-size="11" fill="#d84315">Layer 2: Tool Artifacts</text>
  <text x="277" y="203" text-anchor="middle" font-size="9" fill="#8d6e63">Terminal output, diffs</text>
  <text x="277" y="215" text-anchor="middle" font-size="9" fill="#8d6e63">stack traces, markers</text>

  <rect x="365" y="170" width="155" height="55" rx="4" fill="white" stroke="#ff8a65"/>
  <text x="442" y="188" text-anchor="middle" font-weight="600" font-size="11" fill="#d84315">Layer 3: Code IDs</text>
  <text x="442" y="203" text-anchor="middle" font-size="9" fill="#8d6e63">Dot-chains, functions</text>
  <text x="442" y="215" text-anchor="middle" font-size="9" fill="#8d6e63">JSON, identifiers</text>

  <rect x="530" y="170" width="155" height="55" rx="4" fill="white" stroke="#ff8a65"/>
  <text x="607" y="188" text-anchor="middle" font-weight="600" font-size="11" fill="#d84315">Layer 4: Markdown</text>
  <text x="607" y="203" text-anchor="middle" font-size="9" fill="#8d6e63">Headings, bold, links</text>
  <text x="607" y="215" text-anchor="middle" font-size="9" fill="#8d6e63">URLs, paths, tables</text>

  <rect x="695" y="170" width="155" height="55" rx="4" fill="white" stroke="#ff8a65"/>
  <text x="772" y="188" text-anchor="middle" font-weight="600" font-size="11" fill="#d84315">Layer 5: Safety</text>
  <text x="772" y="203" text-anchor="middle" font-size="9" fill="#8d6e63">Whitespace collapse</text>
  <text x="772" y="215" text-anchor="middle" font-size="9" fill="#8d6e63">Length cap (2000 chars)</text>

  <!-- Sentiment -->
  <rect x="35" y="240" width="820" height="45" rx="4" fill="#e8f5e9" stroke="#43a047" stroke-width="1.5"/>
  <text x="450" y="260" text-anchor="middle" font-weight="600" fill="#2e7d32">detectSentiment(text) -> { mood, pitchModifier, rateModifier }</text>
  <text x="450" y="277" text-anchor="middle" font-size="10" fill="#43a047">positive: pitch +1, rate 1.05x  |  negative: pitch -1, rate 0.95x  |  neutral: no change</text>

  <!-- After filter -->
  <line x1="450" y1="300" x2="450" y2="325" stroke="#424242" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Azure Synthesis -->
  <rect x="250" y="330" width="400" height="60" rx="6" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2"/>
  <text x="450" y="355" text-anchor="middle" font-weight="700" font-size="14" fill="#1b5e20">Azure TTS Synthesis</text>
  <text x="450" y="375" text-anchor="middle" font-size="11" fill="#2e7d32">buildSSML() -> fetch() -> Blob -> Web Audio API</text>

  <line x1="450" y1="390" x2="450" y2="415" stroke="#424242" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Playback -->
  <rect x="300" y="420" width="300" height="45" rx="6" fill="#e3f2fd" stroke="#1565c0" stroke-width="1.5"/>
  <text x="450" y="442" text-anchor="middle" font-weight="700" fill="#0d47a1">Web Audio Playback</text>
  <text x="450" y="457" text-anchor="middle" font-size="10" fill="#1565c0">AudioBufferSourceNode -> GainNode -> destination</text>

  <!-- Interrupt -->
  <rect x="650" y="420" width="220" height="45" rx="6" fill="#ffcdd2" stroke="#c62828" stroke-width="1.5"/>
  <text x="760" y="442" text-anchor="middle" font-weight="600" fill="#b71c1c">Interrupt on Typing</text>
  <text x="760" y="457" text-anchor="middle" font-size="10" fill="#c62828">keydown -> stopSpeech()</text>

  <!-- Session switch stop -->
  <rect x="650" y="475" width="220" height="30" rx="6" fill="#f3e5f5" stroke="#7b1fa2" stroke-width="1.5"/>
  <text x="760" y="495" text-anchor="middle" font-weight="600" fill="#6a1b9a">Stop on Session Switch</text>

  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="#424242"/>
    </marker>
    <marker id="arrowRed" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6" fill="#c62828"/>
    </marker>
  </defs>
</svg>
```

## Audit Findings: Text Filtering

| Component | Source | Azure Edition (Before Fix) | Azure Edition (After Fix) |
|-----------|:-----:|:-------------------------:|:------------------------:|
| `filterTextForSpeech()` | 25 guardrail rules | Basic inline regex | **Ported from source** |
| `detectSentiment()` | Keyword-based mood detection | Missing | **Ported from source** |
| Code block removal | Layer 1 (3 rules) | Partial | **Full** |
| Tool artifact removal | Layer 2 (5 rules) | Missing | **Full** |
| Code identifier removal | Layer 3 (3 rules) | Missing | **Full** |
| Markdown cleanup | Layer 4 (12 rules) | Partial | **Full** |
| Safety limits | Layer 5 (2 rules) | Missing | **Full** |
| Length cap | 500/2000/4000 chars | None | **2000 chars** |

## Interrupt Mechanisms

| Trigger | Source | Azure Edition |
|---------|:-----:|:------------:|
| User starts typing | Yes | Yes |
| Session switch | Yes | Yes |
| Stop button | Yes | Yes |
| Manual stop command | Yes (VS Code command) | Via UI button |
| VAD (mic activity) | Yes | No (V1 scope) |
