"""Command line entry: ``python -m scripts.harvest``."""

import argparse
import sys
from collections.abc import Sequence
from itertools import islice
from pathlib import Path

from .http import JsonClient
from .store import DatasetStore, load_app_baseline
from .themealdb import TheMealDB, ingredient_record
from .vietnam import VietnameseSource

DEFAULT_DATA_DIR = Path("data/open")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scripts.harvest",
        description="Fetch ingredients and recipes from open sources and save only new items.",
    )
    p.add_argument("--source", choices=["themealdb", "vietnam", "all"], default="all")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--what", choices=["all", "ingredients", "recipes"], default="all")
    p.add_argument("--limit", type=int, default=None, help="max items fetched per kind")
    p.add_argument("--api-key", default="1", help="TheMealDB key (default: public test key)")
    p.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    p.add_argument("--cache-dir", type=Path, default=None, help="cache raw API responses")
    p.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    p.add_argument(
        "--no-app-baseline",
        action="store_true",
        help="do not treat the app's seed data as already known",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="list skipped duplicates")
    return p


def run(
    args: argparse.Namespace,
    get_json=None,
    out=print,
) -> DatasetStore:
    store = DatasetStore(args.data_dir, dry_run=args.dry_run)
    if not args.no_app_baseline:
        ingredients, recipes = load_app_baseline()
        store.add_baseline(ingredients, recipes)

    client = get_json or JsonClient(delay=args.delay, cache_dir=args.cache_dir).get_json
    sources = []
    if args.source in ("vietnam", "all"):
        sources.append(VietnameseSource(data_dir=args.data_dir))
    if args.source in ("themealdb", "all"):
        sources.append(TheMealDB(client, api_key=args.api_key))

    def log_dup(kind: str, name: str, origin: str) -> None:
        if args.verbose:
            out(f"  skip {kind}: {name!r} (already in {origin})")

    for src in sources:
        if args.what in ("all", "ingredients"):
            for record in islice(src.ingredients(), args.limit):
                origin = store.add_ingredient(record)
                if origin:
                    log_dup("ingredient", record["name"], origin)

        if args.what in ("all", "recipes"):
            for record in islice(src.meals(), args.limit):
                origin = store.add_recipe(record)
                if origin:
                    log_dup("recipe", record["name"], origin)
                    continue
                # Ingredients used by a new recipe belong in the ingredient dataset too.
                for ing in record.get("ingredients", []):
                    origin = store.add_ingredient(ingredient_record(ing["name"]))
                    if origin:
                        log_dup("ingredient", ing["name"], origin)

    out(store.ingredient_stats.line("ingredients"))
    out(store.recipe_stats.line("recipes"))
    if args.dry_run:
        out("dry run: nothing was written")
    else:
        out(f"data directory: {args.data_dir}")
    return store


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
