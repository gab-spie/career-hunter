from sources import base
import sources.example_source as example


def test_example_returns_valid_offers():
    offers = example.fetch("alternance", {})
    assert offers
    assert all(base.is_valid_offer(o) for o in offers)


def test_example_is_registered():
    assert "example" in base.available()


def test_invalid_offer_detected():
    assert not base.is_valid_offer({"titre": "no url"})
    assert not base.is_valid_offer({"url": "x"})  # no title
