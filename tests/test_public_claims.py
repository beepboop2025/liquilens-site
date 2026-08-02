import copy
import glob
import importlib.util
import json
import os
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
    assert len(RETIRED_POINTERS) == 6


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


def test_the_site_names_a_bond_book_field_the_live_payload_still_carries():
    problems, _ = vpc.check_live(ROOT, fetch=serving())
    assert not any("marked_insolvent" in p for p in problems)


def test_renaming_that_field_at_the_api_refutes_the_site():
    book = copy.deepcopy(payload(BOND_BOOK))
    for row in book["rows"]:
        row["mark_to_market_shortfall"] = row.pop("marked_insolvent")
    problems, _ = vpc.check_live(ROOT, fetch=serving(**{BOND_BOOK: book}))
    assert any("llms.txt" in p and "marked_insolvent" in p for p in problems)


def test_the_bond_book_fixture_is_the_real_public_one():
    row = payload(BOND_BOOK)["rows"][0]
    assert row["bank"] == "COMMUNITY STATE BANK"
    assert "marked_insolvent" in row


def test_an_endpoint_that_does_not_answer_is_never_evidence():
    problems, notes = vpc.check_live(ROOT, fetch=lambda url: None)
    assert problems == []
    assert len(notes) == 3


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
        row["mark_to_market_shortfall"] = row.pop("marked_insolvent")
    against_the_rename = vpc.check_live

    monkeypatch.setattr(sys, "argv", ["verify_public_claims.py"])
    monkeypatch.delenv("LIQUILENS_OFFLINE", raising=False)
    monkeypatch.setattr(
        vpc, "check_live",
        lambda root=vpc.ROOT: against_the_rename(
            root, fetch=serving(**{BOND_BOOK: book})))
    warnings, _ = vpc.check_live(ROOT)
    assert any("marked_insolvent" in w for w in warnings)
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
