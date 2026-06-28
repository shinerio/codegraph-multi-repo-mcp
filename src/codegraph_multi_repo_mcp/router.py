from __future__ import annotations

import re
from dataclasses import dataclass

from .models import RepoConfig


TOKEN_RE = re.compile(r"[A-Za-z0-9_.:/-]+")


@dataclass(frozen=True)
class RepoCandidate:
    repo: RepoConfig
    score: int
    reason: str


def tokenize(value: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(value)}


class RepoRouter:
    def __init__(self, repos: list[RepoConfig]) -> None:
        self.repos = repos

    def route(self, query: str, max_repos: int) -> list[RepoCandidate]:
        query_lower = query.lower()
        query_tokens = tokenize(query)
        candidates = [self._score(repo, query_lower, query_tokens) for repo in self.repos]
        candidates.sort(key=lambda item: (-item.score, self.repos.index(item.repo)))
        return candidates[:max_repos]

    def _score(self, repo: RepoConfig, query_lower: str, query_tokens: set[str]) -> RepoCandidate:
        score = 0
        reasons: list[str] = []

        if repo.name.lower() in query_lower:
            score += 100
            reasons.append(f"name:{repo.name}")

        for alias in repo.aliases:
            if alias.lower() in query_lower:
                score += 80
                reasons.append(f"alias:{alias}")

        for tag in repo.tags:
            if tag.lower() in query_tokens:
                score += 25
                reasons.append(f"tag:{tag}")

        if repo.language and repo.language.lower() in query_tokens:
            score += 40
            reasons.append(f"language:{repo.language}")

        for component in repo.components:
            coordinate = self._component_coordinate(component.group_id, component.artifact_id)
            if coordinate and coordinate.lower() in query_lower:
                score += 120
                reasons.append(f"component:{coordinate}")
            if component.artifact_id and component.artifact_id.lower() in query_lower:
                score += 90
                reasons.append(f"artifact:{component.artifact_id}")
            if component.group_id and component.group_id.lower() in query_lower:
                score += 60
                reasons.append(f"group:{component.group_id}")

        description_tokens = tokenize(repo.description)
        desc_matches = sorted(query_tokens & description_tokens)
        if desc_matches:
            score += 10 * len(desc_matches)
            reasons.append("description:" + ",".join(desc_matches))

        path_tokens = tokenize(str(repo.path))
        path_matches = sorted(query_tokens & path_tokens)
        if path_matches:
            score += 5 * len(path_matches)
            reasons.append("path:" + ",".join(path_matches))

        reason = "; ".join(reasons) if reasons else "fallback:config-order"
        return RepoCandidate(repo=repo, score=score, reason=reason)

    def _component_coordinate(self, group_id: str, artifact_id: str) -> str:
        if not group_id or not artifact_id:
            return ""
        return f"{group_id}:{artifact_id}"
