"""Finding clustering by unique defect signature (Prompt 9).

Cluster key = oracle class + signature kind + normalized endpoint + status + error_type + message_norm.
Deduplicates multiple finds of the same underlying defect into a single cluster,
keeping the minimal reproduction trace and counting occurrences.
"""

from __future__ import annotations

from dataclasses import dataclass

from proofqa.contracts import Finding


@dataclass
class ClusteredFinding:
    """Clustered finding grouping occurrences of the same defect signature."""

    finding: Finding
    cluster_key: str
    occurrences: int = 1
    minimal_trace_length: int = 0


def compute_cluster_key(finding: Finding) -> str:
    """Computes deterministic cluster key from oracle class and failure signature."""
    sig = finding.signature
    parts = [
        finding.oracle_class.value,
        sig.kind or "",
        sig.first_party_endpoint or "",
        str(sig.status) if sig.status is not None else "",
        sig.error_type or "",
        sig.message_norm or "",
    ]
    return ":".join(parts)


def cluster_findings(findings: list[Finding]) -> list[ClusteredFinding]:
    """Clusters findings by failure signature, retaining the minimal reproduction trace."""
    clusters: dict[str, ClusteredFinding] = {}

    for f in findings:
        ckey = compute_cluster_key(f)
        trace_len = len(f.steps)
        if ckey not in clusters:
            clusters[ckey] = ClusteredFinding(
                finding=f,
                cluster_key=ckey,
                occurrences=1,
                minimal_trace_length=trace_len,
            )
        else:
            existing = clusters[ckey]
            existing.occurrences += 1
            # Keep finding with shorter trace (or higher confidence if tied)
            if trace_len < existing.minimal_trace_length or (
                trace_len == existing.minimal_trace_length and f.confidence > existing.finding.confidence
            ):
                existing.finding = f
                existing.minimal_trace_length = trace_len

    return list(clusters.values())
