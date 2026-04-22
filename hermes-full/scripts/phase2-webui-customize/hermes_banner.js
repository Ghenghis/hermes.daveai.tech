/**
 * Phase 2 Task 2.3 — Open WebUI Hermes customisation
 * Drop this into Open WebUI's custom JS injection field (Admin → Settings → Interface → Custom JS)
 * or include via nginx sub_filter injection.
 */

(function () {
    'use strict';

    const AGENTS = [
        { id: 'hermes1', name: 'Hermes 1',  role: 'Planning Strategist',   voice: 'en-GB-MaisieNeural',       color: '#7c3aed' },
        { id: 'hermes2', name: 'Hermes 2',  role: 'Creative Brainstormer', voice: 'en-AU-CarlyNeural',        color: '#0ea5e9' },
        { id: 'hermes3', name: 'Hermes 3',  role: 'System Architect',      voice: 'en-KE-AsiliaNeural',       color: '#10b981' },
        { id: 'hermes4', name: 'Hermes 4',  role: 'Bug Triage Specialist', voice: 'en-US-TonyNeural',         color: '#f59e0b' },
        { id: 'hermes5', name: 'Hermes 5',  role: 'Root Cause Analyst',    voice: 'en-US-ChristopherNeural', color: '#ef4444' },
    ];

    // Inject Hermes agent selector banner at top of page
    function injectBanner() {
        if (document.getElementById('hermes-agent-banner')) return;

        const banner = document.createElement('div');
        banner.id = 'hermes-agent-banner';
        banner.style.cssText = [
            'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:9999',
            'background:#0f172a', 'border-bottom:1px solid #1e293b',
            'display:flex', 'align-items:center', 'gap:8px',
            'padding:6px 16px', 'font-family:system-ui,sans-serif',
        ].join(';');

        const label = document.createElement('span');
        label.textContent = 'Agent:';
        label.style.cssText = 'color:#94a3b8;font-size:12px;font-weight:600;letter-spacing:.05em;';
        banner.appendChild(label);

        AGENTS.forEach(agent => {
            const btn = document.createElement('button');
            btn.id = `hermes-btn-${agent.id}`;
            btn.textContent = `${agent.name}`;
            btn.title = agent.role;
            btn.style.cssText = [
                `background:${agent.color}22`, `border:1px solid ${agent.color}66`,
                `color:${agent.color}`, 'border-radius:6px', 'padding:2px 10px',
                'font-size:12px', 'cursor:pointer', 'transition:all .15s',
            ].join(';');

            btn.addEventListener('click', () => selectAgent(agent));
            banner.appendChild(btn);
        });

        // TPS indicator
        const tps = document.createElement('span');
        tps.id = 'hermes-tps';
        tps.style.cssText = 'margin-left:auto;color:#64748b;font-size:11px;';
        tps.textContent = 'TPS: —';
        banner.appendChild(tps);

        document.body.prepend(banner);
        document.body.style.marginTop = '38px';
        fetchTPS();
        setInterval(fetchTPS, 15000);
    }

    let selectedAgent = AGENTS[0];

    function selectAgent(agent) {
        selectedAgent = agent;
        // Highlight active button
        AGENTS.forEach(a => {
            const btn = document.getElementById(`hermes-btn-${a.id}`);
            if (btn) btn.style.fontWeight = a.id === agent.id ? 'bold' : 'normal';
        });
        // Store selection for gateway requests
        window.__hermesSelectedAgent = agent;
        console.log(`[Hermes] Active agent: ${agent.id} (${agent.role})`);
    }

    function fetchTPS() {
        fetch('http://localhost:8000/tps')
            .then(r => r.json())
            .then(d => {
                const el = document.getElementById('hermes-tps');
                if (el) el.textContent = `TPS: ${d.remaining}/${d.limit}`;
            })
            .catch(() => {});
    }

    // Run after DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectBanner);
    } else {
        injectBanner();
    }

    selectAgent(AGENTS[0]);
    window.__hermesAgents = AGENTS;
})();
