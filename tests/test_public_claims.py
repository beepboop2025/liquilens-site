import copy
import glob
import importlib.util
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def _load():
    spec = importlib.util.spec_from_file_location(
        "verify_public_claims",
        os.path.join(ROOT, "scripts", "verify_public_claims.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vpc = _load()

MODEL_CARD = "https://api.liquilens.in/api/failure-radar/model-card"
US_VALIDATION = "https://api.liquilens.in/api/us-radar/validation"
BOARD = "https://api.liquilens.in/api/failure-radar/board"
BOND_BOOK = "https://api.liquilens.in/api/public-signals/bond-book"

# Captured unauthenticated from the production API on 2026-08-03.
LIVE = {
    MODEL_CARD: "failure-radar-model-card.json",
    US_VALIDATION: "us-radar-validation.json",
    BOARD: "failure-radar-board.json",
    BOND_BOOK: "public-signals-bond-book.json",
}


def payload(url):
    with open(os.path.join(FIXTURES, LIVE[url]), encoding="utf-8") as fh:
        return json.load(fh)


def serving(**overrides):
    """A fetch stub answering with the live payloads, edits applied."""
    def fetch(url):
        if url in overrides:
            return overrides[url]
        return payload(url) if url in LIVE else None
    return fetch


def write(tmp_path, name, text):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


def test_the_published_site_agrees_with_itself():
    assert vpc.check(ROOT) == []


def test_one_failure_count_everywhere(tmp_path):
    write(tmp_path, "index.html",
          "<p>73% recall on 552 US bank collapses</p>")
    write(tmp_path, "us/index.html",
          "<p>recall 73.1% of 550 failures</p>")
    problems = vpc.check(str(tmp_path))
    assert any("2 different numbers" in p for p in problems)
    assert any("552" in p and "study record is 550" in p for p in problems)


def test_the_study_number_alone_passes(tmp_path):
    write(tmp_path, "index.html",
          "<p>73% recall on 550 US bank collapses</p>")
    write(tmp_path, "us/index.html",
          "<p>recall 73.1% of 550 failures</p>")
    assert vpc.check(str(tmp_path)) == []


def test_a_number_agreed_everywhere_still_has_to_be_the_study_number(tmp_path):
    write(tmp_path, "index.html", "<p>73% recall on 552 US bank failures</p>")
    write(tmp_path, "us/index.html", "<p>all 552 FDIC failures</p>")
    problems = vpc.check(str(tmp_path))
    assert any("study record is 550" in p for p in problems)


def test_a_year_beside_the_word_failures_is_not_a_count(tmp_path):
    write(tmp_path, "index.html",
          "<p>two of the four 2026 failures, out of 550 failures since 2008</p>")
    assert vpc.check(str(tmp_path)) == []


def test_a_surface_with_no_count_at_all_is_refused(tmp_path):
    write(tmp_path, "index.html", "<p>nothing to see</p>")
    assert vpc.check(str(tmp_path)) == [
        "no US failure count found on any surface"]


@pytest.mark.parametrize("path", ["llms.txt", "index.html", "us/index.html",
                                  "research/index.html"])
def test_every_surface_that_owns_the_number_still_states_it(path):
    text = open(os.path.join(ROOT, path), encoding="utf-8").read()
    assert vpc.US_FAILURE_COUNT in vpc.plain(text)


def test_off_ladder_undertow_price(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "llms.txt",
          "## Undertow\nRetail desk small desk $149-299/mo; Desk $199/mo")
    problems = vpc.check(str(tmp_path))
    assert any("$149-299/mo" in p and "not on the Undertow ladder" in p
               for p in problems)


def test_ladder_prices_pass(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "llms.txt",
          "Undertow: Alerts $29/mo; Agent seat $99/mo; Desk $199/mo; "
          "founding $8,000/yr; paid routes from $0.05/call")
    assert vpc.check(str(tmp_path)) == []


def test_a_liquilens_price_is_not_measured_against_the_undertow_ladder(
        tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. The LiquiLens pilot starts at $2,500/mo.</p>")
    assert vpc.check(str(tmp_path)) == []


def test_the_same_price_on_an_undertow_surface_is_measured(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "undertow/index.html",
          "<p>The Undertow desk starts at $2,500/mo.</p>")
    problems = vpc.check(str(tmp_path))
    assert any("$2,500/mo" in p and "undertow/index.html" in p
               for p in problems)


RETIRED_POINTERS = sorted(
    os.path.basename(p) for p in
    glob.glob(os.path.join(FIXTURES, "retired_pointers", "*.html")))


def test_the_retired_pointer_fixtures_were_captured():
    assert len(RETIRED_POINTERS) == 7


@pytest.mark.parametrize("name", RETIRED_POINTERS)
def test_a_pointer_the_site_published_at_the_401_demo_is_refused(
        tmp_path, name):
    write(tmp_path, "index.html",
          fixture(os.path.join("retired_pointers", name)))
    problems = vpc.check(str(tmp_path))
    assert any("demo.liquilens.in" in p for p in problems), name


def test_the_gate_reads_a_pointer_that_lives_only_in_the_href(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. "
          "<a href=\"https://demo.liquilens.in/?tab=evidence\">"
          "Open the Evidence record</a></p>")
    problems = vpc.check(str(tmp_path))
    assert any("open door" in p for p in problems)


def test_the_gate_reads_a_single_quoted_href_too(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. "
          "<a href='https://demo.liquilens.in/?tab=evidence'>"
          "Open the Evidence record</a></p>")
    problems = vpc.check(str(tmp_path))
    assert any("open door" in p for p in problems), problems


def test_the_host_is_matched_however_it_is_cased(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. "
          "<a href=\"https://DEMO.LiquiLens.in/?tab=evidence\">"
          "Open the Evidence record</a></p>")
    problems = vpc.check(str(tmp_path))
    assert any("open door" in p for p in problems), problems


def test_a_pointer_that_names_the_gate_passes(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. The record sits in the "
          "<a href=\"https://demo.liquilens.in/?tab=evidence\">Evidence tab"
          "</a>, which is granted on request.</p>")
    assert vpc.check(str(tmp_path)) == []


def test_a_pointer_that_says_nothing_about_the_gate_is_refused(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. The record sits in the "
          "<a href=\"https://demo.liquilens.in/?tab=evidence\">Evidence tab"
          "</a>.</p>")
    problems = vpc.check(str(tmp_path))
    assert any("says nothing about the gate" in p for p in problems)


def test_the_dated_ship_log_may_not_call_the_demo_open(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "ship-log/index.html",
          "<div>20 Jul The demo gate comes down: demo.liquilens.in is open, "
          "no code and no signup.</div>")
    problems = vpc.check(str(tmp_path))
    assert any("ship-log/index.html" in p for p in problems)


def test_a_past_tense_ship_log_entry_passes(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "ship-log/index.html",
          "<div>20 Jul The demo gate came down: demo.liquilens.in was opened "
          "to anyone, and the access code was retired.</div>")
    assert vpc.check(str(tmp_path)) == []


def test_retired_demo_openness_claim(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. The walkthrough at demo.liquilens.in is open, "
          "no signup and no code.</p>")
    problems = vpc.check(str(tmp_path))
    assert any("demo openness" in p for p in problems)


def test_demo_granted_on_request_passes(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. The walkthrough at demo.liquilens.in sits behind "
          "an access request, so the URL answers 401.</p>")
    assert vpc.check(str(tmp_path)) == []


def test_browser_desk_advertised_as_needing_no_signup(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "llms.txt",
          "- Web desk in any browser (https://liquilens-undertow.com/app/): "
          "the free tier surfaces with no signup")
    problems = vpc.check(str(tmp_path))
    assert any("no signup" in p and "401" in p for p in problems)


def test_free_web_desk_claim(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "llms.txt", "- Product site and free web desk: ...")
    problems = vpc.check(str(tmp_path))
    assert any("undertow web desk" in p for p in problems)


WORKFLOW_WITH_RM = """
jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
      - name: Keep the unscanned directories out of the artifact
        run: rm -rf scripts tests
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
"""

WORKFLOW_WITHOUT_RM = """
jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
"""


def test_every_directory_the_scanner_skips_is_kept_off_the_public_site():
    assert vpc.SKIP_DIRS <= vpc.artifact_excludes(ROOT)


def test_the_scanner_skips_a_directory_that_holds_retired_strings():
    here = open(os.path.abspath(__file__), encoding="utf-8").read()
    assert "552 US bank collapses" in here
    assert "all 552 FDIC failures" in here
    assert "demo.liquilens.in is open, no code and no signup" in here
    assert "tests" in vpc.SKIP_DIRS


def test_a_workflow_that_uploads_the_scanner_blind_spots_is_refused(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, ".github/workflows/pages.yml", WORKFLOW_WITHOUT_RM)
    problems = vpc.check(str(tmp_path))
    assert any(p.startswith("scripts/") for p in problems)
    assert any(p.startswith("tests/") for p in problems)


def test_a_workflow_that_drops_them_before_upload_passes(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, ".github/workflows/pages.yml", WORKFLOW_WITH_RM)
    assert vpc.check(str(tmp_path)) == []


STATUS = os.path.join(ROOT, "status", "index.html")


def test_the_status_page_never_badges_an_unreadable_probe_ok():
    raw = open(STATUS, encoding="utf-8").read()
    at = raw.find("no-cors")
    assert at > 0
    resolve = raw[at:at + 400]
    assert ", true," not in resolve
    assert "'answered'" in resolve


def test_the_status_page_says_what_the_weaker_state_means():
    text = vpc.plain(open(STATUS, encoding="utf-8").read())
    assert "ANSWERED" in text
    assert "401" in text


def test_the_live_model_card_refutes_the_sites_withheld_weights_claim():
    problems, notes = vpc.check_live(ROOT, fetch=serving())
    assert notes == []
    assert any("research/index.html" in p and "fitted weights" in p
               and MODEL_CARD in p for p in problems)


def test_the_live_us_validation_refutes_it_too():
    problems, _ = vpc.check_live(ROOT, fetch=serving())
    assert any("fitted weights" in p and US_VALIDATION in p for p in problems)


def test_the_claim_stands_once_the_api_stops_serving_the_weights():
    card = copy.deepcopy(payload(MODEL_CARD))
    card["hazard_fit"]["coefficients"].pop("coef")
    validation = copy.deepcopy(payload(US_VALIDATION))
    validation["validation"].pop("weights")
    problems, notes = vpc.check_live(
        ROOT, fetch=serving(**{MODEL_CARD: card, US_VALIDATION: validation}))
    assert problems == []
    assert notes == []


def test_the_live_board_refutes_a_promise_that_living_scores_stay_private(
        tmp_path):
    write(tmp_path, "research/index.html",
          fixture("retired_withhold_promise.html"))
    problems, _ = vpc.check_live(str(tmp_path), fetch=serving())
    assert any("scores of living institutions" in p and BOARD in p
               for p in problems)


def test_the_site_no_longer_promises_that_living_scores_stay_private():
    problems, _ = vpc.check_live(ROOT, fetch=serving())
    assert not any("scores of living institutions" in p for p in problems)


def test_the_board_fixture_is_the_real_public_one():
    rows = payload(BOARD)["rows"]
    assert rows[0]["name"] == "ESAF Small Finance Bank"
    assert rows[0]["score"] == 66.0
    assert rows[0]["label"] != "failed"


MARK_FIELD = "tier1_negative_after_ugl_mark"


def test_the_site_names_a_bond_book_field_the_live_payload_still_carries():
    problems, _ = vpc.check_live(ROOT, fetch=serving())
    assert not any(MARK_FIELD in p for p in problems)


def test_renaming_that_field_at_the_api_refutes_the_site():
    book = copy.deepcopy(payload(BOND_BOOK))
    for row in book["rows"]:
        row["marked_insolvent"] = row.pop(MARK_FIELD)
    problems, _ = vpc.check_live(ROOT, fetch=serving(**{BOND_BOOK: book}))
    assert any("llms.txt" in p and MARK_FIELD in p for p in problems)


def test_a_field_the_site_stopped_naming_is_reported_not_dropped(monkeypatch):
    monkeypatch.setattr(
        vpc, "FIELD_VS_LIVE",
        (("marked_insolvent", BOND_BOOK, ("rows", 0, "marked_insolvent")),))
    problems, notes = vpc.check_live(ROOT, fetch=serving())
    assert not any("marked_insolvent" in p for p in problems)
    assert any("no published surface names marked_insolvent" in n
               for n in notes)


def test_the_bond_book_fixture_is_the_real_public_one():
    row = payload(BOND_BOOK)["rows"][0]
    assert row["bank"] == "COMMUNITY STATE BANK"
    assert MARK_FIELD in row
    assert "mark_qualifier" in row
    assert "mark_semantics" in payload(BOND_BOOK)


def test_an_endpoint_that_does_not_answer_is_never_evidence():
    problems, notes = vpc.check_live(ROOT, fetch=lambda url: None)
    assert problems == []
    assert len(notes) == 5


def test_the_live_api_warns_and_publishes_while_a_local_clash_still_blocks(
        monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["verify_public_claims.py"])
    monkeypatch.delenv("LIQUILENS_OFFLINE", raising=False)
    monkeypatch.setattr(vpc, "check", lambda root=vpc.ROOT: [])
    monkeypatch.setattr(
        vpc, "check_live",
        lambda root=vpc.ROOT: (["the model card serves the weights"], []))
    assert vpc.main() == 0
    assert "the model card serves the weights" in capsys.readouterr().err

    monkeypatch.setattr(vpc, "check",
                        lambda root=vpc.ROOT: ["552 and 550 on one site"])
    assert vpc.main() == 1


def test_renaming_the_bond_book_field_at_the_api_never_blocks_the_deploy(
        monkeypatch):
    book = copy.deepcopy(payload(BOND_BOOK))
    for row in book["rows"]:
        row["marked_insolvent"] = row.pop(MARK_FIELD)
    against_the_rename = vpc.check_live

    monkeypatch.setattr(sys, "argv", ["verify_public_claims.py"])
    monkeypatch.delenv("LIQUILENS_OFFLINE", raising=False)
    monkeypatch.setattr(
        vpc, "check_live",
        lambda root=vpc.ROOT: against_the_rename(
            root, fetch=serving(**{BOND_BOOK: book})))
    warnings, _ = vpc.check_live(ROOT)
    assert any(MARK_FIELD in w for w in warnings)
    assert vpc.main() == 0


def test_neither_a_dead_network_nor_an_offline_run_can_redden_the_deploy(
        monkeypatch):
    def unreachable(root=vpc.ROOT):
        raise OSError("getaddrinfo failed")

    monkeypatch.setattr(sys, "argv", ["verify_public_claims.py"])
    monkeypatch.delenv("LIQUILENS_OFFLINE", raising=False)
    monkeypatch.setattr(vpc, "check", lambda root=vpc.ROOT: [])
    monkeypatch.setattr(vpc, "check_live", unreachable)
    assert vpc.main() == 0

    monkeypatch.setenv("LIQUILENS_OFFLINE", "1")
    assert vpc.main() == 0


def test_the_publish_step_never_reads_the_network_and_the_live_step_cannot_fail(
        ):
    raw = open(os.path.join(ROOT, ".github", "workflows", "pages.yml"),
               encoding="utf-8").read()
    steps = raw.split("- name: ")
    blocking = [s for s in steps
                if s.startswith("Verify the published files")]
    live = [s for s in steps if s.startswith("Report where the live API")]
    assert len(blocking) == 1 and len(live) == 1
    assert "LIQUILENS_OFFLINE" in blocking[0]
    assert "continue-on-error: true" not in blocking[0]
    assert "continue-on-error: true" in live[0]


FAQ_JSONLD = """<p>550 failures</p>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
  {"@type": "Question", "name": "How do I get access?",
   "acceptedAnswer": {"@type": "Answer", "text": "%s"}}]}
</script>"""

JSONLD_OPEN_DOOR = ("The walkthrough is at https://demo.liquilens.in and you "
                    "can open it now.")

JSONLD_NAMES_THE_GATE = ("The walkthrough at https://demo.liquilens.in sits "
                         "behind an access request, so the URL answers 401 "
                         "until access is granted.")


def test_a_json_ld_answer_that_calls_the_gated_demo_open_is_refused(tmp_path):
    write(tmp_path, "index.html", FAQ_JSONLD % JSONLD_OPEN_DOOR)
    problems = vpc.check(str(tmp_path))
    assert any("JSON-LD" in p and "open door" in p for p in problems), problems

    write(tmp_path, "index.html", FAQ_JSONLD % JSONLD_NAMES_THE_GATE)
    assert vpc.check(str(tmp_path)) == []


def test_a_json_ld_answer_that_says_nothing_about_the_gate_is_refused(
        tmp_path):
    write(tmp_path, "index.html",
          FAQ_JSONLD % "The record sits in the demo.liquilens.in Evidence tab.")
    problems = vpc.check(str(tmp_path))
    assert any("JSON-LD" in p and "says nothing about the gate" in p
               for p in problems), problems


def test_a_json_ld_block_that_will_not_parse_is_still_scanned(tmp_path):
    write(tmp_path, "index.html",
          FAQ_JSONLD % JSONLD_OPEN_DOOR + "\n<script type='application/ld+json'>"
          "{not json at all: https://demo.liquilens.in is open}</script>")
    problems = vpc.check(str(tmp_path))
    assert sum("JSON-LD" in p for p in problems) == 2, problems


def test_the_homepage_faq_json_ld_is_reached_by_the_scanner():
    raw = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    answers = vpc.jsonld_texts(raw)
    assert any(vpc.DEMO_HOST in a and "401" in a for a in answers)


# The only access cue sits in a neighbouring sentence, well inside 200
# characters of the pointer, and never in the pointer's own sentence.
CUE_IN_A_DIFFERENT_SENTENCE = (
    "<p>550 failures. Pilot access to the lender console is granted on "
    "request, and the desk answers every request for the product API within "
    "a working day.</p>"
    "<p><a href=\"https://demo.liquilens.in\">The Evidence tab</a></p>")

CUE_IN_THE_SAME_SENTENCE = (
    "<p>550 failures. Pilot access to the lender console is granted on "
    "request, and the desk answers every request for the product API within "
    "a working day.</p>"
    "<p><a href=\"https://demo.liquilens.in\">The Evidence tab</a> is granted "
    "on request too.</p>")


def test_a_cue_in_a_neighbouring_sentence_no_longer_excuses_the_pointer(
        tmp_path):
    write(tmp_path, "index.html", CUE_IN_A_DIFFERENT_SENTENCE)
    problems = vpc.check(str(tmp_path))
    assert any("says nothing about the gate" in p for p in problems), problems

    write(tmp_path, "index.html", CUE_IN_THE_SAME_SENTENCE)
    assert vpc.check(str(tmp_path)) == []


# List items carry no sentence punctuation, so tag stripping alone runs the
# neighbour's cue and the pointer together into one line.
CUE_IN_A_NEIGHBOURING_ELEMENT = (
    "<p>550 failures</p>"
    "<ul><li>Pilot access to the lender console is granted on request</li>"
    "<li><a href=\"https://demo.liquilens.in\">The Evidence tab</a></li></ul>")

CUE_IN_THE_SAME_ELEMENT = (
    "<p>550 failures</p>"
    "<ul><li>Pilot access to the lender console is granted on request</li>"
    "<li><a href=\"https://demo.liquilens.in\">The Evidence tab</a>, granted "
    "on request</li></ul>")


def test_a_cue_in_a_neighbouring_element_no_longer_excuses_the_pointer(
        tmp_path):
    write(tmp_path, "index.html", CUE_IN_A_NEIGHBOURING_ELEMENT)
    problems = vpc.check(str(tmp_path))
    assert any("says nothing about the gate" in p for p in problems), problems

    write(tmp_path, "index.html", CUE_IN_THE_SAME_ELEMENT)
    assert vpc.check(str(tmp_path)) == []


def test_an_inline_tag_inside_the_sentence_does_not_split_it(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. The record sits in the "
          "<a href=\"https://demo.liquilens.in\">Evidence tab</a>, which is "
          "<strong>granted <em>on request</em></strong>.</p>")
    assert vpc.check(str(tmp_path)) == []


def test_a_retired_access_claim_in_the_og_description_is_refused(tmp_path):
    write(tmp_path, "index.html",
          fixture(os.path.join("retired_meta", "og-description-access-claim"
                                              ".html")))
    problems = vpc.check(str(tmp_path))
    assert any("demo openness" in p for p in problems), problems


def test_the_meta_tags_that_carried_the_other_denominator_are_scanned(tmp_path):
    write(tmp_path, "index.html",
          fixture(os.path.join("retired_meta",
                               "index-9-22-denominator.html")))
    write(tmp_path, "us/index.html", "<p>recall 73.1% of 550 failures</p>")
    problems = vpc.check(str(tmp_path))
    assert any("2 different numbers" in p for p in problems), problems
    assert any("552" in p and "study record is 550" in p for p in problems)


def test_a_pointer_that_lives_only_in_a_card_description_is_read(tmp_path):
    write(tmp_path, "index.html",
          "<meta property=\"og:description\" content=\"The full board is at "
          "demo.liquilens.in\" />"
          "<p>550 failures. Pilot access is granted on request.</p>")
    problems = vpc.check(str(tmp_path))
    assert any("attribute" in p and "says nothing about the gate" in p
               for p in problems), problems


def test_an_open_door_promise_in_an_alt_or_aria_label_is_refused(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures</p>"
          "<img src=\"/og-radar.png\" alt=\"The demo.liquilens.in board is "
          "one click away\" />")
    problems = vpc.check(str(tmp_path))
    assert any("attribute" in p and "open door" in p for p in problems), \
        problems

    write(tmp_path, "index.html",
          "<p>550 failures</p>"
          "<img src=\"/og-radar.png\" aria-label=\"The demo.liquilens.in "
          "board, granted on request\" />")
    assert vpc.check(str(tmp_path)) == []


def test_an_anchors_own_label_is_read_beside_the_link_text(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures. <a href=\"https://demo.liquilens.in\" "
          "aria-label=\"Open it now\">the Evidence tab, granted on request"
          "</a></p>")
    problems = vpc.check(str(tmp_path))
    assert any("open door" in p for p in problems), problems


CSP = [line for line in
       open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
       .splitlines() if "Content-Security-Policy" in line]


def test_the_content_security_policy_is_a_header_and_not_copy(tmp_path):
    assert len(CSP) == 1 and vpc.DEMO_HOST in CSP[0]
    write(tmp_path, "index.html", CSP[0] + "<p>550 failures</p>")
    assert vpc.check(str(tmp_path)) == []


RETIRED_CSS = ("/* banner copy, retired: demo.liquilens.in is open, "
               "no signup and no code */\n.url b{color:#E3B778}\n")


def test_a_retired_claim_in_a_served_stylesheet_is_refused(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "brand/_banner.css", RETIRED_CSS)
    problems = vpc.check(str(tmp_path))
    assert any("brand/_banner.css" in p and "demo openness" in p
               for p in problems), problems


def test_a_served_file_with_no_suffix_at_all_is_refused(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "brand/COPY", "banner strap: 552 US bank failures\n")
    problems = vpc.check(str(tmp_path))
    assert any("brand/COPY" in p and "study record is 550" in p
               for p in problems), problems


def test_the_stylesheets_the_site_serves_are_in_the_scan():
    scanned = vpc.published_files(ROOT)
    assert "brand/_banner.css" in scanned
    assert "brand/_logo.css" in scanned
    assert ".well-known/security.txt" in scanned


def test_an_image_is_never_read_as_copy(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    (tmp_path / "og.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00552 US bank failures\x00")
    assert vpc.check(str(tmp_path)) == []
    assert "og.png" not in vpc.published_files(str(tmp_path))


def test_one_badly_encoded_file_no_longer_disarms_every_other_rule(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    (tmp_path / "us").mkdir(parents=True, exist_ok=True)
    (tmp_path / "us" / "index.html").write_bytes(
        "<p>caf\xe9 lenders: 552 US bank failures</p>".encode("latin-1"))
    problems = vpc.check(str(tmp_path))
    assert any("552" in p and "study record is 550" in p for p in problems)


def test_a_cue_above_the_links_call_to_action_no_longer_excuses_it(tmp_path):
    write(tmp_path, "index.html",
          fixture(os.path.join("retired_pointers",
                               "index-839-card-cue-above-the-call-to-action"
                               ".html")))
    problems = vpc.check(str(tmp_path))
    assert any("says nothing about the gate" in p for p in problems), problems


LAYER_CARD = re.compile(
    r"<a class=\"layer\"[^>]*href=\"https://demo\.liquilens\.in[^\"]*\"[^>]*>"
    r".*?</a>", re.S)


def test_the_published_cards_carry_the_cue_in_their_call_to_action(tmp_path):
    raw = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    cards = LAYER_CARD.findall(raw)
    assert len(cards) == 5
    for card in cards:
        write(tmp_path, "index.html", card + "<p>550 failures</p>")
        assert vpc.check(str(tmp_path)) == [], card[:200]


# The promise window still covers the whole link, so a retired claim in the
# card body is caught even when it is nowhere near the call to action. The
# body sentence is index.html line 1207 as published before 2026-08-03.
def test_an_open_door_claim_in_the_card_body_is_still_refused(tmp_path):
    write(tmp_path, "index.html",
          "<a class=\"layer\" "
          "href=\"https://demo.liquilens.in/?tab=evidence\">"
          "<h3>LiquiLens Treasury</h3>"
          "<p>Treasury and early warning for Indian lenders and businesses. "
          "Runs in production, multi tenant, on your servers if your book "
          "cannot leave the building. The crisis validation record is open in "
          "the demo's Evidence tab, institution by institution, misses "
          "included.</p>"
          "<span class=\"go\"><span>Read the board →</span></span></a>"
          "<p>550 failures</p>")
    problems = vpc.check(str(tmp_path))
    assert any("open door" in p for p in problems), problems


def test_a_retired_claim_a_script_writes_into_the_page_is_refused(tmp_path):
    write(tmp_path, "index.html",
          fixture(os.path.join("retired_injected",
                               "index-1068-board-fallback-written-by-script"
                               ".html")))
    problems = vpc.check(str(tmp_path))
    assert any("index.html script" in p and "open door" in p
               for p in problems), problems


def test_a_retired_pointer_a_style_rule_writes_into_the_page_is_refused(
        tmp_path):
    write(tmp_path, "index.html",
          fixture(os.path.join("retired_injected",
                               "status-353-row-written-by-a-style-rule"
                               ".html")))
    problems = vpc.check(str(tmp_path))
    assert any("index.html style" in p and "says nothing about the gate" in p
               for p in problems), problems


def test_the_script_that_probes_the_demo_is_not_read_as_copy(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures</p>"
          "<script>fetch('https://demo.liquilens.in/', {mode:'no-cors'})"
          ".then(function(){ set('demoBadge', 'answered'); });</script>")
    assert vpc.check(str(tmp_path)) == []


def test_a_retired_claim_parked_in_a_comment_is_refused(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "ship-log/index.html",
          fixture(os.path.join("retired_injected",
                               "ship-log-340-parked-in-a-comment.html")))
    problems = vpc.check(str(tmp_path))
    assert any("demo openness" in p for p in problems), problems
    assert any("open door" in p for p in problems), problems


def test_the_copy_that_replaced_it_still_passes(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, "ship-log/index.html",
          fixture(os.path.join("retired_injected",
                               "ship-log-340-parked-in-a-comment.html"))
          .split("-->")[-1])
    assert vpc.check(str(tmp_path)) == []


# The og:description sentence retired from index.html on 2026-08-03, in the
# two attributes a tooltip and a form hint carry copy in.
RETIRED_ACCESS_SENTENCE = (
    "The live walkthrough at demo.liquilens.in is open, no signup and no "
    "code.")


@pytest.mark.parametrize("markup", [
    "<span class=\"chip\" data-tip=\"%s\"></span>",
    "<input id=\"lcrAssets\" placeholder=\"%s\">"])
def test_a_retired_claim_in_a_tooltip_or_a_form_hint_is_refused(
        tmp_path, markup):
    write(tmp_path, "index.html",
          "<p>550 failures</p>" + markup % RETIRED_ACCESS_SENTENCE)
    problems = vpc.check(str(tmp_path))
    assert any("demo openness" in p for p in problems), problems


def test_a_data_attribute_that_is_machinery_is_never_read_as_copy(tmp_path):
    write(tmp_path, "index.html",
          "<p>550 failures</p>"
          "<i class=\"bar\" data-w=\"552\"></i> failures flagged early")
    assert vpc.check(str(tmp_path)) == []


def test_a_json_ld_answer_is_reported_once_and_under_its_own_name(tmp_path):
    write(tmp_path, "index.html", FAQ_JSONLD % JSONLD_OPEN_DOOR)
    problems = vpc.check(str(tmp_path))
    assert len(problems) == 1, problems
    assert "JSON-LD" in problems[0]


def test_a_file_git_keeps_out_of_the_checkout_is_never_scanned(tmp_path):
    write(tmp_path, "index.html", "<p>550 failures</p>")
    write(tmp_path, ".gitignore", ".pytest_cache/\n")
    write(tmp_path, ".pytest_cache/v/cache/lastfailed.json",
          "{\"552 US bank failures\": true}")
    assert vpc.check(str(tmp_path)) == []
