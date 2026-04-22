"""
safemode_server.py — Safe-mode HTTP server.
Serves the repair dashboard UI on :7861.
Exposes WebSocket /ws/repair for real-time event streaming.
Exposes POST /repair/trigger to kick off repairs.
Exposes GET /repair/status for polling.
Redirects to :7860 when system is healthy.
"""
from __future__ import annotations
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from health_checks import run_all_checks, summary, is_safemode_required
from repair_agent import full_repair_cycle, RepairEvent

app = FastAPI(title="Hermes Safe-Mode & Repair Server", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WEBUI_URL = os.environ.get("WEBUI_URL", "http://localhost:7860")

# Shared state
_repair_running = False
_repair_result: Optional[dict] = None
_event_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
_subscribers: list[asyncio.Queue] = []


# ── Health gate ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "safemode_server", "ok": True}


@app.get("/check")
async def check():
    results = run_all_checks()
    s = summary(results)
    return JSONResponse(s)


# ── Repair trigger ────────────────────────────────────────────────────────────

@app.post("/repair/trigger")
async def trigger_repair(background_tasks: BackgroundTasks):
    global _repair_running, _repair_result
    if _repair_running:
        return JSONResponse({"status": "already_running"})
    _repair_running = True
    _repair_result = None
    background_tasks.add_task(_run_repair_bg)
    return JSONResponse({"status": "started"})


@app.get("/repair/status")
async def repair_status():
    return JSONResponse({
        "running": _repair_running,
        "result": _repair_result,
    })


async def _run_repair_bg():
    global _repair_running, _repair_result
    q: asyncio.Queue = asyncio.Queue()
    try:
        # Forward events to all subscribers
        asyncio.create_task(_forward_events(q))
        result = await full_repair_cycle(q)
        _repair_result = result
    finally:
        _repair_running = False


async def _forward_events(source: asyncio.Queue):
    while True:
        try:
            event: RepairEvent = await asyncio.wait_for(source.get(), timeout=120)
            for sub in list(_subscribers):
                try:
                    sub.put_nowait(event)
                except asyncio.QueueFull:
                    pass
        except asyncio.TimeoutError:
            break


# ── WebSocket event stream ────────────────────────────────────────────────────

@app.websocket("/ws/repair")
async def ws_repair(ws: WebSocket):
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    try:
        while True:
            try:
                event: RepairEvent = await asyncio.wait_for(q.get(), timeout=30)
                await ws.send_json({
                    "agent": event.agent,
                    "action": event.action,
                    "detail": event.detail,
                    "ok": event.ok,
                    "progress": event.progress,
                    "ts": time.time(),
                })
            except asyncio.TimeoutError:
                await ws.send_json({"ping": True})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        _subscribers.remove(q)


# ── Repair Dashboard UI ───────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Hermes — System Repair</title>
<style>
  :root{--bg:#0d1117;--bg2:#161b22;--bg3:#1c2128;--border:#30363d;
        --green:#3fb950;--yellow:#ffa657;--red:#f85149;--blue:#58a6ff;
        --purple:#a371f7;--text:#e6edf3;--muted:#8b949e}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:monospace;min-height:100vh;padding:20px}
  h1{text-align:center;font-size:1.4rem;margin-bottom:4px;color:var(--blue)}
  .subtitle{text-align:center;color:var(--muted);font-size:.8rem;margin-bottom:20px}
  .progress-wrap{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:4px;margin:0 auto 20px;max-width:700px}
  .progress-bar{height:24px;border-radius:6px;background:linear-gradient(90deg,var(--green),var(--blue));
                transition:width .4s ease;display:flex;align-items:center;justify-content:flex-end;padding-right:8px;font-size:.75rem;font-weight:bold;min-width:32px}
  .status-row{display:flex;justify-content:center;gap:20px;margin-bottom:16px;font-size:.8rem}
  .badge{padding:3px 10px;border-radius:12px;font-weight:bold}
  .badge.green{background:rgba(63,185,80,.15);color:var(--green);border:1px solid var(--green)}
  .badge.yellow{background:rgba(255,166,87,.15);color:var(--yellow);border:1px solid var(--yellow)}
  .badge.red{background:rgba(248,81,73,.15);color:var(--red);border:1px solid var(--red)}
  .badge.blue{background:rgba(88,166,255,.15);color:var(--blue);border:1px solid var(--blue)}
  .panels{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:1200px;margin:0 auto 20px}
  .panel{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:14px}
  .panel h2{font-size:.9rem;margin-bottom:10px;border-bottom:1px solid var(--border);padding-bottom:6px}
  .log{height:300px;overflow-y:auto;font-size:.75rem;line-height:1.6}
  .log-entry{padding:2px 0;border-bottom:1px solid rgba(48,54,61,.4)}
  .log-entry .ts{color:var(--muted);margin-right:6px}
  .log-entry .ag{font-weight:bold;margin-right:6px}
  .log-entry.ok .ag{color:var(--green)}
  .log-entry.fail .ag{color:var(--red)}
  .log-entry .act{color:var(--yellow)}
  .log-entry .det{color:var(--muted)}
  .checks-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:.72rem}
  .check-item{padding:4px 6px;border-radius:4px;display:flex;align-items:center;gap:6px}
  .check-item.pass{background:rgba(63,185,80,.08)}
  .check-item.fail{background:rgba(248,81,73,.08)}
  .check-item .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
  .dot.green{background:var(--green)}
  .dot.red{background:var(--red)}
  .dot.yellow{background:var(--yellow)}
  .buttons{display:flex;justify-content:center;gap:12px;margin:16px 0}
  button{background:var(--bg3);color:var(--text);border:1px solid var(--border);
         border-radius:6px;padding:8px 20px;cursor:pointer;font-family:monospace;font-size:.85rem;transition:border-color .2s}
  button:hover{border-color:var(--blue)}
  button.primary{border-color:var(--blue);color:var(--blue)}
  button.danger{border-color:var(--red);color:var(--red)}
  .ticker{text-align:center;color:var(--muted);font-size:.75rem;margin-top:4px}
  .redirect-banner{display:none;background:rgba(63,185,80,.15);border:2px solid var(--green);
                   border-radius:8px;padding:16px;text-align:center;max-width:700px;margin:20px auto;font-size:1rem}
  @media(max-width:700px){.panels{grid-template-columns:1fr}.checks-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>⚡ Hermes — Autonomous Repair Mode</h1>
<p class="subtitle">System detected failures at boot. Repair agents are working to restore full functionality.</p>

<div class="progress-wrap">
  <div class="progress-bar" id="pbar" style="width:0%">0%</div>
</div>

<div class="status-row">
  <span class="badge blue" id="badge-status">Initializing</span>
  <span class="badge" id="badge-agent">agent: watchdog</span>
  <span class="badge" id="badge-checks">checks: —</span>
  <span id="elapsed-badge" class="badge" style="border-color:var(--muted);color:var(--muted)">00:00</span>
</div>

<div class="redirect-banner" id="redirect-banner">
  ✓ System fully restored! Redirecting to Hermes WebUI in <strong id="countdown">5</strong>s...
</div>

<div class="panels">
  <div class="panel">
    <h2>🤖 Agent Activity Log</h2>
    <div class="log" id="activity-log"></div>
  </div>
  <div class="panel">
    <h2>🔍 Health Check Status</h2>
    <div class="checks-grid" id="checks-grid"></div>
  </div>
</div>

<div class="buttons">
  <button class="primary" onclick="triggerRepair()">▶ Run Repair Now</button>
  <button onclick="runChecks()">🔍 Re-run Checks</button>
  <button onclick="window.open('/terminal','_blank')">💻 Open Terminal</button>
  <button onclick="location.href='/logs'">📋 View Logs</button>
</div>
<p class="ticker" id="ticker">Connecting to repair stream...</p>

<script>
const WEBUI_URL = '""" + WEBUI_URL + """';
let startTime = Date.now();
let progress = 0;
let ws;

function fmt(ts){return new Date(ts*1000).toLocaleTimeString()}
function elapsed(){const s=Math.floor((Date.now()-startTime)/1000);return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}

function addLog(ev){
  const log=document.getElementById('activity-log');
  const div=document.createElement('div');
  div.className='log-entry '+(ev.ok?'ok':'fail');
  div.innerHTML=`<span class="ts">${fmt(ev.ts||Date.now()/1000)}</span>`+
    `<span class="ag">[${ev.agent}]</span>`+
    `<span class="act">${ev.action}:</span> `+
    `<span class="det">${ev.detail||''}</span>`;
  log.appendChild(div);
  log.scrollTop=log.scrollHeight;
}

function updateProgress(pct){
  progress=Math.max(progress,pct);
  const bar=document.getElementById('pbar');
  bar.style.width=progress+'%';
  bar.textContent=progress+'%';
}

function setBadge(id,text,cls){
  const el=document.getElementById(id);
  el.textContent=text;
  el.className='badge '+(cls||'');
}

function handleEvent(ev){
  addLog(ev);
  updateProgress(ev.progress||0);
  setBadge('badge-agent','agent: '+ev.agent, ev.ok?'green':'red');
  document.getElementById('ticker').textContent=ev.action+': '+ev.detail;

  if(ev.progress>=100){
    if(ev.ok){
      setBadge('badge-status','✓ REPAIRED','green');
      showRedirect();
    } else {
      setBadge('badge-status','⚠ PARTIAL','yellow');
    }
  } else {
    setBadge('badge-status','⚡ REPAIRING','yellow');
  }
}

function showRedirect(){
  const banner=document.getElementById('redirect-banner');
  banner.style.display='block';
  let n=5;
  const tick=setInterval(()=>{
    document.getElementById('countdown').textContent=--n;
    if(n<=0){clearInterval(tick);location.href=WEBUI_URL}
  },1000);
}

function connectWS(){
  ws=new WebSocket('ws://'+location.host+'/ws/repair');
  ws.onopen=()=>{document.getElementById('ticker').textContent='Connected to repair stream';};
  ws.onmessage=(e)=>{
    const d=JSON.parse(e.data);
    if(!d.ping) handleEvent(d);
  };
  ws.onclose=()=>{setTimeout(connectWS,3000)};
  ws.onerror=()=>{ws.close()};
}

async function triggerRepair(){
  setBadge('badge-status','⚡ STARTING','blue');
  progress=0;
  document.getElementById('pbar').style.width='0%';
  document.getElementById('pbar').textContent='0%';
  await fetch('/repair/trigger',{method:'POST'});
  document.getElementById('ticker').textContent='Repair triggered...';
}

async function runChecks(){
  setBadge('badge-status','🔍 CHECKING','blue');
  const r=await fetch('/check');
  const d=await r.json();
  setBadge('badge-checks',`checks: ${d.passed}/${d.total}`, d.safemode?'red':'green');
  const grid=document.getElementById('checks-grid');
  grid.innerHTML='';
  const all=[...d.hard_failures,...d.soft_warnings];
  // Show summary
  const item=document.createElement('div');
  item.innerHTML=`<div class="check-item pass"><div class="dot green"></div>${d.passed} passed</div>`;
  grid.innerHTML+=`<div class="check-item pass"><div class="dot green"></div>${d.passed} passed</div>`;
  if(d.failed_hard>0) grid.innerHTML+=`<div class="check-item fail"><div class="dot red"></div>${d.failed_hard} hard fail</div>`;
  if(d.failed_soft>0) grid.innerHTML+=`<div class="check-item fail"><div class="dot yellow"></div>${d.failed_soft} warnings</div>`;
  for(const f of d.hard_failures){
    grid.innerHTML+=`<div class="check-item fail"><div class="dot red"></div><span title="${f.detail}">${f.name}</span></div>`;
  }
  if(d.safemode===false){
    setBadge('badge-status','✓ HEALTHY','green');
    setTimeout(()=>location.href=WEBUI_URL,3000);
  }
}

// Elapsed timer
setInterval(()=>{document.getElementById('elapsed-badge').textContent=elapsed()},1000);

// Init
connectWS();
runChecks();
// Auto-trigger repair if not healthy
setTimeout(async()=>{
  const r=await fetch('/repair/status');
  const d=await r.json();
  if(!d.running && !d.result) triggerRepair();
},2000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/ready")
async def ready_check():
    """Check if system is healthy enough to redirect to WebUI."""
    results = run_all_checks()
    s = summary(results)
    if s["failed_hard"] == 0:
        return RedirectResponse(url=WEBUI_URL, status_code=302)
    return JSONResponse({"safemode": True, "summary": s}, status_code=503)


@app.get("/logs")
async def logs():
    try:
        content = Path("/opt/repair/repair.log").read_text()[-20000:]
    except Exception:
        content = "No repair logs yet."
    return HTMLResponse(
        f"<html><body style='background:#0d1117;color:#e6edf3;font-family:monospace;padding:20px'>"
        f"<pre>{content}</pre></body></html>"
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861, log_level="warning")
