"""Dated articles keep what they published and carry a dated note.

When LiquiLens re-dated three co-operative bank failures to their onset, the
India figures that 35 daily articles quoted changed. Those articles are dated
publications: their text stays as published, a short dated correction at the
top says what changed and why, and the six that stated a licence-cancellation
date as the default date are corrected in place with the note saying so. Every
other article that shows Failure Radar tier states gets a dated update saying
tiers are paused. Notes live in the article Markdown, so the page, the .md file
and the feeds carry them and a daily surface refresh keeps them.
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import article_corrections as corrections  # noqa: E402
import daily_article  # noqa: E402
import social_cards  # noqa: E402

ARTICLES = os.path.join(ROOT, "articles")
SIX = {
    "2026-09-01-rupee-co-operative-bank-replay-the-signal-was-an-evidence-boundary-not-a-cle",
    "2026-09-13-madhavpura-s-replay-shows-where-a-balance-sheet-radar-can-go-blind",
    "2026-09-24-rupee-co-operative-bank-replay-shows-where-a-balance-sheet-warning-ends",
    "2026-10-05-ckp-co-operative-bank-replay-when-a-missing-warning-is-not-an-all-clear",
    "2026-10-06-rupee-co-operative-bank-the-warning-was-a-blank-record-not-an-early-signal",
    "2026-10-17-madhavpura-replay-the-warning-a-disclosure-screen-could-not-honestly-give",
}


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def registry(note_id=corrections.CORRECTION_ID):
    return json.loads(read("articles", "corrections", f"{note_id}.json"))


def corrected_slugs():
    return [row["slug"] for row in registry()["articles"]]


def updated_slugs():
    return [row["slug"] for row in registry(corrections.UPDATE_ID)["articles"]]


def test_every_note_and_corrected_fact_matches_the_registry():
    assert corrections.run(check=True) == []


def test_the_registry_froze_the_regenerated_record_from_the_capture():
    record = registry()
    raw = open(corrections.CAPTURE, "rb").read()
    evidence = json.loads(raw)
    if hashlib.sha256(raw).hexdigest() != record["record"]["capture_sha256"]:
        return  # a later capture; the dated notes stay as published
    summary, ex = evidence["summary"], evidence["uncertainty"]["recall_ex_fraud"]
    assert record["record"]["recall_ex_fraud_pct"] == summary["recall_ex_fraud_pct"]
    assert record["record"]["median_lead_months"] == summary["median_lead_months"]
    assert (record["record"]["flagged_ex_fraud"], record["record"]["failed_ex_fraud"]) == (ex["k"], ex["n"])
    served = {row["slug"]: row["default_date"] for row in evidence["institutions"]}
    for onset in record["onsets"]:
        assert served[onset["slug"]] == onset["onset_date"] != onset["previous_date"]
        assert onset["source_url"].startswith("https://www.rbi.org.in/")


def test_every_article_gets_the_note_its_text_calls_for():
    listed, updated = set(corrected_slugs()), set(updated_slugs())
    assert len(listed) == 35 and SIX <= listed and not listed & updated
    for name in sorted(os.listdir(ARTICLES)):
        if not name.endswith(".md") or not name.startswith("2026-"):
            continue
        slug = name[:-3]
        body = read("articles", name)
        text = body.split("\n\n", 1)[1] if body.startswith(corrections.NOTE_LEADS) else body
        quotes_old = bool(corrections.CITES_RECALL.search(text) or corrections.CITES_LEAD.search(text))
        assert (quotes_old or slug in SIX) == (slug in listed), slug
        assert body.startswith(corrections.NOTE_LEAD) == (slug in listed), slug
        shows_tiers = bool(corrections.MENTIONS_TIERS.search(text))
        assert (shows_tiers and slug not in listed) == (slug in updated), slug
        assert body.startswith(corrections.UPDATE_LEAD) == (slug in updated), slug


def test_notes_state_the_onsets_sources_and_regenerated_figures_without_dashes():
    record = registry()
    for slug in corrected_slugs():
        note = read("articles", f"{slug}.md").split("\n\n", 1)[0]
        for onset in record["onsets"]:
            assert corrections.long_date(onset["onset_date"]) in note
            assert onset["source_url"] in note
        assert "insufficient data" in note
        assert "\u2014" not in note and "\u2013" not in note
        if corrections.MENTIONS_TIERS.search(read("articles", f"{slug}.md").split("\n\n", 1)[1]):
            assert "Failure Radar tiers are now paused pending re-validation." in note
    for slug in updated_slugs():
        note = read("articles", f"{slug}.md").split("\n\n", 1)[0]
        assert note.startswith(corrections.UPDATE_LEAD)
        assert "paused pending re-validation" in note and "not a current reading" in note
        assert "\u2014" not in note and "\u2013" not in note
        if corrections.CITES_RECALL.search(read("articles", f"{slug}.md").split("\n\n", 1)[1]):
            assert f"{corrections.compact(record['record']['recall_ex_fraud_pct'])}% (" in note


def test_the_six_wrong_default_dates_are_corrected_in_place_and_explained():
    record = registry()
    previous = {o["previous_date"]: o["onset_date"] for o in record["onsets"]}
    for slug in SIX:
        note, text = read("articles", f"{slug}.md").split("\n\n", 1)
        assert not any(old in text for old in previous), slug
        assert "This article originally gave" in note
        sidecar = json.loads(read("articles", f"{slug}.json"))
        subject = json.dumps(sidecar["subject"])
        assert not any(old in subject for old in previous), slug
        fixed = sidecar["corrections"][-1]["dates_corrected"]
        assert [previous[row["from"]] for row in fixed] == [row["to"] for row in fixed]


def test_noted_pages_are_rendered_from_the_article_sources():
    for slug in corrected_slugs() + updated_slugs():
        meta = json.loads(read("articles", f"{slug}.json"))
        article = {**meta, "body_md": read("articles", f"{slug}.md")}
        png = open(os.path.join(ARTICLES, slug, "share.png"), "rb").read()
        revision = hashlib.sha256(png).hexdigest()[:16]
        card = social_cards.RenderedCard(
            png=png, revision=revision,
            url=f"https://liquilens.in/articles/{slug}/share.png?v={revision}",
            alt=social_cards._card_alt(social_cards.article_card_spec(article)))
        page = read("articles", slug, "index.html")
        assert daily_article.render_article(article, social_card=card) == page, slug
        assert '<aside class="correction wrap" role="note"' in page
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
        assert ld["dateModified"] == f"{meta['corrections'][-1]['date']}T00:00:00Z"
        if meta["corrections"][-1]["kind"] == "correction":
            assert ld["correction"][0]["@type"] == "CorrectionComment"
            assert " · corrected 20" in page
        else:
            assert "correction" not in ld
            assert " · updated 20" in page


def test_feeds_carry_the_note_and_the_revision_date():
    listed, updated = set(corrected_slugs()), set(updated_slugs())
    feed = json.loads(read("articles", "feed.json"))
    seen = 0
    for item in feed["items"]:
        slug = item["url"].rstrip("/").rsplit("/", 1)[-1]
        if slug in listed or slug in updated:
            seen += 1
            lead = corrections.NOTE_LEAD if slug in listed else corrections.UPDATE_LEAD
            assert item["content_text"].startswith(lead)
            assert item["date_modified"].endswith("T00:00:00Z")
        else:
            assert "date_modified" not in item
    assert seen > 0
    atom = read("articles", "feed.xml")
    assert "Correction, " in atom


def test_a_refresh_cannot_drop_a_note():
    slug = sorted(SIX)[0]
    body = read("articles", f"{slug}.md")
    notes, text = daily_article.split_correction_notes(body)
    assert len(notes) == 1 and notes[0].startswith(corrections.NOTE_LEAD)
    assert text and not text.startswith(corrections.NOTE_LEAD)
