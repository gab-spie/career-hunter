"""
Example source (template).

Copy this file, rename it, and implement ``fetch()`` to query your own source
(an API, a feed, a public listing...). Return normalized offers as described in
``sources/base.py``. Enable it by adding the module name to ``extra_sources``
in ``config.yaml``.

This example returns static data so the interface can be exercised without any
network call or credentials.
"""

from sources.base import register


@register("example")
class ExampleSource:
    """Minimal source returning a couple of illustrative offers."""

    @staticmethod
    def fetch(profile: str, config: dict) -> list[dict]:
        contrat = "alternance" if profile == "alternance" else "stage"
        return [
            {
                "url": "https://example.org/jobs/1",
                "titre": "Analyste M&A",
                "source": "example",
                "entreprise": "Example Bank",
                "lieu": "Paris",
                "contrat": contrat,
                "date_debut": "2027-09-01",
                "description": "Illustrative offer for the source interface.",
            },
        ]


def fetch(profile: str, config: dict) -> list[dict]:
    """Module-level entry point used by the pipeline (config `extra_sources`)."""
    return ExampleSource.fetch(profile, config)


def describe(offer: dict) -> tuple[str, bool, bool]:
    """Optional hook: full text of one offer -> (text, readable, clean).
    Here the text is already in the offer, so it is returned as is."""
    text = offer.get("description") or ""
    return text, bool(text), True
