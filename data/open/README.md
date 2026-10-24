# data/open

Ingredients and recipes harvested by `python -m scripts.harvest` from open APIs.

- `ingredients.jsonl`, `recipes.jsonl`: one JSON object per line, append-only. Every record carries `source`, `source_id`, `license` and `fetched_at`.
- Items already in this dataset or in the app seed data are not written again (match on normalised name and aliases).
- Content is in the source's language (currently English, `language: "en"`); it is **not** translated, so it will not match the Vietnamese seed names. Translate/alias before importing into the app.
- Check each source's terms before commercial use (TheMealDB's free key is for development/education).
