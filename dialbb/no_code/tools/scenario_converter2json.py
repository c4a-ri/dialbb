#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scenario_converter2json.py

Convert scenario.xlsx -> state_graph.json (PySide6 scenario_editor compatible)

Excel columns expected (sheet: scenario by default):
- state
- system utterance
- user utterance example
- user utterance type
- conditions
- actions
- next state

Rules (based on your spec):
1) state -> system node_kind mapping:
    1-1) #initial/#prep/#error => initial/prep/error (strip '#')
    1-2) '#final_' (and typo '#finel_') prefix => final
    1-3) If 'system utterance' == '$skip', the utterance is preserved as '$skip' in JSON; node kind is
            determined by the state (no special 'skip' kind).
    else => other  (but if state starts with '#xxx' then 'xxx' is used as kind)
2) If current system is final, do not create user nodes under that system.
3/4) (No extra branching) system utterance may be omitted for consecutive rows of same state:
   - if state unchanged and system utterance empty => inherit previous system utterance in same state block
   - system node identity is (state, effective_system_utterance)
5) Duplicate error for special states (#initial/#prep/#error):
   - if same special state appears with different system utterance => raise error
6) userNode priority:
   - within same state block, first created user row => 100, then 90, 80... (-10)
   - reset to 100 when state changes
"""

from __future__ import annotations

import argparse
import json
import re
import string
import uuid
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd


NODE_TYPE_SYSTEM = "system"
NODE_TYPE_USER = "user"

REQUIRED_COLS = [
    "state",
    "system utterance",
    "user utterance example",
    "user utterance type",
    "conditions",
    "actions",
    "next state",
]

SPECIAL_STATES = {"#initial", "#prep", "#error"}


def gen_short_id(length: int = 6, used: Optional[set[str]] = None) -> str:
    chars = string.ascii_uppercase + string.digits
    used = used if used is not None else set()
    while True:
        s = "".join(random.choices(chars, k=length))
        if s not in used:
            used.add(s)
            return s


def system_kind_from(state: str, sys_utt: str) -> str:
    s = (state or "").strip()
    u = (sys_utt or "").strip()


    # 1-2) '#final_' (and typo '#finel_') => final
    if re.match(r"^#final_", s, flags=re.IGNORECASE) or re.match(r"^#finel_", s, flags=re.IGNORECASE):
        return "final"

    # 1-1) special => strip '#'
    if s in SPECIAL_STATES:
        return s[1:]

    # if other '#xxx' appears, keep behavior close to existing converter: strip '#'
    if s.startswith("#") and len(s) > 1:
        return s[1:]

    return "other"


def read_excel_rows(xlsx_path: Path, sheet: str) -> List[Dict[str, str]]:
    df = pd.read_excel(xlsx_path, sheet_name=sheet)
    df = df.fillna("")

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}\nAvailable: {list(df.columns)}")

    rows: List[Dict[str, str]] = []
    for _, r in df.iterrows():
        row = {c: (str(r[c]).strip() if r[c] is not None else "") for c in REQUIRED_COLS}
        rows.append(row)
    return rows


def is_user_row_empty(row: Dict[str, str]) -> bool:
    # existing behavior: if all user-area columns are empty, do not create a user node
    user_area = [
        row.get("user utterance example", ""),
        row.get("user utterance type", ""),
        row.get("conditions", ""),
        row.get("actions", ""),
        row.get("next state", ""),
    ]
    return "".join(user_area).strip() == ""


def apply_simple_layout(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], dx: float = 280.0, dy: float = 310.0):
    """
    Similar spirit to your auto_layout:
    - Build undirected adjacency, directed incoming_count from edges
    - BFS levels from roots (incoming==0 system preferred)
    - Place each level at x=level*dx, distribute y to avoid overlap
    - Sort: user level by priority desc, else keep as-is order
    """
    id2node = {n["id"]: n for n in nodes}
    if not id2node:
        return

    adj: Dict[str, set[str]] = {nid: set() for nid in id2node}
    incoming: Dict[str, int] = {nid: 0 for nid in id2node}

    for e in edges:
        a = e["from"]
        b = e["to"]
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
        if b in incoming:
            incoming[b] += 1
        incoming.setdefault(a, incoming.get(a, 0))

    # roots: incoming==0 system preferred
    roots = [nid for nid, n in id2node.items() if n.get("type") == NODE_TYPE_SYSTEM and incoming.get(nid, 0) == 0]
    if not roots:
        roots = [nid for nid in id2node if incoming.get(nid, 0) == 0]
    if not roots:
        roots = list(id2node.keys())

    level: Dict[str, int] = {}
    q: List[str] = []
    for r in roots:
        level[r] = 0
        q.append(r)

    while q:
        cur = q.pop(0)
        for nb in adj.get(cur, []):
            if nb not in level:
                level[nb] = level[cur] + 1
                q.append(nb)

    # fill missing
    if len(level) < len(id2node):
        max_lv = max(level.values()) if level else 0
        for nid in id2node:
            if nid not in level:
                max_lv += 1
                level[nid] = max_lv

    levels: Dict[int, List[Dict[str, Any]]] = {}
    for nid, lv in level.items():
        levels.setdefault(lv, []).append(id2node[nid])

    base_x = 0.0
    base_y = 0.0

    for lv in sorted(levels.keys()):
        group = levels[lv]
        x = base_x + lv * dx

        # if all user, sort by priority desc (bigger on top)
        if group and all(n.get("type") == NODE_TYPE_USER for n in group):
            def pr(n: Dict[str, Any]) -> int:
                try:
                    return int(n.get("priority", 0))
                except Exception:
                    return 0
            group_sorted = sorted(group, key=pr, reverse=True)
        else:
            group_sorted = group  # keep insertion-ish order

        n = len(group_sorted)
        start_y = base_y - (n - 1) * dy / 2.0
        for i, node in enumerate(group_sorted):
            node["x"] = float(x)
            node["y"] = float(start_y + i * dy)


def convert_rows_to_graph(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    used_short_ids: set[str] = set()

    # system identity: (state, effective_sys_utt) => node dict
    system_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    # state -> list[system nodes] (for resolving next state)
    state_index: Dict[str, List[Dict[str, Any]]] = {}
    # special duplicate check: state -> sys_utt
    special_seen: Dict[str, str] = {}

    current_state = None
    current_sys_node: Optional[Dict[str, Any]] = None
    last_sys_utt_in_state = ""
    # rule 6: per-state priority counter (starts 100, then -10 per created user)
    cur_priority = 100

    # pending edges for user->next_state resolve at end
    pending_next: List[Tuple[Dict[str, Any], str]] = []

    def register_node(n: Dict[str, Any]):
        nodes.append(n)

    def new_system_node(state: str, sys_utt: str) -> Dict[str, Any]:
        s = (state or "").strip()
        u = (sys_utt or "").strip()

        # rule 5: duplicate error for special states
        if s in SPECIAL_STATES:
            prev = special_seen.get(s)
            if prev is None:
                special_seen[s] = u
            else:
                if prev != u:
                    raise ValueError(
                        f"Duplicate special state error: {s}\n"
                        f"  previous utterance: {prev!r}\n"
                        f"  current  utterance: {u!r}"
                    )

        key = (s, u)
        if key in system_map:
            return system_map[key]

        node_id = str(uuid.uuid4())
        node = {
            "id": node_id,
            "short_id": gen_short_id(6, used_short_ids),
            "x": 0.0,
            "y": 0.0,
            "text": "システム",
            "type": NODE_TYPE_SYSTEM,
            "node_kind": system_kind_from(s, u),
            "utterance": u,
        }
        system_map[key] = node
        state_index.setdefault(s, []).append(node)
        register_node(node)
        return node

    def new_user_node(priority: int, row: Dict[str, str]) -> Dict[str, Any]:
        node_id = str(uuid.uuid4())
        node = {
            "id": node_id,
            "short_id": gen_short_id(6, used_short_ids),
            "x": 0.0,
            "y": 0.0,
            "text": "ユーザ",
            "type": NODE_TYPE_USER,
            "priority": str(priority),
            "utterance_example": row.get("user utterance example", "").strip(),
            "utterance_type": row.get("user utterance type", "").strip(),
            "condition": row.get("conditions", "").strip(),
            "action": row.get("actions", "").strip(),
        }
        register_node(node)
        return node

    def add_edge(from_node: Dict[str, Any], to_node: Dict[str, Any]):
        edges.append(
            {
                "from": from_node["id"],
                "to": to_node["id"],
                "from_conn": "right",
                "to_conn": "left",
            }
        )

    # ---- sequential processing ----
    for row in rows:
        state = row.get("state", "").strip()
        sys_utt = row.get("system utterance", "").strip()

        # state change -> create/get new current system node
        if current_state != state:
            current_state = state
            last_sys_utt_in_state = ""  # reset utterance inheritance within state block
            cur_priority = 100          # rule 6 reset

        # rule 3: inherit system utterance only when same state block and cell is empty
        if sys_utt == "" and last_sys_utt_in_state != "":
            sys_utt = last_sys_utt_in_state
        elif sys_utt != "":
            last_sys_utt_in_state = sys_utt

        # system node is always created for each row's state (but deduped by (state, utterance))
        current_sys_node = new_system_node(state, sys_utt)

        # rule 2: if system is final, skip user node creation under this system
        if (current_sys_node.get("node_kind", "").strip().lower() == "final"):
            continue

        # if user area is all empty, do not create user node
        if is_user_row_empty(row):
            continue

        # create user node with rule 6 priority
        user_node = new_user_node(cur_priority, row)
        cur_priority -= 10

        # connect system -> user
        add_edge(current_sys_node, user_node)

        # connect user -> next system (resolve later; may appear later)
        next_state = row.get("next state", "").strip()
        if next_state:
            pending_next.append((user_node, next_state))

    # ---- resolve pending next-state edges ----
    def resolve_system_by_state(state: str) -> Dict[str, Any]:
        s = (state or "").strip()
        cands = state_index.get(s, [])
        if not cands:
            # create stub system node (utterance empty)
            return new_system_node(s, "")

        if len(cands) == 1:
            return cands[0]

        # If multiple: prefer exactly one with non-empty utterance, others empty (stubs)
        non_empty = [n for n in cands if (n.get("utterance", "") or "").strip() != ""]
        empty = [n for n in cands if (n.get("utterance", "") or "").strip() == ""]
        if len(non_empty) == 1 and len(empty) >= 1:
            return non_empty[0]

        # ambiguous
        raise ValueError(
            f"Ambiguous next state resolution for state={s!r}. "
            f"Multiple system nodes exist for this state (different system utterance)."
        )

    for user_node, next_state in pending_next:
        target_sys = resolve_system_by_state(next_state)
        add_edge(user_node, target_sys)

    # ---- initial layout (optional but helpful) ----
    apply_simple_layout(nodes, edges)

    return {"nodes": nodes, "edges": edges}


# ------------------------------------------------------------
# GUI用エントリポイント
# ------------------------------------------------------------
def convert_excel_to_json(excel_path: str, json_path: str, sheet: str = "scenario") -> None:
    """
    GUIから直接呼び出すためのAPI。
    Excel→JSON変換を実行する。
    """
    xlsx_path = Path(excel_path)
    out_path = Path(json_path)

    rows = read_excel_rows(xlsx_path, sheet)
    graph = convert_rows_to_graph(rows)

    out_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    # print(f"OK: {out_path.resolve()}  nodes={len(graph['nodes'])} edges={len(graph['edges'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convert scenario.xlsx to state_graph.json")
    ap.add_argument("xlsx", nargs="?", default="scenario.xlsx", help="Input Excel file (default: scenario.xlsx)")
    ap.add_argument("-s", "--sheet", default="scenario", help="Sheet name (default: scenario)")
    ap.add_argument("-o", "--out", default="state_graph.json", help="Output JSON path (default: state_graph.json)")
    args = ap.parse_args()

    convert_excel_to_json(args.xlsx, args.out, args.sheet)
