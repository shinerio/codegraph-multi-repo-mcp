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
