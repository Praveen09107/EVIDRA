"""
EVIDRA — Argument Graph Builder (Tier 5).

Implements CANONICAL_04 spec:
- Assembles CausalGraph: HYPOTHESIS → CLAIM → EVIDENCE
- Computes betweenness centrality for node importance
- Provides navigable structure for UI and downstream reasoning
"""
import json
import logging
from uuid import UUID, uuid4
from collections import defaultdict
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.graph_builder")


def compute_betweenness_centrality(nodes: list[dict], edges: list[dict]) -> dict[str, float]:
    """
    Simplified betweenness centrality for the argument graph.
    Uses adjacency-based path counting.
    """
    node_ids = [n["id"] for n in nodes]
    if len(node_ids) < 2:
        return {nid: 0.5 for nid in node_ids}

    # Build adjacency
    adj = defaultdict(set)
    for e in edges:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])

    centrality = {}
    for node in node_ids:
        # Count how many shortest paths pass through this node
        paths_through = 0
        total_paths = 0

        for s in node_ids:
            if s == node:
                continue
            for t in node_ids:
                if t == node or t == s:
                    continue
                total_paths += 1
                # BFS from s to t
                visited = {s}
                queue = [(s, [s])]
                found_path = False
                while queue and not found_path:
                    current, path = queue.pop(0)
                    for neighbor in adj.get(current, set()):
                        if neighbor == t:
                            if node in path:
                                paths_through += 1
                            found_path = True
                            break
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, path + [neighbor]))

        centrality[node] = round(paths_through / max(total_paths, 1), 4)

    # Normalize to 0-1
    max_c = max(centrality.values()) if centrality else 1
    if max_c > 0:
        centrality = {k: round(v / max_c, 4) for k, v in centrality.items()}

    return centrality


class ArgumentGraphBuilder(BaseAgent):
    agent_id = "graph_builder"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Build the causal/argument graph from claims, relations, and hypotheses."""

        # 1. Fetch claims
        claims = await db.fetch("SELECT * FROM claims WHERE case_id=$1", case_id)
        relations = await db.fetch("SELECT * FROM claim_relations WHERE case_id=$1", case_id)
        hypotheses = await db.fetch(
            "SELECT * FROM hypothesis_history WHERE pipeline_run_id=$1",
            pipeline_run_id,
        )
        hotspots = await db.fetch(
            "SELECT * FROM hotspots WHERE pipeline_run_id=$1",
            pipeline_run_id,
        )

        nodes = []
        edges = []

        # 2. Create HYPOTHESIS nodes
        hyp_node_map = {}
        for hyp in (hypotheses or []):
            node_id = str(uuid4())
            hyp_node_map[hyp["hypothesis_key"]] = node_id
            nodes.append({
                "id": node_id,
                "kind": "HYPOTHESIS",
                "label": hyp["hypothesis_key"],
                "probability": float(hyp["probability"]),
                "importance": 0.0,  # Updated after centrality
                "metadata": {"evidence_summary": hyp.get("evidence_summary", "")},
            })

        # 3. Create CLAIM nodes
        claim_node_map = {}
        for claim in (claims or []):
            cid = str(claim["claim_id"])
            claim_node_map[cid] = cid
            nodes.append({
                "id": cid,
                "kind": "CLAIM",
                "label": claim["text"][:120],
                "probability": None,
                "importance": 0.0,
                "metadata": {
                    "source_agent": claim.get("source_agent", ""),
                    "certainty": float(claim.get("certainty", 0.8)),
                    "claim_type": claim.get("claim_type", "EVENT"),
                },
            })

        # 4. Create EVIDENCE nodes from unique source agents
        evidence_nodes = {}
        for claim in (claims or []):
            source = claim.get("source_agent", "unknown")
            if source not in evidence_nodes:
                eid = str(uuid4())
                evidence_nodes[source] = eid
                nodes.append({
                    "id": eid,
                    "kind": "EVIDENCE",
                    "label": f"Evidence: {source}",
                    "probability": None,
                    "importance": 0.0,
                    "metadata": {"agent_id": source},
                })

        # 5. Create EVIDENCE → CLAIM edges
        for claim in (claims or []):
            source = claim.get("source_agent", "unknown")
            eid = evidence_nodes.get(source)
            cid = str(claim["claim_id"])
            if eid and cid:
                edges.append({
                    "id": str(uuid4()),
                    "source": eid,
                    "target": cid,
                    "relation": "SUPPORTS",
                    "strength": float(claim.get("certainty", 0.8)),
                })

        # 6. Create CLAIM → CLAIM edges (from NLI mapper)
        for rel in (relations or []):
            from_id = str(rel["from_claim_id"])
            to_id = str(rel["to_claim_id"])
            if from_id in claim_node_map and to_id in claim_node_map:
                edges.append({
                    "id": str(uuid4()),
                    "source": from_id,
                    "target": to_id,
                    "relation": rel["relation"],
                    "strength": float(rel.get("confidence", 0.8)),
                })

        # 7. Create CLAIM → HYPOTHESIS edges
        # Connect claims to hypotheses based on content matching
        for claim in (claims or []):
            claim_text = claim["text"].lower()
            cid = str(claim["claim_id"])

            for hyp_key, hyp_nid in hyp_node_map.items():
                # Keyword heuristic for hypothesis linkage
                strength = 0.0
                direction = "NEUTRAL"

                if hyp_key == "HOMICIDE":
                    if any(kw in claim_text for kw in ["defensive wound", "homicide", "murder", "stab", "blunt force", "ligature"]):
                        strength = 0.7
                        direction = "SUPPORTS"
                elif hyp_key == "SUICIDE":
                    if any(kw in claim_text for kw in ["suicide", "self-inflicted", "hesitation", "overdose"]):
                        strength = 0.7
                        direction = "SUPPORTS"
                elif hyp_key == "NATURAL":
                    if any(kw in claim_text for kw in ["natural", "cardiac", "disease", "infarction"]):
                        strength = 0.7
                        direction = "SUPPORTS"
                elif hyp_key == "ACCIDENT":
                    if any(kw in claim_text for kw in ["accident", "fall", "intoxication"]):
                        strength = 0.7
                        direction = "SUPPORTS"

                if strength > 0:
                    edges.append({
                        "id": str(uuid4()),
                        "source": cid,
                        "target": hyp_nid,
                        "relation": direction,
                        "strength": strength,
                    })

        # 8. Compute betweenness centrality
        centrality = compute_betweenness_centrality(nodes, edges)
        for node in nodes:
            node["importance"] = centrality.get(node["id"], 0.0)

        # 9. Save graph to DB
        await db.execute(
            """
            INSERT INTO causal_graphs (case_id, pipeline_run_id, graph_data)
            VALUES ($1, $2, $3)
            ON CONFLICT (case_id, pipeline_run_id) DO UPDATE SET graph_data=$3
            """,
            case_id, pipeline_run_id,
            json.dumps({"nodes": nodes, "edges": edges}, default=str),
        )

        await self.log_step(
            "RULE",
            "Argument Graph Construction",
            f"Built graph: {len(nodes)} nodes, {len(edges)} edges. "
            f"Hypotheses: {len(hyp_node_map)}, Claims: {len(claim_node_map)}, Evidence: {len(evidence_nodes)}",
            confidence=0.90,
        )

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "hypothesis_nodes": len(hyp_node_map),
            "claim_nodes": len(claim_node_map),
            "evidence_nodes": len(evidence_nodes),
            "_confidence": 0.90,
        }
