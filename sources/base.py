"""
Source interface.

A "source" is any module that exposes a ``fetch(profile, config)`` function
returning a list of **normalized offers**. That single contract is all the
pipeline needs: filters, scoring, deduplication, delivery and tracking are the
same for every source.

Normalized offer (a plain dict):

    {
        "url":           str,   # unique key, used for deduplication (required)
        "titre":         str,   # job title (required)
        "source":        str,   # source name, e.g. "official_api"
        "entreprise":    str | None,   # company
        "lieu":          str | None,   # location
        "contrat":       str | None,   # contract type
        "date_debut":    str | None,   # ISO start date if known
        "description":   str,          # may be empty
        # optional, used by richer sources to sharpen filtering:
        "contrat_label": str | None,   # raw contract label from the source
        "diplome_eu":    int | None,   # European degree level (5/6/7)
    }

Field names keep the author's French naming (see the README language note).

Optional hook: a source may also expose ``describe(offer)`` returning
``(text, readable, clean)`` with the full text of one offer. The pipeline
calls it only for NEW offers when ``read_full_offers`` is on for the profile,
so the start date ("from March 2027") is found even when the title is silent.
``clean`` is True when the text is the offer alone (then it also feeds the
score); a whole web page (menus included) is used for the date only.
``readable`` False flags the offer "start date to check" instead of dropping it.

To add a source: create a module with a ``fetch`` function matching
``Source`` below, then enable it in ``config.yaml`` under ``extra_sources``.
See ``sources/example_source.py`` for a template. Concrete connectors (such as
``src/source_lba.py``, which calls an official public API) implement this exact
contract.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Source(Protocol):
    def fetch(self, profile: str, config: dict) -> list[dict]:
        """Return normalized offers for the given profile."""
        ...


# Optional lightweight registry, handy for discovery/tests.
_REGISTRY: dict[str, "Source"] = {}


def register(name: str):
    """Decorator to register a source module/object under a name."""
    def deco(obj):
        _REGISTRY[name] = obj
        return obj
    return deco


def available() -> list[str]:
    return sorted(_REGISTRY)


def get(name: str):
    return _REGISTRY[name]


def is_valid_offer(offer: dict) -> bool:
    """A usable offer has at least a URL (dedup key) and a title."""
    return bool(offer.get("url")) and bool(offer.get("titre"))
