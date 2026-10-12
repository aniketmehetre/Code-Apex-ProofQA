"""NetworkX state graph persisted in SQLite with frontier management."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import networkx as nx

from proofqa.contracts import Action, StateFingerprint


class StateGraph:
    """Directed state graph keyed by StateFingerprint, persisting nodes and transitions."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.graph = nx.DiGraph()
        self.db_path = Path(db_path) if db_path else None
        self.root_id: str | None = None

        if self.db_path:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        if not self.db_path:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS states (
                    id TEXT PRIMARY KEY,
                    url_path TEXT,
                    simhash TEXT,
                    aria_hash TEXT,
                    control_count INTEGER,
                    depth INTEGER,
                    visit_count INTEGER,
                    candidate_actions TEXT,
                    tried_actions TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT,
                    target_id TEXT,
                    action_json TEXT,
                    step INTEGER
                )
                """
            )
            conn.commit()

    @staticmethod
    def get_state_id(fp: StateFingerprint) -> str:
        return f"{fp.url_path}:{fp.simhash}"

    def add_state(
        self,
        fp: StateFingerprint,
        candidate_actions: list[Action],
        depth: int = 0,
    ) -> str:
        """Adds or updates a page state in the graph."""
        state_id = self.get_state_id(fp)
        if self.root_id is None:
            self.root_id = state_id

        if state_id not in self.graph:
            self.graph.add_node(
                state_id,
                fingerprint=fp,
                url_path=fp.url_path,
                depth=depth,
                visit_count=1,
                candidate_actions={a.id: a for a in candidate_actions},
                tried_actions=set(),
            )
        else:
            node = self.graph.nodes[state_id]
            node["visit_count"] += 1
            # Merge candidate actions
            for a in candidate_actions:
                if a.id not in node["candidate_actions"]:
                    node["candidate_actions"][a.id] = a

        if self.db_path:
            self._persist_state(state_id)

        return state_id

    def record_transition(
        self,
        source_id: str,
        action: Action,
        target_id: str,
        step: int,
    ) -> None:
        """Records an action transition edge between two states."""
        self.mark_action_tried(source_id, action.id)
        self.graph.add_edge(source_id, target_id, action=action, step=step)

        if self.db_path:
            self._persist_transition(source_id, target_id, action, step)

    def mark_action_tried(self, state_id: str, action_id: str) -> None:
        if state_id in self.graph:
            self.graph.nodes[state_id]["tried_actions"].add(action_id)
            if self.db_path:
                self._persist_state(state_id)

    def get_untried_actions(self, state_id: str) -> list[Action]:
        if state_id not in self.graph:
            return []
        node = self.graph.nodes[state_id]
        tried = node["tried_actions"]
        return [a for a_id, a in node["candidate_actions"].items() if a_id not in tried]

    def find_nearest_state_with_untried(self, current_id: str) -> str | None:
        """Finds the nearest state in the graph that has untried candidate actions."""
        # Find all candidate target states with untried actions
        targets = [
            n for n in self.graph.nodes
            if len(self.get_untried_actions(n)) > 0 and n != current_id
        ]
        if not targets:
            return None

        # Check shortest path from current_id
        best_target = None
        best_dist = float("inf")
        for target in targets:
            try:
                dist = nx.shortest_path_length(self.graph, current_id, target)
                if dist < best_dist:
                    best_dist = dist
                    best_target = target
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        if best_target:
            return best_target

        # If not reachable from current, pick nearest from root
        if self.root_id:
            for target in targets:
                try:
                    dist = nx.shortest_path_length(self.graph, self.root_id, target)
                    if dist < best_dist:
                        best_dist = dist
                        best_target = target
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass

        return best_target or (targets[0] if targets else None)

    def path_from_root(self, target_id: str) -> list[Action]:
        """Returns the shortest path of Actions from the root state to target state."""
        if not self.root_id or self.root_id == target_id:
            return []
        try:
            nodes = nx.shortest_path(self.graph, self.root_id, target_id)
            actions: list[Action] = []
            for u, v in zip(nodes[:-1], nodes[1:], strict=True):
                edge_data = self.graph.get_edge_data(u, v)
                if edge_data and "action" in edge_data:
                    actions.append(edge_data["action"])
            return actions
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def coverage_summary(self) -> dict[str, Any]:
        """Computes current structural exploration coverage metrics."""
        distinct_urls = set(
            self.graph.nodes[n]["url_path"] for n in self.graph.nodes if "url_path" in self.graph.nodes[n]
        )
        total_actions = sum(len(self.graph.nodes[n].get("candidate_actions", {})) for n in self.graph.nodes)
        tried_actions = sum(len(self.graph.nodes[n].get("tried_actions", set())) for n in self.graph.nodes)

        return {
            "states_count": len(self.graph.nodes),
            "edges_count": len(self.graph.edges),
            "distinct_urls_count": len(distinct_urls),
            "distinct_urls": sorted(distinct_urls),
            "total_candidate_actions": total_actions,
            "tried_actions": tried_actions,
        }

    def _persist_state(self, state_id: str) -> None:
        if not self.db_path:
            return
        node = self.graph.nodes[state_id]
        fp: StateFingerprint = node["fingerprint"]
        cand_json = json.dumps([a.model_dump() for a in node["candidate_actions"].values()])
        tried_json = json.dumps(list(node["tried_actions"]))

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO states
                (id, url_path, simhash, aria_hash, control_count, depth, visit_count, candidate_actions, tried_actions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    fp.url_path,
                    fp.simhash,
                    fp.aria_hash,
                    fp.control_count,
                    node["depth"],
                    node["visit_count"],
                    cand_json,
                    tried_json,
                ),
            )
            conn.commit()

    def _persist_transition(
        self,
        source_id: str,
        target_id: str,
        action: Action,
        step: int,
    ) -> None:
        if not self.db_path:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO transitions (source_id, target_id, action_json, step)
                VALUES (?, ?, ?, ?)
                """,
                (source_id, target_id, json.dumps(action.model_dump()), step),
            )
            conn.commit()
