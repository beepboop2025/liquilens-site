"""Failure Radar tier publication is paused pending re-validation.

Decided on 2 November 2026, after three co-operative bank failures in the
Indian crisis record were re-dated to their onset. Until the model
re-validates, no surface shows a tier, a tier colour, a grade letter or a
tier count; probabilities are labelled research only; and an absent tier is
never presented as a calm or all-green reading, whatever the API serves.
"""
import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import daily_article  # noqa: E402
import static_social_cards  # noqa: E402
from test_daily_articles import datasets  # noqa: E402

PAUSE = "paused pending re-validation"


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def radar_renderer():
    library = read("evidence-library.js")
    start = library.index("// the failure radar: every licence type on one API-dated board")
    end = library.index("// the Seiche desk panel")
    return library[start:end]


def test_the_radar_renderer_prints_no_tier_grade_or_count():
    radar = radar_renderer()
    for forbidden in ("r.tier", "b.tiers", "TIERS", "toUpperCase()", "r.grade", "'green'"):
        assert forbidden not in radar, forbidden
    assert "tiers paused pending re-validation" in radar
    assert "12-month probabilities are research only" in radar
    assert "return x == null ? 'n/a'" in radar


def test_the_home_radar_section_states_the_pause():
    home = read("index.html")
    section = home[home.index('<section class="band" id="radar">'):home.index("<!-- exposure watch -->")]
    assert "<b>Tiers paused pending re-validation.</b>" in section
    assert "research only" in section
    assert "<th>Tier</th>" not in section
    assert "why is this name orange" not in section
    assert "an absent tier is not a calm reading" in section
    assert "the tier rule is published with the data" not in home


def test_the_home_card_carries_no_tier_count():
    card, og_type, generated = static_social_cards.cards()["/"]
    assert og_type == "website" and generated
    assert PAUSE in card.alt.lower()
    assert not re.search(r"\b(?:red|orange|yellow|green) \d", card.alt, re.I)
    home = read("index.html")
    social = home[home.index(static_social_cards.SOCIAL_START):home.index(static_social_cards.SOCIAL_END)]
    assert not re.search(r"\b(?:red|orange|yellow|green) \d", social, re.I)
    assert not os.path.exists(os.path.join(ROOT, "research", "share-card-board.json"))


def test_the_sample_pack_never_reads_an_india_tier():
    sample = read("access/sample/app.js")
    assert "row.tier" not in sample and "WATCH_TIERS" not in sample
    assert "Quiet is a reading too" not in sample
    assert "India Failure Radar tiers are paused pending re-validation" in sample
    assert "research only" in sample


def test_machine_and_offer_copy_state_the_pause():
    llms = read("llms.txt")
    assert "Failure Radar tiers are paused pending re-validation" in llms
    assert "India tier flips are paused while Failure Radar tiers are re-validated" in llms
    assert "India tier flips are paused" in read("access/index.html")
    assert "India tier flips are paused" in read("about/index.html")


def board_with_tiers():
    data = datasets()
    data["board"]["tiers"] = {"red": 0, "orange": 0, "yellow": 0, "green": 34}
    data["board"]["rows"][0]["tier"] = "green"
    return data


def test_daily_articles_publish_no_tier_while_paused():
    data = board_with_tiers()
    for previous in ([], [{"board_signature": daily_article.board_signature(data["board"]),
                           "topic": "some-other-case"}]):
        article = daily_article.build_article(
            copy.deepcopy(data), date="2026-11-04", recent_index=previous, configured_model=None)
        assert article["quality_gate"]["status"] == "PASS"
        assert daily_article.tier_leaks(article["headline"], article["dek"], article["body_md"]) == []
        assert "34 green" not in article["body_md"] and "0 red" not in article["body_md"]
        assert PAUSE in article["body_md"]
        subject = article["subject"]
        assert "tier" not in subject and "grade" not in subject


def test_a_tier_change_alone_is_not_news_while_paused():
    data = board_with_tiers()
    moved = copy.deepcopy(data)
    moved["board"]["tiers"] = {"red": 0, "orange": 0, "yellow": 2, "green": 32}
    moved["board"]["rows"][0]["tier"] = "yellow"
    assert daily_article.board_signature(data["board"]) == daily_article.board_signature(moved["board"])


def test_the_gate_rejects_model_copy_that_names_tiers():
    article = daily_article.build_article(
        board_with_tiers(), date="2026-11-04", recent_index=[], configured_model=None)
    leaked = dict(article, body_md=article["body_md"] + "\nThe board shows 0 red, 2 yellow and 32 green rows.\n")
    issues = daily_article.quality_issues(leaked)
    assert any("tier publication is paused" in issue for issue in issues)
    assert daily_article.tier_leaks("red flag", "tier one capital", "investment grade a lender") == []


def test_the_writer_and_editor_are_told():
    assert "Failure Radar tier publication is paused pending re-validation" in daily_article.WRITER_SYSTEM
    assert "delete any tier, tier colour, grade letter or tier count" in daily_article.REVIEW_SYSTEM
    dossier_board = daily_article.compact_board(
        daily_article.without_tier_publication(board_with_tiers()["board"]), "none")
    text = json.dumps(dossier_board)
    assert '"tiers"' not in text and '"tier"' not in text and "quadrant_rule" not in json.dumps(
        {k: v for k, v in dossier_board.items() if v is not None})
