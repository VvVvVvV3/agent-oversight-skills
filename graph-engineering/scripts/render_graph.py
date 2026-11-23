#!/usr/bin/env python3
"""Render a graph-spec.json to Mermaid. The JSON is the truth; this output is a derived view.

Usage: python render_graph.py path/to/graph-spec.json > graph.mmd
"""
import json
import sys

SHAPES = {
    "source": ("([", "])"),
    "agent": ("[", "]"),
    "function": ("[[", "]]"),
    "router": ("{", "}"),
    "join": ("{{", "}}"),
    "verifier": ("[/", "/]"),
    "gate": ("[(", ")]"),
    "sink": ("[(", ")]"),
}

CLASS = {
    "agent": "agent",
    "verifier": "verifier",
    "gate": "gate",
    "sink": "sink",
    "function": "fn",
    "router": "fn",
    "join": "fn",
    "source": "fn",
}


def esc(s):
    return s.replace('"', "'")


def build(path):
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    if not isinstance(spec, dict):
        raise ValueError("not a JSON object")
    for key in ("nodes", "edges"):
        items = spec.get(key, [])
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ValueError(key + " is not a list of objects")
    for n in spec.get("nodes", []):
        if "id" not in n or "type" not in n:
            raise ValueError("a node has no id or no type")
    out = [f"%% {spec.get('name')} v{spec.get('version')}  (rendered from graph-spec.json; do not hand-edit)", "flowchart TD"]
    for n in spec.get("nodes", []):
        l, r = SHAPES.get(n["type"], ("[", "]"))
        label = f"{n['id']}<br/><i>{n['type']}</i>"
        if n["type"] == "sink" and n.get("irreversible"):
            label += "<br/>IRREVERSIBLE"
        out.append(f'  {n["id"]}{l}"{esc(label)}"{r}')
    for e in spec.get("edges", []):
        label = esc(f"{e.get('payload', '')} | {e.get('trigger', '')}")
        arrow = "-.->" if e.get("trigger", "").startswith("on-reject") else "-->"
        out.append(f'  {e["from"]} {arrow}|"{label}"| {e["to"]}')
    out.append("  classDef agent fill:#e8f0fe,stroke:#1a56db;")
    out.append("  classDef verifier fill:#fff4e5,stroke:#b45309;")
    out.append("  classDef gate fill:#fde8e8,stroke:#b91c1c,stroke-width:2px;")
    out.append("  classDef sink fill:#e5e7eb,stroke:#374151;")
    out.append("  classDef fn fill:#f0fdf4,stroke:#15803d;")
    by_class = {}
    for n in spec.get("nodes", []):
        by_class.setdefault(CLASS.get(n["type"], "fn"), []).append(n["id"])
    for cls, ids in by_class.items():
        out.append(f"  class {','.join(ids)} {cls};")
    return "\n".join(out)


def main(path):
    try:
        text = build(path)
    except OSError:
        print(f"ERROR cannot read {path}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("ERROR cannot draw this spec; run validate_graph.py on it first", file=sys.stderr)
        sys.exit(1)
    print(text)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    for _stream, _kw in ((sys.stdout, {"encoding": "utf-8", "errors": "backslashreplace"}), (sys.stderr, {"errors": "backslashreplace"})):
        try:
            _stream.reconfigure(**_kw)
        except Exception:
            pass
    main(sys.argv[1])
