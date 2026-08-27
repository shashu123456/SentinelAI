"""Knowledge Graph — models relationships between vulnerabilities, endpoints, and attack paths.

Used by the AI engine to explain attack chains and root causes.
"""

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str  # finding, endpoint, cwe, owasp, user, data
    label: str
    properties: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relationship: str  # affects, leads_to, requires, exposes, depends_on
    properties: dict = field(default_factory=dict)


class VulnerabilityKnowledgeGraph:
    """Builds and queries a knowledge graph of vulnerability relationships."""

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []

    def build_from_findings(self, findings: list[dict]) -> None:
        """Build the knowledge graph from a list of findings."""
        self.nodes.clear()
        self.edges.clear()

        for finding in findings:
            fid = f"finding_{finding.get('id', 'unknown')}"
            cwe_id = finding.get("cwe_id", "unknown")
            owasp = finding.get("owasp_category", "unknown")
            endpoint = finding.get("affected_endpoint", "unknown")

            # Add finding node
            self.nodes[fid] = GraphNode(
                id=fid,
                type="finding",
                label=finding.get("vulnerability_name", "Unknown"),
                properties={
                    "severity": finding.get("severity", "Unknown"),
                    "cwe_id": cwe_id,
                    "owasp": owasp,
                },
            )

            # Add CWE node
            cwe_node_id = f"cwe_{cwe_id}"
            if cwe_node_id not in self.nodes:
                self.nodes[cwe_node_id] = GraphNode(
                    id=cwe_node_id,
                    type="cwe",
                    label=cwe_id,
                    properties={},
                )
            self.edges.append(GraphEdge(source=fid, target=cwe_node_id, relationship="classified_as"))

            # Add OWASP node
            owasp_node_id = f"owasp_{owasp}"
            if owasp_node_id not in self.nodes:
                self.nodes[owasp_node_id] = GraphNode(
                    id=owasp_node_id,
                    type="owasp",
                    label=owasp,
                    properties={},
                )
            self.edges.append(GraphEdge(source=fid, target=owasp_node_id, relationship="in_category"))

            # Add endpoint node
            if endpoint and endpoint != "unknown":
                ep_node_id = f"endpoint_{endpoint}"
                if ep_node_id not in self.nodes:
                    self.nodes[ep_node_id] = GraphNode(
                        id=ep_node_id,
                        type="endpoint",
                        label=endpoint,
                        properties={},
                    )
                self.edges.append(GraphEdge(source=fid, target=ep_node_id, relationship="affects"))

        # Build cross-finding relationships
        self._build_attack_chains(findings)

    def _build_attack_chains(self, findings: list[dict]) -> None:
        """Identify potential attack chains between findings."""
        auth_findings = [f for f in findings if any(
            w in f.get("vulnerability_name", "").lower()
            for w in ["auth", "authentication", "session", "token"]
        )]
        injection_findings = [f for f in findings if any(
            w in f.get("vulnerability_name", "").lower()
            for w in ["injection", "sql", "xss", "command"]
        )]
        access_findings = [f for f in findings if any(
            w in f.get("vulnerability_name", "").lower()
            for w in ["bola", "idor", "access", "authorization", "broken object"]
        )]

        # Auth bypass → Injection → Data access chain
        for auth_f in auth_findings:
            for inj_f in injection_findings:
                auth_id = f"finding_{auth_f.get('id', 'unknown')}"
                inj_id = f"finding_{inj_f.get('id', 'unknown')}"
                self.edges.append(GraphEdge(
                    source=auth_id,
                    target=inj_id,
                    relationship="enables",
                    properties={"chain_step": "authentication_bypass_enables_injection"},
                ))

        for inj_f in injection_findings:
            for acc_f in access_findings:
                inj_id = f"finding_{inj_f.get('id', 'unknown')}"
                acc_id = f"finding_{acc_f.get('id', 'unknown')}"
                self.edges.append(GraphEdge(
                    source=inj_id,
                    target=acc_id,
                    relationship="escalates_to",
                    properties={"chain_step": "injection_enables_privilege_escalation"},
                ))

    def get_attack_paths(self) -> list[dict]:
        """Find all attack paths (chains of related findings)."""
        chains = []
        chain_edges = [e for e in self.edges if e.relationship in ("enables", "escalates_to")]

        # Group by connected components
        visited = set()
        for edge in chain_edges:
            if edge.source not in visited:
                chain = self._trace_chain(edge.source)
                if len(chain) > 1:
                    chains.append({
                        "path_length": len(chain),
                        "nodes": chain,
                        "description": self._describe_chain(chain),
                    })
                    visited.update(n["id"] for n in chain)

        return chains

    def _trace_chain(self, start_id: str) -> list[dict]:
        """Trace an attack chain from a starting node."""
        path = []
        current = start_id
        visited = set()

        while current and current not in visited:
            visited.add(current)
            node = self.nodes.get(current)
            if node:
                path.append({"id": node.id, "type": node.type, "label": node.label})

            # Find next node in chain
            next_edge = None
            for edge in self.edges:
                if edge.source == current and edge.relationship in ("enables", "escalates_to"):
                    next_edge = edge
                    break

            current = next_edge.target if next_edge else None

        return path

    def _describe_chain(self, chain: list[dict]) -> str:
        """Generate a human-readable description of an attack chain."""
        if len(chain) < 2:
            return ""

        steps = []
        for i, node in enumerate(chain):
            if node["type"] == "finding":
                steps.append(f"Step {i+1}: Exploit '{node['label']}'")
            elif node["type"] == "endpoint":
                steps.append(f"  via endpoint: {node['label']}")

        return " → ".join(steps) if steps else ""

    def get_related_findings(self, finding_id: str) -> list[dict]:
        """Get findings related to a specific finding through the graph."""
        related = set()
        for edge in self.edges:
            if edge.source == finding_id:
                related.add(edge.target)
            elif edge.target == finding_id:
                related.add(edge.source)

        results = []
        for node_id in related:
            node = self.nodes.get(node_id)
            if node and node.type == "finding":
                results.append({
                    "id": node.id,
                    "label": node.label,
                    "severity": node.properties.get("severity", "Unknown"),
                })

        return results

    def to_dict(self) -> dict:
        """Serialize the graph for API responses."""
        return {
            "nodes": [
                {"id": n.id, "type": n.type, "label": n.label, "properties": n.properties}
                for n in self.nodes.values()
            ],
            "edges": [
                {"source": e.source, "target": e.target, "relationship": e.relationship}
                for e in self.edges
            ],
        }


_graph = None


def get_knowledge_graph() -> VulnerabilityKnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = VulnerabilityKnowledgeGraph()
    return _graph
