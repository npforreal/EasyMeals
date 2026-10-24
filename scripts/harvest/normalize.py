"""Name normalisation used to decide whether two items are the same."""

import re
import unicodedata
from collections.abc import Iterable

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    """Lowercase, strip diacritics (incl. đ), collapse punctuation/whitespace to single spaces."""
    text = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def _singular(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("oes"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def match_keys(name: str, aliases: Iterable[str] = ()) -> set[str]:
    """Every key under which an item can be recognised: name and aliases, each in its
    normalised form and with a light English plural fold on the last word
    ("Red Onions" == "red onion"). Two items are the same when their key sets intersect."""
    keys: set[str] = set()
    for raw in (name, *aliases):
        norm = normalize(raw)
        if not norm:
            continue
        keys.add(norm)
        head, _, last = norm.rpartition(" ")
        keys.add(f"{head} {_singular(last)}".strip())
    return keys
