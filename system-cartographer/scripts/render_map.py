#!/usr/bin/env python3
"""
render_map.py - turn system-map.json into a self-contained HTML explorer and a
Mermaid markdown render.

The JSON is the source of truth. These outputs are disposable; regenerate, never edit.

Usage:
    python3 render_map.py docs/system-map/system-map.json
    python3 render_map.py map.json --out docs/system-map --html-only
    python3 render_map.py map.json --mermaid-only

Layout is computed here, in Python, so the same JSON always produces byte-identical
HTML. That keeps the render diffable and keeps the browser side dumb.
"""

import argparse
import html
import json
import os
import sys
from collections import defaultdict, deque

TW, TH = 62.0, 31.0        # isometric tile half-width / half-height (2:1)
UNIT = 24.0                # pixels of extrusion per height unit
SPACING = 3                # grid cells between adjacent nodes
PAD = 60.0                 # canvas padding

KIND_FOOTPRINT = {
    "store": (1.55, 1.15),
    "queue": (1.7, 0.65),
    "external": (1.0, 1.0),
    "model": (0.72, 0.72),
    "config": (0.8, 0.8),
    "entrypoint": (1.2, 1.0),
    "job": (1.0, 1.0),
    "process": (1.0, 1.0),
}

STATE_ORDER = ["ok", "partial", "stub", "not_wired", "dead"]


# ----------------------------------------------------------------------------- load

def load(path):
    try:
        fh = open(path, "r", encoding="utf-8")
    except OSError as exc:
        sys.exit("error: cannot read %s: %s" % (path, exc.strerror or exc))
    with fh:
        try:
            data = json.load(fh)
        except ValueError as exc:
            sys.exit("error: not valid JSON: %s" % exc)
        except OSError as exc:
            sys.exit("error: cannot read %s: %s" % (path, exc.strerror or exc))
    if not isinstance(data, dict):
        sys.exit("error: the map must be a JSON object")
    if data.get("schema") != "system-map/v1":
        sys.exit("error: schema must be 'system-map/v1', got %r" % data.get("schema"))
    for key in ("repo", "title", "commit", "nodes", "edges"):
        if key not in data:
            sys.exit("error: missing required top-level key %r" % key)
    return data


# --------------------------------------------------------------------------- layout

def perimeter_slots(w, h):
    """Grid coordinates walking clockwise round a w x h rectangle."""
    pts = []
    for x in range(w):
        pts.append((x, 0))
    for y in range(h):
        pts.append((w, y))
    for x in range(w, 0, -1):
        pts.append((x, h))
    for y in range(h, 0, -1):
        pts.append((0, y))
    return pts


def ring_positions(n):
    """Even-ish placement of n nodes round a rectangle, returned in path order."""
    if n <= 0:
        return []
    w = max(2, int(round((n / 4.0) * 1.35)))
    h = max(2, int(round(n / 2.0) - w))
    slots = perimeter_slots(w, h)
    while len(slots) < n:
        w += 1
        h += 1
        slots = perimeter_slots(w, h)
    step = len(slots) / float(n)
    return [slots[int(round(i * step)) % len(slots)] for i in range(n)]


def layer_nodes(nodes, edges, fixed):
    """Longest-path layering over the acyclic part, for everything not on the ring."""
    ids = [n["id"] for n in nodes if n["id"] not in fixed]
    idset = set(ids)
    succ = defaultdict(list)
    indeg = {i: 0 for i in ids}
    for e in edges:
        a, b = e["from"], e["to"]
        if a in idset and b in idset and a != b:
            succ[a].append(b)
            indeg[b] += 1
    layer = {i: 0 for i in ids}
    q = deque([i for i in ids if indeg[i] == 0])
    seen = set(q)
    while q:
        cur = q.popleft()
        for nxt in succ[cur]:
            layer[nxt] = max(layer[nxt], layer[cur] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0 and nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    for i in ids:                      # anything left in a cycle sits at its current layer
        layer.setdefault(i, 0)
    return layer


def compute_layout(data):
    nodes = data["nodes"]
    edges = data["edges"]
    by_id = {n["id"]: n for n in nodes}
    group_order = {g["id"]: g.get("order", 99) for g in data.get("groups", [])}

    # primary loop flow drives the ring
    ring_path = []
    for flow in data.get("flows", []):
        if flow.get("loop"):
            seq = [p for p in flow["path"] if p in by_id]
            deduped = []
            for p in seq:
                if p not in deduped:
                    deduped.append(p)
            if len(deduped) >= 3:
                ring_path = deduped
                break

    pos, taken = {}, set()

    def place(nid, cell):
        pos[nid] = (cell[0] * SPACING, cell[1] * SPACING)
        taken.add(cell)

    if ring_path:
        for nid, cell in zip(ring_path, ring_positions(len(ring_path))):
            place(nid, cell)

    rest = [n for n in nodes if n["id"] not in pos]
    if rest:
        adj = defaultdict(set)
        for e in edges:
            adj[e["from"]].add(e["to"])
            adj[e["to"]].add(e["from"])
        layers = layer_nodes(nodes, edges, set(pos))
        # place the best-connected first, so later nodes have anchors to sit beside
        rest.sort(key=lambda n: (-len(adj[n["id"]] & set(pos)),
                                 group_order.get(n.get("group"), 99),
                                 layers.get(n["id"], 0), n["id"]))
        ring_cells = set(taken)
        cx = sum(c[0] for c in ring_cells) / float(len(ring_cells)) if ring_cells else 0.0
        cy = sum(c[1] for c in ring_cells) / float(len(ring_cells)) if ring_cells else 0.0
        spiral = sorted(((dx, dy) for dx in range(-9, 10) for dy in range(-9, 10)),
                        key=lambda d: (abs(d[0]) + abs(d[1]), abs(d[0]), d[1], d[0]))
        for n in rest:
            anchors = [pos[m] for m in adj[n["id"]] if m in pos]
            if anchors:
                ax = sum(p[0] for p in anchors) / float(len(anchors)) / SPACING
                ay = sum(p[1] for p in anchors) / float(len(anchors)) / SPACING
                # push outward from the ring centre so satellites hang off the outside
                vx, vy = ax - cx, ay - cy
                mag = max(0.001, (vx * vx + vy * vy) ** 0.5)
                ax += 1.6 * vx / mag
                ay += 1.6 * vy / mag
            else:
                ax, ay = cx, cy + 4
            base = (int(round(ax)), int(round(ay)))
            for dx, dy in spiral:
                cell = (base[0] + dx, base[1] + dy)
                if cell not in taken:
                    place(n["id"], cell)
                    break
            else:
                place(n["id"], (base[0], base[1] + 12))

    if pos:
        minx = min(x for x, _ in pos.values())
        miny = min(y for _, y in pos.values())
        pos = {k: (x - minx, y - miny) for k, (x, y) in pos.items()}

    placed = []
    for n in nodes:
        gx, gy = pos[n["id"]]
        fw, fd = KIND_FOOTPRINT.get(n.get("kind", "process"), (1.0, 1.0))
        h = float(n.get("height", 1)) * UNIT
        cx = (gx + fw / 2.0 - gy - fd / 2.0) * TW
        cy = (gx + fw / 2.0 + gy + fd / 2.0) * TH - h
        placed.append({
            "id": n["id"], "gx": gx, "gy": gy, "fw": fw, "fd": fd,
            "h": h, "cx": round(cx, 2), "cy": round(cy, 2),
            "by": round((gx + fw + gy + fd) * TH, 2),   # bottom of the base rhombus
            "corners": iso_box(gx, gy, fw, fd, h),
        })
    return {p["id"]: p for p in placed}


def iso(gx, gy):
    return ((gx - gy) * TW, (gx + gy) * TH)


def iso_box(gx, gy, fw, fd, h):
    p0 = iso(gx, gy)
    p1 = iso(gx + fw, gy)
    p2 = iso(gx + fw, gy + fd)
    p3 = iso(gx, gy + fd)
    top = [(x, y - h) for x, y in (p0, p1, p2, p3)]
    return {
        "top": [[round(x, 2), round(y, 2)] for x, y in top],
        "left": [[round(v, 2) for v in pt] for pt in
                 (top[3], top[2], list(p2), list(p3))],
        "right": [[round(v, 2) for v in pt] for pt in
                  (top[1], top[2], list(p2), list(p1))],
    }


def route(layout, a, b):
    """Elbow route between two node tops, in isometric space."""
    na, nb = layout[a], layout[b]
    ax, ay = na["gx"] + na["fw"] / 2.0, na["gy"] + na["fd"] / 2.0
    bx, by = nb["gx"] + nb["fw"] / 2.0, nb["gy"] + nb["fd"] / 2.0
    elbow = (bx, ay) if abs(bx - ax) >= abs(by - ay) else (ax, by)
    pts = []
    for i, (gx, gy) in enumerate([(ax, ay), elbow, (bx, by)]):
        x, y = iso(gx, gy)
        lift = na["h"] if i == 0 else (nb["h"] if i == 2 else max(na["h"], nb["h"]))
        pts.append([round(x, 2), round(y - lift, 2)])
    if pts[0] == pts[1] or pts[1] == pts[2]:
        pts = [pts[0], pts[2]]
    return pts


# ----------------------------------------------------------------------------- html

CSS = """
:root{
  --paper:#d8d2ab; --ink:#1c1b16; --line:#1c1b16; --dim:#6d6a55;
  --face-top:#e2ddbd; --face-l:#cdc79f; --face-r:#bcb58c; --hl:#1c1b16;
  --ok:#3f6b3f; --partial:#8a6d1f; --stub:#8a4a1f; --dead:#8a2020; --nw:#3f5a8a;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--paper);color:var(--ink);
  font:12px/1.5 "SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace}
#app{display:grid;grid-template-columns:200px 1fr 420px;grid-template-rows:40px 1fr;
  height:100vh}
header{grid-column:1/4;display:flex;align-items:stretch;border-bottom:1px solid var(--line)}
header .repo{padding:0 14px;display:flex;align-items:center;font-weight:700;
  letter-spacing:.02em;border-right:1px solid var(--line);white-space:nowrap}
header .stat{padding:4px 14px;border-right:1px solid var(--line);display:flex;
  flex-direction:column;justify-content:center;white-space:nowrap}
header .stat b{font-size:9px;letter-spacing:.09em;color:var(--dim);font-weight:400}
header .spacer{flex:1;border-right:1px solid var(--line)}
header .ctl{display:flex;align-items:center;gap:6px;padding:0 10px}
button{font:inherit;background:transparent;border:1px solid var(--line);color:var(--ink);
  padding:3px 9px;cursor:pointer;letter-spacing:.06em;font-size:10px}
button:hover{background:var(--ink);color:var(--paper)}
button.on{background:var(--ink);color:var(--paper)}
#side{border-right:1px solid var(--line);overflow-y:auto;padding-bottom:40px}
#side h4{margin:14px 8px 4px;font-size:9px;letter-spacing:.11em;color:var(--dim);
  font-weight:400}
.item{display:flex;gap:7px;align-items:baseline;margin:2px 6px;padding:5px 7px;
  border:1px solid var(--line);cursor:pointer;background:rgba(255,255,255,.14)}
.item.sub{margin-left:18px;background:transparent}
.item:hover,.item.active{background:var(--ink);color:var(--paper)}
.item .k{font-weight:700;font-size:10px;min-width:16px}
.item .n{flex:1;font-size:10px;letter-spacing:.04em}
.item .h{font-size:8.5px;letter-spacing:.05em}
.item:hover .h,.item.active .h{color:var(--paper)}
#stage{position:relative;overflow:hidden;cursor:grab}
#stage.drag{cursor:grabbing}
#zoom{position:absolute;right:10px;top:10px;display:flex;flex-direction:column;gap:4px}
#hint{position:absolute;left:14px;bottom:10px;font-size:10px;color:var(--dim);
  letter-spacing:.06em;pointer-events:none}
#panel{border-left:1px solid var(--line);display:flex;flex-direction:column;overflow:hidden}
#tabs{display:flex;border-bottom:1px solid var(--line);flex:0 0 auto}
#tabs div{flex:1;text-align:center;padding:8px 4px;font-size:10px;letter-spacing:.1em;
  cursor:pointer;border-right:1px solid var(--line)}
#tabs div.on{background:var(--ink);color:var(--paper)}
#body{overflow-y:auto;padding:14px 18px 60px}
#body .eyebrow{font-size:9px;letter-spacing:.13em;color:var(--dim);margin-bottom:2px}
#body h1{font:400 22px/1.25 Georgia,serif;margin:0 0 4px}
#body h2{font-size:9px;letter-spacing:.13em;color:var(--dim);font-weight:400;
  margin:20px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}
#body p{margin:0 0 10px;font-size:12.5px;line-height:1.62}
#body .mark{background:var(--ink);color:var(--paper);padding:0 3px}
#body ul{margin:0 0 10px;padding-left:16px}
#body li{margin-bottom:5px;font-size:12px}
#body code{background:rgba(0,0,0,.07);padding:1px 4px}
.badge{display:inline-block;font-size:9px;letter-spacing:.08em;border:1px solid;
  padding:1px 6px;margin-right:5px}
.b-ok{color:var(--ok);border-color:var(--ok)}
.b-partial{color:var(--partial);border-color:var(--partial)}
.b-stub{color:var(--stub);border-color:var(--stub)}
.b-dead{color:var(--dead);border-color:var(--dead)}
.b-not_wired{color:var(--nw);border-color:var(--nw)}
.cond{border-left:2px solid var(--stub);padding:6px 0 6px 10px;margin:0 0 10px;
  font-size:12px;background:rgba(138,74,31,.07)}
.src{font-size:11px;color:var(--dim);margin-bottom:3px}
.step{border:1px solid var(--line);padding:7px 9px;margin-bottom:6px}
.step b{font-size:10px;letter-spacing:.06em}
.step span{display:block;color:var(--dim);font-size:11px;margin-top:2px}
svg{display:block}
.node{cursor:pointer}
.node .lbl{font-size:15px;font-weight:700;text-anchor:middle;pointer-events:none;
  fill:var(--ink);letter-spacing:.03em}
.node .tag{font-size:9.5px;font-weight:400}
.node.dimmed{opacity:.16}
.node.hot .top{fill:var(--ink)}
.node.hot .lbl{fill:var(--paper)}
.node.hot .tag{fill:var(--ink);font-weight:700}
.edge{fill:none;stroke:var(--line);stroke-width:1.15}
.edge.async{stroke-dasharray:5 4}
.edge.conditional{stroke-dasharray:1.5 3.5}
.edge.error{stroke:var(--dead)}
.edge.dimmed{opacity:.13}
.edge.hot{stroke-width:2.6}
.mark-d{fill:var(--line)}
.grid{stroke:var(--line);stroke-width:.4;opacity:.14}
.tag{font-size:8.5px;fill:var(--dim);letter-spacing:.08em;pointer-events:none}
"""

JS = r"""
const M = window.__MAP__;
const byId = Object.fromEntries(M.nodes.map(n => [n.id, n]));
const lay  = M.layout;
let view = {x:0, y:0, k:1}, hot = null, tab = 0, flowIx = -1, flowStep = 0, timer = null;

const svg = document.getElementById('svg');
const g   = document.getElementById('scene');
const esc = s => (s==null?'':String(s)).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function applyView(){ g.setAttribute('transform',
  `translate(${view.x},${view.y}) scale(${view.k})`); }

function reset(){
  const b = M.bounds, r = svg.getBoundingClientRect();
  view.k = Math.min(r.width/(b.w+80), r.height/(b.h+80), 1.5);
  view.x = (r.width  - b.w*view.k)/2 - b.x*view.k;
  view.y = (r.height - b.h*view.k)/2 - b.y*view.k;
  applyView();
}

function focus(id){
  hot = id; tab = 0; paint(); render();
  document.querySelectorAll('#tabs div').forEach((d,i)=>d.classList.toggle('on', i===0));
}

function neighbours(id){
  const s = new Set([id]);
  M.edges.forEach(e => { if (e.from===id) s.add(e.to); if (e.to===id) s.add(e.from); });
  return s;
}

function paint(){
  const flow = flowIx>=0 ? M.flows[flowIx] : null;
  const near = hot ? neighbours(hot) : null;
  document.querySelectorAll('.node').forEach(el => {
    const id = el.dataset.id;
    el.classList.toggle('hot', id===hot);
    el.classList.toggle('dimmed', !!near && !near.has(id));
  });
  document.querySelectorAll('.edge').forEach(el => {
    const [a,b] = el.dataset.e.split('>');
    let on = !hot || a===hot || b===hot;
    if (flow) {
      const p = flow.path, i = flowStep % Math.max(1, p.length-1);
      on = (p[i]===a && p[i+1]===b);
      el.classList.toggle('hot', on);
    }
    el.classList.toggle('dimmed', !on);
  });
  document.querySelectorAll('.item').forEach(el =>
    el.classList.toggle('active', el.dataset.id===hot));
}

function srcLine(s){
  return esc(s.path) + (s.symbol ? ' &middot; ' + esc(s.symbol) : '')
       + (s.lines ? ' &middot; L' + esc(s.lines) : '');
}

function render(){
  const el = document.getElementById('body');
  if (!hot) {
    const s = M.summary || {};
    el.innerHTML = `<div class="eyebrow">${esc(M.repo).toUpperCase()}</div>
      <h1>${esc(M.title)}</h1><p style="color:#6d6a55">${esc(M.subtitle||'')}</p>
      <h2>WHAT THIS IS</h2><p>${esc(s.what_this_is||'')}</p>
      ${s.hard_part?`<p>${esc(s.hard_part)}</p>`:''}
      <h2>HOW TO READ IT</h2><p>${esc(s.how_to_read||'')}</p>
      ${(M.flows||[]).length?`<h2>FLOWS</h2>`+M.flows.map((f,i)=>
        `<div class="step"><b>${esc(f.label)}</b><span>${esc(f.path.join(' → '))}</span>
         <span>${f.loop?'loops until: '+esc(f.exit||'UNDEFINED'):'one pass'}</span></div>`).join(''):''}
      ${(M.unknowns||[]).length?`<h2>NOT YET UNDERSTOOD</h2><ul>`+
        M.unknowns.map(u=>`<li>${esc(u)}</li>`).join('')+`</ul>`:''}
      <h2>PROVENANCE</h2><p class="src">commit ${esc(M.commit)} &middot; generated ${esc(M.generated)}</p>`;
    return;
  }
  const n = byId[hot];
  const ins  = M.edges.filter(e=>e.to===hot), outs = M.edges.filter(e=>e.from===hot);
  const wire = e => `<li><code>${esc(e.kind)}</code> ${esc(e.label)}${e.condition?' &middot; '+esc(e.condition):''}</li>`;
  let main;
  if (tab === 0) {
    main = `<h2>WHAT IT DOES</h2><p>${esc(n.what_it_does)}</p>
      ${n.condition?`<h2>CONDITION</h2><div class="cond">${esc(n.condition)}</div>`:''}
      ${ins.length?`<h2>RECEIVES</h2><ul>`+ins.map(e=>`<li>from <b>${esc(byId[e.from].label)}</b>: ${esc(e.label)}</li>`).join('')+`</ul>`:''}
      ${outs.length?`<h2>SENDS</h2><ul>`+outs.map(e=>`<li>to <b>${esc(byId[e.to].label)}</b>: ${esc(e.label)}</li>`).join('')+`</ul>`:''}`;
  } else {
    main = `<h2>HOW IT'S BUILT</h2><p>${esc(n.how_its_built)}</p>
      <h2>SOURCE</h2>${(n.source||[]).map(s=>`<div class="src">${srcLine(s)}</div>`).join('')}
      ${(n.steps||[]).length?`<h2>INSIDE, IN ORDER</h2>`+n.steps.map(s=>
        `<div class="step"><b>${esc(s.id)} ${esc(s.label)}</b><span>${esc(s.what||'')}</span></div>`).join(''):''}
      ${(ins.concat(outs)).length?`<h2>WIRING</h2><ul>`+ins.concat(outs).map(wire).join('')+`</ul>`:''}`;
  }
  el.innerHTML = `<div class="eyebrow">${esc((M.groupLabel[n.group]||n.group||'').toUpperCase())}</div>
    <h1>${esc(n.label)}</h1>
    <p><span class="badge b-${esc(n.state)}">${esc(n.state).replace('_',' ')}</span>
       <span class="badge">${esc(n.kind)}</span>
       ${n.owner?`<span class="badge">${esc(n.owner)}</span>`:''}</p>${main}`;
}

/* ---- flow control ---- */
function stepFlow(){
  if (flowIx < 0) flowIx = 0;
  const f = M.flows[flowIx]; if (!f) return;
  flowStep = (flowStep + 1) % Math.max(1, f.path.length - 1);
  hot = f.path[flowStep]; render(); paint();
}
function toggleFlow(){
  const b = document.getElementById('play');
  if (timer) { clearInterval(timer); timer = null; b.classList.remove('on');
               b.textContent = '▶ RESUME THE FLOW'; flowIx = -1; paint(); return; }
  if (!(M.flows||[]).length) return;
  flowIx = 0; flowStep = -1; b.classList.add('on'); b.textContent = '■ STOP';
  stepFlow(); timer = setInterval(stepFlow, 1400);
}

/* ---- interaction ---- */
let drag = null;
svg.addEventListener('mousedown', e => { drag = {x:e.clientX-view.x, y:e.clientY-view.y};
  svg.parentElement.classList.add('drag'); });
addEventListener('mouseup', () => { drag = null; svg.parentElement.classList.remove('drag'); });
addEventListener('mousemove', e => { if (!drag) return;
  view.x = e.clientX-drag.x; view.y = e.clientY-drag.y; applyView(); });
svg.addEventListener('wheel', e => { e.preventDefault();
  const f = e.deltaY < 0 ? 1.12 : 1/1.12, r = svg.getBoundingClientRect();
  const mx = e.clientX-r.left, my = e.clientY-r.top;
  view.x = mx - (mx-view.x)*f; view.y = my - (my-view.y)*f; view.k *= f; applyView();
}, {passive:false});
document.getElementById('zin').onclick  = () => { view.k *= 1.2; applyView(); };
document.getElementById('zout').onclick = () => { view.k /= 1.2; applyView(); };
document.getElementById('rst').onclick  = () => { hot = null; flowIx = -1;
  if (timer){clearInterval(timer);timer=null;
    document.getElementById('play').classList.remove('on');
    document.getElementById('play').textContent='▶ RESUME THE FLOW';}
  reset(); paint(); render(); };
document.getElementById('play').onclick = toggleFlow;
document.getElementById('step').onclick = stepFlow;
document.querySelectorAll('#tabs div').forEach((d,i) => d.onclick = () => {
  tab = i; document.querySelectorAll('#tabs div').forEach((x,j)=>x.classList.toggle('on', i===j));
  render(); });
document.querySelectorAll('.node,.item').forEach(el =>
  el.addEventListener('click', () => focus(el.dataset.id)));
document.querySelectorAll('.node,.item').forEach(el =>
  el.addEventListener('mouseenter', () => { if (!timer) { hot = el.dataset.id;
    tab = tab; render(); paint(); } }));

addEventListener('resize', reset);
reset(); render(); paint();
"""


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def build_html(data, layout):
    nodes, edges = data["nodes"], data["edges"]
    by_id = {n["id"]: n for n in nodes}
    groups = sorted(data.get("groups", []), key=lambda g: g.get("order", 99))
    glabel = {g["id"]: g["label"] for g in groups}

    xs, ys = [], []
    for p in layout.values():
        for face in p["corners"].values():
            for x, y in face:
                xs.append(x)
                ys.append(y)
    bx, by = min(xs) - PAD, min(ys) - PAD
    bw, bh = (max(xs) - min(xs)) + 2 * PAD, (max(ys) - min(ys)) + 2 * PAD

    # ---- svg edges
    parts = []
    for e in edges:
        if e["from"] not in layout or e["to"] not in layout:
            continue
        pts = route(layout, e["from"], e["to"])
        d = " ".join("%s,%s" % (x, y) for x, y in pts)
        mid = pts[len(pts) // 2]
        parts.append(
            '<polyline class="edge %s" data-e="%s&gt;%s" points="%s"/>'
            '<rect class="mark-d" x="%.1f" y="%.1f" width="5" height="5" '
            'transform="rotate(45 %.1f %.1f)"/>'
            % (esc(e.get("kind", "data")), esc(e["from"]), esc(e["to"]), d,
               mid[0] - 2.5, mid[1] - 2.5, mid[0], mid[1]))

    # ---- svg nodes, painters order back to front
    order = sorted(nodes, key=lambda n: (layout[n["id"]]["gx"] + layout[n["id"]]["gy"],
                                         layout[n["id"]]["gx"]))
    for n in order:
        p = layout[n["id"]]
        c = p["corners"]
        poly = lambda pts: " ".join("%s,%s" % (x, y) for x, y in pts)
        fill_top = "none" if n.get("kind") == "external" else "var(--face-top)"
        state = n.get("state", "ok")
        flag = ("" if state == "ok" else
                '<rect class="flag" x="%.1f" y="%.1f" width="7" height="7" '
                'fill="var(--%s)"/>' % (p["cx"] + 14, p["cy"] - 20,
                                        {"partial": "partial", "stub": "stub",
                                         "dead": "dead", "not_wired": "nw"}[state]))
        parts.append(
            '<g class="node st-%s" data-id="%s"><title>%s</title>'
            '<polygon points="%s" fill="var(--face-l)" stroke="var(--line)" stroke-width="1"/>'
            '<polygon points="%s" fill="url(#hatch)" stroke="var(--line)" stroke-width="1"/>'
            '<polygon points="%s" fill="var(--face-r)" stroke="var(--line)" stroke-width="1"/>'
            '<polygon points="%s" fill="url(#hatch)" stroke="var(--line)" stroke-width="1"/>'
            '<polygon class="top" points="%s" fill="%s" stroke="var(--line)" stroke-width="1.2"/>'
            '%s<text class="lbl" x="%.1f" y="%.1f">%s</text>'
            '<text class="tag" x="%.1f" y="%.1f" text-anchor="middle">%s</text></g>'
            % (esc(state), esc(n["id"]),
               esc(n["label"] + " (" + state.replace("_", " ") + ")"),
               poly(c["left"]), poly(c["left"]),
               poly(c["right"]), poly(c["right"]),
               poly(c["top"]), fill_top, flag,
               p["cx"], p["cy"] + 6, esc(n["id"]),
               p["cx"], p["by"] + 15, esc(n["label"])))

    # ---- sidebar
    side = []
    for gp in groups:
        side.append('<h4>%s</h4>' % esc(gp["label"]))
        for n in nodes:
            if n.get("group") != gp["id"]:
                continue
            st = n.get("state", "ok")
            side.append(
                '<div class="item" data-id="%s"><span class="k">%s</span>'
                '<span class="n">%s</span><span class="h b-%s">%s</span></div>'
                % (esc(n["id"]), esc(n["id"]), esc(n["label"]), esc(st),
                   "" if st == "ok" else esc(st.replace("_", " "))))
    ungrouped = [n for n in nodes if n.get("group") not in glabel]
    if ungrouped:
        side.append('<h4>UNGROUPED</h4>')
        for n in ungrouped:
            side.append('<div class="item" data-id="%s"><span class="k">%s</span>'
                        '<span class="n">%s</span></div>'
                        % (esc(n["id"]), esc(n["id"]), esc(n["label"])))

    stats = "".join('<div class="stat"><b>%s</b>%s</div>' % (esc(s["label"]), esc(s["value"]))
                    for s in data.get("stats", []))

    payload = {
        "repo": data["repo"], "title": data["title"], "subtitle": data.get("subtitle", ""),
        "commit": data["commit"], "generated": data.get("generated", ""),
        "summary": data.get("summary", {}), "nodes": nodes, "edges": edges,
        "flows": data.get("flows", []), "unknowns": data.get("unknowns", []),
        "layout": layout, "groupLabel": glabel,
        "bounds": {"x": round(bx, 1), "y": round(by, 1), "w": round(bw, 1), "h": round(bh, 1)},
    }

    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>%(title)s &middot; system map</title>
<style>%(css)s</style></head><body><div id="app">
<header>
  <div class="repo">%(repo)s</div>%(stats)s<div class="spacer"></div>
  <div class="ctl">
    <button id="play">&#9654; RESUME THE FLOW</button>
    <button id="step">TRACE ONE STEP</button>
    <button id="rst">RESET VIEW</button>
  </div>
</header>
<div id="side">%(side)s</div>
<div id="stage">
  <svg id="svg" width="100%%" height="100%%">
    <defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse"
      patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6"
      stroke="var(--line)" stroke-width=".55" opacity=".33"/></pattern></defs>
    <g id="scene">%(svg)s</g>
  </svg>
  <div id="zoom"><button id="zin">+</button><button id="zout">&minus;</button></div>
  <div id="hint">CLICK A BLOCK TO OPEN IT &middot; HOVER TO READ &middot; DRAG TO PAN &middot; SCROLL TO ZOOM</div>
</div>
<div id="panel">
  <div id="tabs"><div class="on">WHAT IT DOES</div><div>HOW IT'S BUILT</div></div>
  <div id="body"></div>
</div>
</div>
<script>window.__MAP__ = %(json)s;</script>
<script>%(js)s</script>
</body></html>""" % {
        "title": esc(data["title"]), "css": CSS, "repo": esc(data["repo"]),
        "stats": stats, "side": "".join(side), "svg": "".join(parts),
        "json": json.dumps(payload, separators=(",", ":")), "js": JS,
    }


# -------------------------------------------------------------------------- mermaid

MERMAID_SHAPE = {
    "store": ('[(', ')]'), "queue": ('>', ']'), "external": ('{{', '}}'),
    "model": ('([', '])'), "config": ('[/', '/]'), "entrypoint": ('((', '))'),
    "job": ('[[', ']]'), "process": ('[', ']'),
}
MERMAID_ARROW = {
    "data": "-->", "control": "==>", "async": "-.->", "conditional": "-.->",
    "error": "-->",
}


def build_mermaid(data):
    nodes, edges = data["nodes"], data["edges"]
    by_id = {n["id"]: n for n in nodes}
    groups = sorted(data.get("groups", []), key=lambda g: g.get("order", 99))
    safe = lambda s: str(s).replace('"', "'").replace("\n", " ")

    out = ["# %s" % data["title"], ""]
    if data.get("subtitle"):
        out += ["_%s_" % data["subtitle"], ""]
    out += ["`%s` at commit `%s`, generated %s."
            % (data["repo"], data["commit"], data.get("generated", "")), ""]
    if data.get("summary", {}).get("what_this_is"):
        out += [data["summary"]["what_this_is"], ""]

    out += ["```mermaid", "flowchart LR"]
    seen = set()
    for gp in groups:
        members = [n for n in nodes if n.get("group") == gp["id"]]
        if not members:
            continue
        out.append('  subgraph %s["%s"]' % (gp["id"], safe(gp["label"])))
        out.append("    direction TB")
        for n in members:
            o, c = MERMAID_SHAPE.get(n.get("kind", "process"), ("[", "]"))
            out.append('    %s%s"%s"%s' % (n["id"], o, safe(n["label"]), c))
            seen.add(n["id"])
        out.append("  end")
    for n in nodes:
        if n["id"] not in seen:
            o, c = MERMAID_SHAPE.get(n.get("kind", "process"), ("[", "]"))
            out.append('  %s%s"%s"%s' % (n["id"], o, safe(n["label"]), c))
    for e in edges:
        if e["from"] not in by_id or e["to"] not in by_id:
            continue
        arrow = MERMAID_ARROW.get(e.get("kind", "data"), "-->")
        lbl = safe(e.get("label", ""))
        if e.get("condition"):
            lbl += " (%s)" % safe(e["condition"])
        out.append('  %s %s|"%s"| %s' % (e["from"], arrow, lbl, e["to"]))
    for st, colour in (("stub", "#8a4a1f"), ("dead", "#8a2020"),
                       ("not_wired", "#3f5a8a"), ("partial", "#8a6d1f")):
        ids = [n["id"] for n in nodes if n.get("state") == st]
        if ids:
            out.append("  classDef %s stroke:%s,stroke-width:2px,stroke-dasharray:4 3"
                       % (st, colour))
            out.append("  class %s %s" % (",".join(ids), st))
    out += ["```", ""]

    out += ["## Nodes", "",
            "| id | name | state | what it does | source |",
            "|---|---|---|---|---|"]
    for n in nodes:
        src = "<br>".join("`%s`" % s["path"] for s in n.get("source", []))
        out.append("| `%s` | %s | %s | %s | %s |"
                   % (n["id"], safe(n["label"]), n.get("state", ""),
                      safe(n["what_it_does"]), src))
    out.append("")

    conds = [n for n in nodes if n.get("condition")]
    if conds:
        out += ["## Condition", ""]
        for n in conds:
            out.append("- **%s**: %s" % (safe(n["label"]), safe(n["condition"])))
        out.append("")

    if data.get("flows"):
        out += ["## Flows", ""]
        for f in data["flows"]:
            out.append("- **%s**: `%s`%s"
                       % (safe(f["label"]), " -> ".join(f["path"]),
                          (". Loops until: %s" % safe(f.get("exit", "UNDEFINED")))
                          if f.get("loop") else ""))
        out.append("")

    if data.get("unknowns"):
        out += ["## Not yet understood", ""]
        out += ["- %s" % safe(u) for u in data["unknowns"]]
        out.append("")

    return "\n".join(out)


# ------------------------------------------------------------------------------ cli

def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("map", nargs="?", default=os.environ.get(
        "SYSTEM_MAP", "docs/system-map/system-map.json"))
    ap.add_argument("--out", default=None, help="output dir (default: alongside the map)")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--mermaid-only", action="store_true")
    a = ap.parse_args()

    data = load(a.map)
    out = a.out or os.path.dirname(os.path.abspath(a.map))

    # Build everything in memory first, so a map of the wrong shape writes nothing.
    html_text = md_text = counts = None
    try:
        if not a.mermaid_only:
            html_text = build_html(data, compute_layout(data))
            counts = "(%d nodes, %d edges)" % (len(data["nodes"]), len(data["edges"]))
        if not a.html_only:
            md_text = build_mermaid(data)
    except Exception as exc:
        reason = ("%s: %s" % (type(exc).__name__, exc)).replace("\n", " ")
        sys.exit("error: cannot render this map (%s). Run verify_map.py on it first."
                 % reason)

    try:
        os.makedirs(out, exist_ok=True)
        if html_text is not None:
            p = os.path.join(out, "system-map.html")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(html_text)
            print("wrote %s  %s" % (p, counts))
        if md_text is not None:
            p = os.path.join(out, "system-map.md")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(md_text)
            print("wrote %s" % p)
    except OSError as exc:
        sys.exit("error: cannot write %s: %s" % (exc.filename or out, exc.strerror or exc))


if __name__ == "__main__":
    main()
