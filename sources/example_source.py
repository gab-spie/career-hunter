"""
Example source (template).

Copy this file, rename it, and implement ``fetch()`` to query your own source
(an API, a feed, a public listing...). Return normalized offers as described in
``sources/base.py``. Enable it by adding the module name to ``sources_extra``
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
    """Module-level entry point used by the pipeline (config `sources_extra`)."""
    return ExampleSource.fetch(profile, config)
