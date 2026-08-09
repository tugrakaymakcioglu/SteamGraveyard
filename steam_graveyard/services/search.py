"""Cached AppID, text, and typo-tolerant game search."""

from __future__ import annotations

from rapidfuzz.fuzz import WRatio

from steam_graveyard.database.repository import GameRepository, SearchRecord
from steam_graveyard.models import Game


class SearchService:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository
        self._corpus: list[SearchRecord] | None = None
        self._cache: dict[str, list[int]] = {}

    def invalidate(self) -> None:
        self._corpus = None
        self._cache.clear()

    def search(self, query: str, *, limit: int = 50, offset: int = 0) -> list[Game]:
        normalized = " ".join(query.casefold().split())
        if not normalized:
            return []
        appids = self._cache.get(normalized)
        if appids is None:
            appids = self._rank(normalized)
            if len(self._cache) >= 32:
                self._cache.pop(next(iter(self._cache)))
            self._cache[normalized] = appids
        return self.repository.get_games_by_appids(appids[offset : offset + limit])

    def _rank(self, query: str) -> list[int]:
        if self._corpus is None:
            self._corpus = self.repository.search_corpus()
        fts_matches = set(self.repository.search_fts_appids(query))
        numeric = int(query) if query.isascii() and query.isdigit() else None
        ranked: list[tuple[float, int]] = []
        for record in self._corpus:
            if numeric == record.appid:
                ranked.append((1000.0, record.appid))
                continue
            candidates = (record.name, *record.aliases)
            folded = [candidate.casefold() for candidate in candidates]
            substring = max(
                (120.0 - value.index(query) for value in folded if query in value),
                default=0.0,
            )
            fuzzy = max(WRatio(query, value) for value in folded)
            score = max(substring, fuzzy) + (15.0 if record.appid in fts_matches else 0.0)
            if score >= 60:
                ranked.append((score, record.appid))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [appid for _, appid in ranked]
