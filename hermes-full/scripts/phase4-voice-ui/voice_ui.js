/**
 * Phase 4 — Hermes Voice UI
 * Add to Open WebUI via Admin → Settings → Interface → Custom JS
 * Provides: mic button (STT) + auto-play TTS for agent responses
 */

(function () {
    'use strict';

    const VOICE_GW = 'http://localhost:8001';   // voice_gateway.py
    let activeAgent = 'hermes1';
    let ttsEnabled  = true;
    let recording   = false;
    let mediaRec    = null;
    let chunks      = [];

    // ── Inject voice control bar ──────────────────────────────────────────────
    function injectVoiceBar() {
        if (document.getElementById('hermes-voice-bar')) return;

        const bar = document.createElement('div');
        bar.id = 'hermes-voice-bar';
        bar.style.cssText = [
            'position:fixed', 'bottom:20px', 'right:20px', 'z-index:9999',
            'display:flex', 'gap:8px', 'align-items:center',
            'background:#0f172a', 'border:1px solid #1e293b',
            'border-radius:12px', 'padding:8px 14px',
            'font-family:system-ui,sans-serif',
            'box-shadow:0 4px 24px rgba(0,0,0,.5)',
        ].join(';');

        // Mic button
        const mic = document.createElement('button');
        mic.id = 'hermes-mic';
        mic.title = 'Hold to speak';
        mic.innerHTML = '🎤';
        mic.style.cssText = 'background:transparent;border:none;font-size:22px;cursor:pointer;';
        mic.addEventListener('mousedown', startRecording);
        mic.addEventListener('mouseup',   stopRecording);
        mic.addEventListener('touchstart', startRecording, {passive: true});
        mic.addEventListener('touchend',   stopRecording);
        bar.appendChild(mic);

        // TTS toggle
        const ttsBtn = document.createElement('button');
        ttsBtn.id = 'hermes-tts-btn';
        ttsBtn.title = 'Toggle voice output';
        ttsBtn.innerHTML = '🔊';
        ttsBtn.style.cssText = 'background:transparent;border:none;font-size:18px;cursor:pointer;';
        ttsBtn.addEventListener('click', () => {
            ttsEnabled = !ttsEnabled;
            ttsBtn.innerHTML = ttsEnabled ? '🔊' : '🔇';
        });
        bar.appendChild(ttsBtn);

        // Status label
        const status = document.createElement('span');
        status.id = 'hermes-voice-status';
        status.textContent = 'Ready';
        status.style.cssText = 'color:#64748b;font-size:11px;min-width:60px;';
        bar.appendChild(status);

        document.body.appendChild(bar);
    }

    // ── STT: record mic audio → POST to /stt → fill chat input ──────────────
    async function startRecording() {
        if (recording) return;
        recording = true;
        chunks = [];
        setStatus('🔴 Recording…');

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRec = new MediaRecorder(stream);
        mediaRec.ondataavailable = e => chunks.push(e.data);
        mediaRec.start();
    }

    async function stopRecording() {
        if (!recording || !mediaRec) return;
        recording = false;

        mediaRec.stop();
        mediaRec.onstop = async () => {
            setStatus('⏳ Transcribing…');
            const blob = new Blob(chunks, { type: 'audio/webm' });
            const form = new FormData();
            form.append('audio', blob, 'speech.webm');

            try {
                const resp = await fetch(`${VOICE_GW}/stt`, { method: 'POST', body: form });
                const data = await resp.json();
                if (data.transcript) {
                    fillInput(data.transcript);
                    setStatus('✓ Transcribed');
                } else {
                    setStatus('No speech');
                }
            } catch (err) {
                setStatus('STT error');
                console.error('[Hermes Voice] STT error:', err);
            }
        };
    }

    // ── TTS: play agent response via /tts ─────────────────────────────────────
    async function speakResponse(text) {
        if (!ttsEnabled || !text.trim()) return;
        const agentId = window.__hermesSelectedAgent?.id || activeAgent;

        try {
            const resp = await fetch(`${VOICE_GW}/tts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId, text }),
            });
            if (!resp.ok) return;
            const blob = await resp.blob();
            const url  = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.onended = () => URL.revokeObjectURL(url);
            audio.play();
        } catch (err) {
            console.error('[Hermes Voice] TTS error:', err);
        }
    }

    // ── Observe chat for new assistant messages and auto-play TTS ────────────
    function observeChat() {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(m => {
                m.addedNodes.forEach(node => {
                    if (node.nodeType !== 1) return;
                    // Open WebUI marks assistant messages with data-role or class
                    if (node.dataset?.role === 'assistant' || node.classList?.contains('assistant-message')) {
                        const text = node.innerText || '';
                        if (text.length > 0 && text.length < 2000) {
                            speakResponse(text);
                        }
                    }
                });
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // ── Fill Open WebUI's chat textarea ───────────────────────────────────────
    function fillInput(text) {
        const textarea = document.querySelector('textarea[placeholder], textarea#chat-input, textarea');
        if (!textarea) return;
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        nativeInputValueSetter.call(textarea, text);
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        textarea.focus();
    }

    function setStatus(msg) {
        const el = document.getElementById('hermes-voice-status');
        if (el) el.textContent = msg;
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    function init() {
        injectVoiceBar();
        observeChat();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.__hermesVoice = { speakResponse, startRecording, stopRecording };
})();
