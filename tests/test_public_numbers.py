"""The headline evidence figures are generated from the reviewed capture.

These tests pin the M9 contract: no hand-typed evidence figure, no fallback
when the capture or the live API is unavailable or out of contract, and an
India recall that never appears without its qualifier.
"""
from __future__ import annotations

import copy
import io
import json
import re
import shutil
from pathlib import Path

import pytest

from scripts import public_numbers as pn


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = pn.load_capture(ROOT)
FIGURES = pn.values(CAPTURE)
REGISTERED = sorted({figure.path for figure in pn.FIGURES})


def site_copy(tmp_path: Path) -> Path:
    """The capture and every registered page, outside the checkout."""
    root = tmp_path / "site"
    for relative in [pn.CAPTURE_PATH, *REGISTERED]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return root


def write_capture(root: Path, capture: dict) -> None:
    (root / pn.CAPTURE_PATH).write_text(json.dumps(capture), encoding="utf-8")


def edit(root: Path, relative: str, old: str, new: str, count: int = 1) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == count, (relative, old)
    path.write_text(text.replace(old, new), encoding="utf-8")


def line_of(relative: str, needle: str, root: Path = ROOT) -> int:
    text = (root / relative).read_text(encoding="utf-8")
    assert text.count(needle) == 1, (relative, needle)
    return text[:text.index(needle)].count("\n") + 1


def append(root: Path, relative: str, snippet: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert "</body>" in text
    path.write_text(text.replace("</body>", snippet + "\n</body>", 1),
                    encoding="utf-8")


# ------------------------------------------------------------ the record


def test_the_committed_capture_is_in_contract():
    assert CAPTURE["schema"] == pn.SCHEMA
    assert CAPTURE["us"]["source_url"] == "https://api.liquilens.in/api/evidence/us"
    assert CAPTURE["india"]["source_url"] == (
        "https://api.liquilens.in/api/evidence/summary")
    assert CAPTURE["us"]["historical_evidence"]["status"] == pn.US_STATUS
    assert CAPTURE["india"]["historical_evidence"]["status"] == pn.INDIA_STATUS


def test_every_published_figure_follows_the_capture():
    assert pn.problems(ROOT) == []


def test_generation_is_idempotent(tmp_path):
    root = site_copy(tmp_path)
    assert pn.render(root) == []
    for relative in REGISTERED:
        assert (root / relative).read_bytes() == (ROOT / relative).read_bytes()


def test_every_registration_and_exemption_still_matches():
    for figure in pn.FIGURES:
        text = (ROOT / figure.path).read_text(encoding="utf-8")
        pattern, _ = pn._compile(figure.template)
        assert len(pattern.findall(text)) == figure.count, figure.template
    for item in pn.EXEMPT:
        text = (ROOT / item.path).read_text(encoding="utf-8")
        assert text.count(item.text) == item.count, item.text


# ------------------------------------------------- the revert, and typing


PRE_M9 = (
    # The copy as it stood on main before this change, typed by hand.
    ("index.html", '<div class="market">United States · 554 failures since 2008</div>',
     '<div class="market">United States · 552 failures since 2008</div>'),
    ("index.html", "<span><b>73.1%</b> recall</span><span><b>0.851</b> pooled AUC"
     "</span><span><b>21.6 mo</b> median lead</span>",
     "<span><b>72.8%</b> recall</span><span><b>0.854</b> pooled AUC"
     "</span><span><b>21.7 mo</b> median lead</span>"),
    ("index.html", "<span><b>88.9%</b> recall excluding fraud-concealed books "
     "(76.2% overall)</span>", "<span><b>88.9%</b> recall</span>"),
    ("us/index.html", "<tr><td class=\"rowlab\">recall, 95% interval</td>"
     "<td>69.5% to 76.9%</td></tr>",
     "<tr><td class=\"rowlab\">recall, 95% interval</td>"
     "<td>69.0% to 76.6%</td></tr>"),
    ("llms.txt", "The served headline reports 88.9 percent recall excluding "
     "fraud-concealed books (76.2 percent overall) and",
     "The served headline reports 88.9 percent recall and"),
)


def test_the_pre_m9_hand_typed_copy_is_refused(tmp_path):
    root = site_copy(tmp_path)
    for relative, current, old in PRE_M9:
        edit(root, relative, current, old)
    found = pn.problems(root)
    us_card = line_of("index.html", 'data-market="US"', root)
    india_card = line_of("index.html", 'data-market="IN"', root)
    interval = line_of("us/index.html", "recall, 95% interval", root)
    india_llms = line_of("llms.txt", "- India: PERIOD_END_PROXY", root)
    for expected in (
            f"index.html:{us_card}: publishes '552' where",
            f"index.html:{us_card}: publishes '72.8' where",
            f"index.html:{us_card}: publishes '0.854' where",
            f"index.html:{us_card}: publishes '21.7' where",
            f"index.html:{india_card}: publishes '<b>88.9%</b> recall' where",
            f"us/index.html:{interval}: publishes '69.0' where",
            f"llms.txt:{india_llms}: publishes '88.9 percent recall' where"):
        assert any(problem.startswith(expected) for problem in found), (
            expected, found)
    # Regenerating restores the reviewed copy exactly.
    assert set(pn.render(root)) == {"index.html", "us/index.html", "llms.txt"}
    assert pn.problems(root) == []
    for relative in REGISTERED:
        assert (root / relative).read_bytes() == (ROOT / relative).read_bytes()


def test_a_correct_figure_typed_by_hand_is_still_refused(tmp_path):
    root = site_copy(tmp_path)
    append(root, "index.html", f"<p>LiquiLens reports {FIGURES['us.recall']}% "
           f"recall across {FIGURES['us.failures']} US failures since 2008, "
           f"pooled AUC {FIGURES['us.auc']} and a {FIGURES['us.median_lead']}"
           f"-month median lead.</p>")
    found = [p for p in pn.problems(root) if "is typed into the page" in p]
    labels = {p.split(": ", 1)[1].split(" is typed")[0] for p in found}
    assert labels >= {
        f"a US failure count {FIGURES['us.failures']}",
        f"a recall percentage {FIGURES['us.recall']}",
        f"an AUC {FIGURES['us.auc']}",
        f"a median lead {FIGURES['us.median_lead']}",
    }, found


def test_a_hand_typed_figure_on_any_publishable_page_is_refused(tmp_path):
    root = site_copy(tmp_path)
    page = root / "guides" / "new" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<html><body><p>The study covers 552 FDIC receiverships "
                    "with 72.8 percent recall.</p></body></html>",
                    encoding="utf-8")
    found = pn.problems(root)
    assert any(p.startswith("guides/new/index.html:1: a US failure count 552")
               for p in found), found
    assert any(p.startswith("guides/new/index.html:1: a recall percentage 72.8")
               for p in found), found


def test_an_unqualified_india_recall_is_refused(tmp_path):
    root = site_copy(tmp_path)
    ex_fraud = FIGURES["india.recall_ex_fraud"]
    append(root, "research/index.html",
           f"<p>{ex_fraud}% recall across 48 Indian institutions.</p>")
    found = pn.problems(root)
    assert any("the India ex-fraud recall" in p and "outside the qualified "
               "label" in p for p in found), found
    assert any(f"a recall percentage {ex_fraud}" in p for p in found), found
    assert any("an India cohort size 48" in p for p in found), found


def test_a_qualifier_removed_from_a_registered_spot_is_refused(tmp_path):
    root = site_copy(tmp_path)
    edit(root, "research/index.html",
         "<span>served recall excluding fraud-concealed books (76.2% overall)"
         "</span>", "<span>served recall</span>")
    tile = line_of("research/index.html", "<span>served recall</span>", root)
    assert any(f"research/index.html:{tile}: publishes ' recall' where" in p
               for p in pn.problems(root))


def test_dated_history_is_left_alone(tmp_path):
    root = site_copy(tmp_path)
    for relative in ("articles/2026-08-01-x/index.html", "ship-log/index.html",
                     "protocol/discovery-observations/x/receipt.json"):
        page = root / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("552 failures since 2008, 72.8% recall, 88.9% recall",
                        encoding="utf-8")
    edit(root, "llms.txt", "<!-- DAILY-ARTICLES:START -->",
         "<!-- DAILY-ARTICLES:START -->\n- 88.9% of non-fraud failures "
         "flagged across 552 US failures")
    assert pn.problems(root) == []
    # The same text on a page that is not dated history is refused.
    control = root / "guides" / "control" / "index.html"
    control.parent.mkdir(parents=True)
    control.write_text("552 failures since 2008, 72.8% recall, 88.9% recall",
                       encoding="utf-8")
    found = pn.problems(root)
    assert any(p.startswith("guides/control/index.html:1: a US failure count "
                            "552") for p in found), found
    assert any("guides/control/index.html:1: a recall percentage 72.8" in p
               for p in found), found


def test_an_exemption_is_pinned_verbatim(tmp_path):
    root = site_copy(tmp_path)
    edit(root, "us/index.html", "64.7 percent of the 552 failures since 2008",
         "64.7 percent of the 553 failures since 2008")
    found = pn.problems(root)
    assert any("the exempt text" in p and "appears 0 time(s)" in p
               for p in found), found
    assert any("a US failure count 553" in p for p in found), found


# ----------------------------------------------------- wording, one line


def test_a_different_india_wording_is_a_one_line_change(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pn, "INDIA_RECALL_LABEL",
        "{overall} recall overall ({ex_fraud} with the fraud-concealed "
        "misses set aside)")
    root = site_copy(tmp_path)
    changed = pn.render(root)
    assert set(changed) == {"index.html", "research/index.html", "llms.txt"}
    assert pn.problems(root) == []
    home = (root / "index.html").read_text(encoding="utf-8")
    research = (root / "research/index.html").read_text(encoding="utf-8")
    llms = (root / "llms.txt").read_text(encoding="utf-8")
    overall, ex_fraud = FIGURES["india.recall"], FIGURES["india.recall_ex_fraud"]
    assert home.count(f"{overall}% recall overall ({ex_fraud}% with the "
                      f"fraud-concealed misses set aside)") == 3
    assert (f"<span><b>{overall}%</b> recall overall ({ex_fraud}% with the "
            f"fraud-concealed misses set aside)</span>") in home
    assert f'<div class="stat"><b>{overall}%</b><span>served recall overall' \
        in research
    assert f"{overall} percent recall overall ({ex_fraud} percent with" in llms
    assert "excluding fraud-concealed books" not in home + research + llms


def test_the_wording_must_carry_both_figures():
    for wording in ("{ex_fraud} recall", "{overall} recall",
                    "{ex_fraud} and {ex_fraud} ({overall})",
                    "{ex_fraud} ({overall}) {other}"):
        with pytest.raises(pn.ContractError):
            pn.india_label(FIGURES, "", wording=wording)


# ------------------------------------------------------- fail closed


def mutated(change) -> dict:
    capture = copy.deepcopy(CAPTURE)
    change(capture)
    return capture


@pytest.mark.parametrize("change", [
    lambda c: c.update(schema="liquilens.public-evidence-figures.v0"),
    lambda c: c["us"]["summary"].update(failures_with_data=True),
    lambda c: c["us"]["summary"].update(failures_with_data=0),
    lambda c: c["us"]["summary"].update(recall_pct=73.14),
    lambda c: c["us"]["summary"].update(recall_ci95_pct=[74.0, 76.9]),
    lambda c: c["us"]["summary"].update(auc_pooled_24m=1.2),
    lambda c: c["us"]["summary"].pop("median_lead_months"),
    lambda c: c["us"]["summary"].update(extra=1),
    lambda c: c["us"]["historical_evidence"].update(real_money_eligible=True),
    lambda c: c["us"]["historical_evidence"].update(status="VALIDATED"),
    lambda c: c["india"]["historical_evidence"].update(
        validated_backtest_eligible=True),
    lambda c: c["india"]["summary"].update(recall_ex_fraud_pct=76.2),
    lambda c: c["india"]["summary"].update(missed_fraud_masked=4),
    lambda c: c["india"]["uncertainty"]["recall_ex_fraud"].update(n=21),
    lambda c: c["india"]["ensemble_fisher"].update(p_value_one_sided="small"),
    lambda c: c["india"].update(source_url="https://example.com/evidence"),
    lambda c: c.update(captured_at="yesterday"),
    lambda c: c["retired"].update({"us.failures": [c["us"]["summary"][
        "failures_with_data"].__str__()]}),
    lambda c: c["retired"].update({"us.lift": ["5.0"]}),
    lambda c: c["retired"].update({"us.auc": ["about 0.85"]}),
    lambda c: c["retired"].update({"us.auc": []}),
    lambda c: c.pop("retired"),
])
def test_an_out_of_contract_capture_stops_the_build(tmp_path, change):
    root = site_copy(tmp_path)
    write_capture(root, mutated(change))
    found = pn.problems(root)
    assert len(found) == 1 and found[0].startswith(
        "REFUSING without a valid evidence capture"), found
    with pytest.raises(pn.ContractError):
        pn.render(root)


@pytest.mark.parametrize("raw", [
    "", "{", '{"schema": 1, "schema": 2}', '{"x": NaN}',
])
def test_an_unreadable_capture_stops_the_build(tmp_path, raw):
    root = site_copy(tmp_path)
    (root / pn.CAPTURE_PATH).write_text(raw, encoding="utf-8")
    assert pn.problems(root)[0].startswith(
        "REFUSING without a valid evidence capture")


def test_a_missing_capture_stops_the_build_and_writes_nothing(tmp_path):
    root = site_copy(tmp_path)
    (root / pn.CAPTURE_PATH).unlink()
    before = {r: (root / r).read_bytes() for r in REGISTERED}
    assert pn.main(["--root", str(root)]) == 1
    assert pn.main(["--check", "--root", str(root)]) == 1
    assert {r: (root / r).read_bytes() for r in REGISTERED} == before


def served(changes: dict[tuple[str, str], object]) -> dict[str, dict]:
    """The capture as the live API would serve it, with summary edits."""
    responses = pn.as_served(CAPTURE)
    for (market, field), value in changes.items():
        responses[pn.SOURCES[market]]["summary"][field] = value
    return responses


def test_the_served_shape_projects_back_to_the_capture():
    responses = pn.as_served(CAPTURE)
    capture = pn.project(
        responses[pn.SOURCES["us"]], responses[pn.SOURCES["india"]],
        us_sha256=CAPTURE["us"]["response_sha256"],
        india_sha256=CAPTURE["india"]["response_sha256"],
        captured_at=CAPTURE["captured_at"], retired=CAPTURE["retired"])
    assert capture == CAPTURE


@pytest.mark.parametrize("failure", ["network", "contract"])
def test_a_failed_refresh_keeps_the_capture_and_pages(tmp_path, monkeypatch,
                                                      failure):
    root = site_copy(tmp_path)
    before = {r: (root / r).read_bytes() for r in [pn.CAPTURE_PATH, *REGISTERED]}
    responses = served({("india", "recall_ex_fraud_pct"): 90.0})

    def fetch(url):
        if failure == "network":
            raise pn.ContractError(f"{url} could not be fetched: timed out")
        body = json.dumps(responses[url]).encode()
        return body, json.loads(body)

    monkeypatch.setattr(pn, "fetch_response", fetch)
    assert pn.main(["--fetch", "--root", str(root)]) == 1
    after = {r: (root / r).read_bytes() for r in [pn.CAPTURE_PATH, *REGISTERED]}
    assert after == before


@pytest.mark.parametrize("changes,refusal", [
    ({("india", "median_lead_months"): 22.5}, "warning horizon"),
    ({}, "says p < 0.001"),
])
def test_a_refresh_that_would_not_publish_writes_nothing(tmp_path, monkeypatch,
                                                        changes, refusal):
    root = site_copy(tmp_path)
    before = {r: (root / r).read_bytes() for r in [pn.CAPTURE_PATH, *REGISTERED]}
    responses = served(changes)
    if not changes:
        responses[pn.SOURCES["india"]]["ensemble_fisher"][
            "p_value_one_sided"] = 0.002

    def fetch(url):
        body = json.dumps(responses[url]).encode()
        return body, json.loads(body)

    monkeypatch.setattr(pn, "fetch_response", fetch)
    assert pn.main(["--fetch", "--root", str(root)]) == 1
    after = {r: (root / r).read_bytes() for r in [pn.CAPTURE_PATH, *REGISTERED]}
    assert after == before


def test_a_refresh_regenerates_every_page_from_the_new_capture(tmp_path,
                                                               monkeypatch):
    root = site_copy(tmp_path)
    responses = served({("us", "failures_with_data"): 556,
                          ("us", "recall_pct"): 73.3})

    def fetch(url):
        body = json.dumps(responses[url]).encode()
        return body, json.loads(body)

    monkeypatch.setattr(pn, "fetch_response", fetch)
    assert pn.main(["--fetch", "--root", str(root)]) == 0
    home = (root / "index.html").read_text(encoding="utf-8")
    us = (root / "us/index.html").read_text(encoding="utf-8")
    assert "United States · 556 failures since 2008" in home
    assert "<b>73.3%</b> recall" in home
    assert "556 failures since 2008" in us and "554 failures" not in us
    capture = pn.load_capture(root)
    assert capture["us"]["summary"]["failures_with_data"] == 556
    # The superseded figures join the retired set, so a stale copy of
    # either is refused anywhere from now on.
    assert capture["retired"]["us.failures"] == [
        *CAPTURE["retired"]["us.failures"], FIGURES["us.failures"]]
    assert capture["retired"]["us.recall"] == [
        *CAPTURE["retired"]["us.recall"], FIGURES["us.recall"]]
    assert pn.problems(root) == []
    append(root, "index.html", "<p>The record covers 554 FDIC failures.</p>")
    assert any("554 was the published us.failures" in p
               for p in pn.problems(root))


def test_an_unreadable_committed_capture_stops_a_refresh(tmp_path,
                                                         monkeypatch):
    root = site_copy(tmp_path)
    (root / pn.CAPTURE_PATH).write_text("{", encoding="utf-8")
    monkeypatch.setattr(pn, "fetch_response", lambda url: pytest.fail(
        "a refresh must not fetch over an unreadable capture"))
    assert pn.main(["--fetch", "--root", str(root)]) == 1
    assert (root / pn.CAPTURE_PATH).read_text(encoding="utf-8") == "{"


def test_a_figure_that_returns_leaves_the_retired_set():
    previous = mutated(lambda c: c["us"]["summary"].update(
        failures_with_data=556))
    previous["retired"]["us.failures"] = [
        *CAPTURE["retired"]["us.failures"], FIGURES["us.failures"]]
    previous = pn.validate(previous)
    responses = pn.as_served(CAPTURE)

    def fetch(url):
        body = json.dumps(responses[url]).encode()
        return body, json.loads(body)

    capture = pn.fetch_capture(fetch, previous=previous)
    assert capture["retired"]["us.failures"] == [
        *CAPTURE["retired"]["us.failures"], "556"]


class _Response(io.BytesIO):
    def __init__(self, body: bytes, *, status: int = 200, url: str,
                 content_type: str = "application/json"):
        super().__init__(body)
        self.status = status
        self._url = url
        self.headers = {"Content-Type": content_type}

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize("kwargs,message", [
    ({"status": 503}, "answered HTTP 503"),
    ({"content_type": "text/html"}, "not JSON"),
    ({"url": "https://example.com/elsewhere"}, "redirected"),
])
def test_fetch_refuses_anything_but_the_exact_json_answer(monkeypatch, kwargs,
                                                          message):
    url = pn.SOURCES["us"]
    options = {"url": url, **kwargs}
    monkeypatch.setattr(pn.urllib.request, "urlopen",
                        lambda request, timeout: _Response(b"{}", **options))
    with pytest.raises(pn.ContractError, match=message):
        pn.fetch_response(url)


def test_fetch_refuses_an_oversized_body(monkeypatch):
    url = pn.SOURCES["us"]
    monkeypatch.setattr(pn, "MAX_RESPONSE_BYTES", 8)
    monkeypatch.setattr(pn.urllib.request, "urlopen",
                        lambda request, timeout: _Response(b"{" * 9, url=url))
    with pytest.raises(pn.ContractError, match="exceeded"):
        pn.fetch_response(url)


# ------------------------------------------- claims that ride on the record


def test_the_live_api_moving_is_reported_as_drift():
    assert pn.drift(CAPTURE, *pn.as_served(CAPTURE).values()) == []
    moved = served({("us", "failures_with_data"): 556})
    found = pn.drift(CAPTURE, *moved.values())
    assert len(found) == 1 and "us.summary.failures_with_data" in found[0]
    broken = served({("india", "recall_pct"): 99.9})
    assert "out of the capture contract" in pn.drift(CAPTURE,
                                                     *broken.values())[0]


def test_the_fisher_claim_is_checked_against_the_record(tmp_path):
    root = site_copy(tmp_path)
    write_capture(root, mutated(
        lambda c: c["india"]["ensemble_fisher"].update(p_value_one_sided=0.002)))
    assert any("says p < 0.001" in p for p in pn.problems(root))


def test_a_moved_india_median_refuses_until_the_horizon_is_redrawn(tmp_path):
    root = site_copy(tmp_path)
    write_capture(root, mutated(
        lambda c: c["india"]["summary"].update(median_lead_months=22.5)))
    before = {r: (root / r).read_bytes() for r in REGISTERED}
    with pytest.raises(pn.ContractError) as refused:
        pn.render(root)
    message = str(refused.value)
    assert 'set data-month="22.5" data-progress=".451"' in message, message
    assert "left:45.1%" in message, message
    assert {r: (root / r).read_bytes() for r in REGISTERED} == before
    # Drawing the chapter where the message says lets the figures through.
    edit(root, "index.html", 'data-month="21.5" data-progress=".476"',
         'data-month="22.5" data-progress=".451"')
    edit(root, "index.html", 'style="left:47.6%"', 'style="left:45.1%"')
    pn.render(root)
    assert pn.problems(root) == []
    home = (root / "index.html").read_text(encoding="utf-8")
    assert "<b>22.5-month median alert</b>" in home


# ------------------------------------------------ nets, both directions


@pytest.mark.parametrize("snippet,expected", [
    ("<p>The recall was {us.recall}% across the US record.</p>",
     "a recall percentage {us.recall}"),
    ("<p>US recall: {us.recall}%, AUROC {us.auc}.</p>", "an AUC {us.auc}"),
    ("<p>AUC is {us.auc} on the pooled US panel.</p>", "an AUC {us.auc}"),
    ("<p>{us.recall} per cent recall on FDIC failures.</p>",
     "a recall percentage {us.recall}"),
    ("<p>A median lead time of {us.median_lead} months.</p>",
     "a median lead {us.median_lead}"),
    ("<p>{us.failures} U.S. bank failures since 2008.</p>",
     "a US failure count {us.failures}"),
    ("<p>{us.failures} failed banks were replayed.</p>",
     "a US failure count {us.failures}"),
    ("<p>{us.failures}&nbsp;US failures since 2008.</p>",
     "a US failure count {us.failures}"),
    ("<p>{us.failures}\u00a0US failures since 2008.</p>",
     "a US failure count {us.failures}"),
    ("<p>95% CI {us.recall_ci_low}-{us.recall_ci_high}%</p>",
     "a recall interval {us.recall_ci_low}"),
    ("<p>{india.institutions} Indian lenders were replayed.</p>",
     "an India cohort size {india.institutions}"),
    ("<p>The diagnostic stood at {us.recall} on its own.</p>",
     "us.recall {us.recall} is typed into the page"),
    ("<p>The diagnostic once read 72.8 on the record.</p>",
     "72.8 was the published us.recall"),
])
def test_the_nets_catch_other_phrasings(tmp_path, snippet, expected):
    def fill(text: str) -> str:
        return re.sub(r"\{([a-z_.]+)\}", lambda m: FIGURES[m.group(1)], text)

    root = site_copy(tmp_path)
    append(root, "index.html", fill(snippet))
    found = pn.problems(root)
    assert any(fill(expected) in p for p in found), found


@pytest.mark.parametrize("snippet", [
    "<p>A 503 failure means the origin did not answer.</p>",
    "<p>The checker covers 12 institution types.</p>",
    "<p>It serves 120 institution-level screens.</p>",
    "<p>The median alert of 12 venues fired first.</p>",
    "<p>Twelve of 16 venues answered in 2008 failures drills.</p>",
])
def test_the_nets_leave_ordinary_copy_alone(tmp_path, snippet):
    root = site_copy(tmp_path)
    append(root, "index.html", snippet)
    assert pn.problems(root) == []


def test_a_page_in_another_encoding_is_still_read(tmp_path):
    root = site_copy(tmp_path)
    page = root / "guides" / "legacy" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_bytes("<p>Caf\u00e9 note: 552 failures since 2008 and "
                     "72.8% recall.</p>".encode("cp1252"))
    found = pn.problems(root)
    assert any("guides/legacy/index.html:1: a US failure count 552" in p
               for p in found), found


def test_an_edit_beside_a_label_is_refused_not_swallowed(tmp_path):
    root = site_copy(tmp_path)
    label = pn.india_label(FIGURES, "percent")
    edit(root, "llms.txt", f"reports {label} and",
         f"reports {label}. Europe is NAMED_CASE_FILES_CONSTRUCTION_PIT and")
    before = (root / "llms.txt").read_bytes()
    assert any("llms.txt: the registered figure" in p and "appears 0" in p
               for p in pn.problems(root))
    with pytest.raises(pn.ContractError):
        pn.render(root)
    assert (root / "llms.txt").read_bytes() == before
