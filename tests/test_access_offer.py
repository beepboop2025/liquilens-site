"""Named-list software is the first paid door; the book pilot stays last."""

import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def test_named_list_offer_is_software_and_asks_for_names():
    page = read("access/index.html")
    assert "Send 15 names" in page
    assert "₹3 lakh" in page
    assert "₹75,000" in page
    assert "₹2.5 lakh" in page
    assert "₹12 lakh" in page
    assert "software subscription" in page.lower()
    assert "no customer loan book" in page.lower() or "customer loan book never" in page.lower()
    assert "mailto:mrinal@liquilens.in?subject=LiquiLens%20named-list%20seat" in page
    assert "Fifteen%20names" in page
    assert "Scope my 6-week" not in page
    assert "—" not in page
    assert "–" not in page
    assert 'data-event="email_clicked"' in page
    assert "https://api.liquilens.in/api/events" in read("access/app.js")
    assert "surface: \"access\"" in read("access/app.js")


def test_sample_pack_is_generated_from_public_feeds():
    page = read("access/sample/index.html")
    script = read("access/sample/app.js")
    assert "generated" in page.lower()
    assert "https://api.liquilens.in/api/failure-radar/board" in script
    assert "https://api.liquilens.in/api/failure-radar/review/" in script
    assert "https://api.seiche.info/api/gauge" in script
    assert "innerHTML" in script
    assert "textContent" in script
    assert "—" not in page
    assert "–" not in page


def test_home_and_pilot_point_at_named_list_first():
    home = read("index.html")
    assert 'data-funnel="access_cta_clicked" href="/access/"' in home
    assert "Send 15 counterparties" in home
    assert "₹3 lakh" in home
    pilot = read("pilot/index.html")
    assert 'href="/access/"' in pilot
    assert "Send 15 names instead" in pilot
    assert "Last rung" in pilot


def test_about_keeps_book_pilot_prices_and_adds_the_seat():
    about = read("about/index.html")
    assert "₹3 lakh" in about
    assert "₹2.5 lakh" in about
    assert "₹12 lakh" in about
    assert "/access/" in about
