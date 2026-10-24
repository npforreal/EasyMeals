"""JSONL dataset with duplicate detection.

Two files live in the data directory: ``ingredients.jsonl`` and ``recipes.jsonl``. An item is a
duplicate when any of its match keys (see ``normalize.match_keys``) is already known, either from
the files themselves, from the baseline (e.g. the app's seed data), or from an item accepted
earlier in the same run. Duplicates are never written.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import match_keys


@dataclass
class Stats:
    seen: int = 0
    added: int = 0
    duplicates: int = 0

    def line(self, label: str) -> str:
        return f"{label}: {self.seen} seen, {self.added} new, {self.duplicates} duplicate"


class _Index:
    """Maps a match key to a label saying where the item came from."""

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def find(self, keys: set[str]) -> str | None:
        for key in keys:
            if key in self._keys:
                return self._keys[key]
        return None

    def add(self, keys: set[str], origin: str) -> None:
        for key in keys:
            self._keys.setdefault(key, origin)


@dataclass
class DatasetStore:
    data_dir: Path
    dry_run: bool = False
    ingredient_stats: Stats = field(default_factory=Stats)
    recipe_stats: Stats = field(default_factory=Stats)

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self._ingredients = _Index()
        self._recipes = _Index()
        for record in self._read("ingredients.jsonl"):
            self._ingredients.add(match_keys(record["name"], record.get("aliases", [])), "dataset")
        for record in self._read("recipes.jsonl"):
            self._recipes.add(match_keys(record["name"], record.get("aliases", [])), "dataset")

    def add_baseline(
        self,
        ingredients: Iterable[tuple[str, list[str]]] = (),
        recipes: Iterable[str] = (),
    ) -> None:
        """Register items that already exist elsewhere (e.g. app seed) so they are skipped."""
        for name, aliases in ingredients:
            self._ingredients.add(match_keys(name, aliases), "baseline")
        for name in recipes:
            self._recipes.add(match_keys(name), "baseline")

    def add_ingredient(self, record: dict) -> str | None:
        """Save the ingredient unless known. Returns the origin of the match, or None if saved."""
        return self._add(record, self._ingredients, "ingredients.jsonl", self.ingredient_stats)

    def add_recipe(self, record: dict) -> str | None:
        return self._add(record, self._recipes, "recipes.jsonl", self.recipe_stats)

    def _add(self, record: dict, index: _Index, filename: str, stats: Stats) -> str | None:
        stats.seen += 1
        keys = match_keys(record["name"], record.get("aliases", []))
        if not keys:
            stats.duplicates += 1
            return "empty-name"
        origin = index.find(keys)
        if origin is not None:
            stats.duplicates += 1
            return origin
        index.add(keys, "run")
        stats.added += 1
        if not self.dry_run:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with (self.data_dir / filename).open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return None

    def _read(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        records = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON ({exc.msg})") from exc
        return records


def load_app_baseline() -> tuple[list[tuple[str, list[str]]], list[str]]:
    """Names already present in the app's seed data. Empty if the app cannot be imported."""
    try:
        from app.storage.repository import InMemoryRepository

        repo = InMemoryRepository()
        ingredients = [(i.name, list(i.aliases)) for i in repo._ingredients.values()]
        recipes = [r.name for r in repo._recipes.values()]
        return ingredients, recipes
    except Exception:  # baseline is best effort; the dataset files still dedupe
        return [], []
