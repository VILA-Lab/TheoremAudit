#!/usr/bin/env python3
"""Strict proof-obligation dependency validation and scheduling."""

from __future__ import annotations

import re
from collections import deque
from typing import Any, Deque, Dict, List, Mapping, Sequence, Set, Tuple


PROOF_ID_PATTERN = re.compile(r"^PO-[A-Za-z0-9._-]+$")

READY_DRAFTING = {"drafted", "accepted_by_arbiter"}
CONDITIONAL_DRAFTING = {
    "unstarted",
    "planned",
    "partial",
    "conditional_draft",
    "repair_requested",
    "analysis_in_progress",
}
BLOCKING_DRAFTING = {
    "failed",
    "blocked",
    "blocked_by_dependency",
    "rejected_by_arbiter",
}
READY_FINAL = {"accepted_by_arbiter"}
PROOF_STATUSES = (
    READY_DRAFTING | CONDITIONAL_DRAFTING | BLOCKING_DRAFTING
)
SCHEDULABLE_DRAFTING = {
    "unstarted",
    "planned",
    "partial",
    "conditional_draft",
    "repair_requested",
    "blocked_by_dependency",
}


def require_proof_id(value: Any) -> str:
    if not isinstance(value, str) or not PROOF_ID_PATTERN.fullmatch(value):
        raise ValueError(f"invalid proof obligation ID: {value!r}")
    return value


class ProofDAG:
    def __init__(self, obligations: Sequence[Mapping[str, Any]]):
        if not isinstance(obligations, (list, tuple)):
            raise ValueError("proof obligations must be a list")
        self.obligations: Dict[str, Dict[str, Any]] = {}
        self.dependencies: Dict[str, List[str]] = {}
        for position, raw in enumerate(obligations):
            if not isinstance(raw, Mapping):
                raise ValueError(f"proof obligation at position {position} must be an object")
            obligation_id = require_proof_id(raw.get("id"))
            if obligation_id in self.obligations:
                raise ValueError(f"duplicate proof obligation: {obligation_id}")
            dependencies = raw.get("depends_on", [])
            if not isinstance(dependencies, list):
                raise ValueError(f"{obligation_id}.depends_on must be a list")
            normalized_dependencies = [require_proof_id(item) for item in dependencies]
            if len(normalized_dependencies) != len(set(normalized_dependencies)):
                raise ValueError(f"{obligation_id} contains duplicate dependencies")
            self.obligations[obligation_id] = dict(raw)
            self.dependencies[obligation_id] = normalized_dependencies

        self.dependents: Dict[str, List[str]] = {key: [] for key in self.obligations}
        for obligation_id, dependencies in self.dependencies.items():
            for dependency in dependencies:
                if dependency in self.dependents:
                    self.dependents[dependency].append(obligation_id)
        self._validate()

    def _validate(self) -> None:
        unknown = [
            (obligation_id, dependency)
            for obligation_id, dependencies in self.dependencies.items()
            for dependency in dependencies
            if dependency not in self.obligations
        ]
        if unknown:
            raise ValueError(f"proof DAG contains unknown dependencies: {unknown}")

        visiting: Set[str] = set()
        visited: Set[str] = set()
        stack: List[str] = []

        def visit(node: str) -> None:
            if node in visiting:
                start = stack.index(node)
                cycle = stack[start:] + [node]
                raise ValueError(f"proof DAG cycle detected: {' -> '.join(cycle)}")
            if node in visited:
                return
            visiting.add(node)
            stack.append(node)
            for dependency in self.dependencies[node]:
                visit(dependency)
            stack.pop()
            visiting.remove(node)
            visited.add(node)

        for obligation_id in self.obligations:
            visit(obligation_id)

    def _validated_statuses(self, statuses: Mapping[str, str]) -> Dict[str, str]:
        if not isinstance(statuses, Mapping):
            raise ValueError("proof statuses must be an object")
        unknown_ids = sorted(set(statuses) - set(self.obligations))
        if unknown_ids:
            raise ValueError(f"statuses contain unknown proof obligations: {unknown_ids}")
        normalized: Dict[str, str] = {}
        for obligation_id in self.obligations:
            status = statuses.get(obligation_id, "unstarted")
            if status not in PROOF_STATUSES:
                raise ValueError(f"invalid proof status for {obligation_id}: {status}")
            normalized[obligation_id] = status
        return normalized

    def topological_order(self) -> List[str]:
        visited: Set[str] = set()
        order: List[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            for dependency in self.dependencies[node]:
                visit(dependency)
            order.append(node)

        for obligation_id in self.obligations:
            visit(obligation_id)
        return order

    def ancestors(self, obligation_id: str) -> List[str]:
        require_proof_id(obligation_id)
        if obligation_id not in self.obligations:
            raise ValueError(f"unknown proof obligation: {obligation_id}")
        found: Set[str] = set()

        def collect(node: str) -> None:
            for dependency in self.dependencies[node]:
                if dependency not in found:
                    found.add(dependency)
                    collect(dependency)

        collect(obligation_id)
        return [item for item in self.topological_order() if item in found]

    def can_attempt(
        self,
        obligation_id: str,
        statuses: Mapping[str, str],
        mode: str = "drafting",
    ) -> Tuple[bool, str, bool]:
        if obligation_id not in self.obligations:
            raise ValueError(f"unknown proof obligation: {obligation_id}")
        if mode not in {"drafting", "final"}:
            raise ValueError("proof DAG mode must be 'drafting' or 'final'")
        normalized = self._validated_statuses(statuses)
        dependencies = self.ancestors(obligation_id)
        if not dependencies:
            return True, "no dependencies", False

        if mode == "final":
            blocking = [
                (item, normalized[item])
                for item in dependencies
                if normalized[item] not in READY_FINAL
            ]
            if blocking:
                return False, f"transitive final dependencies are not accepted: {blocking}", False
            return True, "all transitive dependencies accepted", False

        hard_blockers = [
            (item, normalized[item])
            for item in dependencies
            if normalized[item] in BLOCKING_DRAFTING
        ]
        if hard_blockers:
            return False, f"blocked by transitive dependencies: {hard_blockers}", False
        conditional = [
            (item, normalized[item])
            for item in dependencies
            if normalized[item] in CONDITIONAL_DRAFTING
        ]
        if conditional:
            return True, f"conditional on unresolved dependencies: {conditional}", True
        return True, "all transitive dependencies ready", False

    def drafting_frontier(self, statuses: Mapping[str, str]) -> Dict[str, Any]:
        normalized = self._validated_statuses(statuses)
        result: Dict[str, Any] = {
            "ready": [],
            "conditional": [],
            "blocked": [],
            "reasons": {},
        }
        for obligation_id in self.topological_order():
            if normalized[obligation_id] not in SCHEDULABLE_DRAFTING:
                continue
            allowed, reason, conditional = self.can_attempt(
                obligation_id, normalized, mode="drafting"
            )
            result["reasons"][obligation_id] = reason
            if not allowed:
                result["blocked"].append(obligation_id)
            elif conditional:
                result["conditional"].append(obligation_id)
            else:
                result["ready"].append(obligation_id)
        return result

    def ready_frontier(self, statuses: Mapping[str, str]) -> List[str]:
        return self.drafting_frontier(statuses)["ready"]

    def conditional_frontier(self, statuses: Mapping[str, str]) -> List[str]:
        return self.drafting_frontier(statuses)["conditional"]

    def downstream(self, obligation_id: str) -> List[str]:
        if obligation_id not in self.obligations:
            raise ValueError(f"unknown proof obligation: {obligation_id}")
        found: List[str] = []
        queue: Deque[str] = deque([obligation_id])
        seen = {obligation_id}
        while queue:
            current = queue.popleft()
            for dependent in self.dependents[current]:
                if dependent not in seen:
                    seen.add(dependent)
                    found.append(dependent)
                    queue.append(dependent)
        return found
