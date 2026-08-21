"""Daily editorial cadence and evidence boundaries for LiquiLens."""

from datetime import datetime, timezone
import json
from html import unescape
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import daily_article  # noqa: E402


class FakeResponse:
    def __init__(self, body: bytes, *, content_length: str | None = None):
        self.body = body
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = content_length

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]


def test_strict_json_rejects_ambiguous_or_nonfinite_values():
    with pytest.raises(ValueError, match="duplicate JSON key"):
        daily_article.strict_json_loads('{"status":"PASS","status":"FAIL"}')
    with pytest.raises(ValueError, match="non-finite JSON value"):
        daily_article.strict_json_loads('{"score":NaN}')


def test_bounded_reader_checks_declared_and_actual_sizes():
    with pytest.raises(ValueError, match="byte budget"):
        daily_article.read_bounded(
            FakeResponse(b"{}", content_length="1025"), 1024, "test response"
        )
    with pytest.raises(ValueError, match="byte budget"):
        daily_article.read_bounded(
            FakeResponse(b"x" * 1025), 1024, "test response"
        )
    assert daily_article.read_bounded(
        FakeResponse(b"{}", content_length="2"), 1024, "test response"
    ) == b"{}"


def test_dataset_fetcher_refuses_unlisted_urls_before_network(monkeypatch):
    monkeypatch.setattr(
        daily_article,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("network should not be reached"),
    )
    with pytest.raises(ValueError, match="not allowlisted"):
        daily_article.fetch_json("https://example.invalid/private")


def test_editorial_model_base_url_requires_a_clean_https_url(monkeypatch):
    monkeypatch.setenv("EDITORIAL_LLM_BASE_URL", "http://127.0.0.1:8080/api")
    with pytest.raises(ValueError, match="must be an HTTPS"):
        daily_article.model_config()

    monkeypatch.setenv(
        "EDITORIAL_LLM_BASE_URL", "https://models.example.test/v1/"
    )
    config = daily_article.model_config()
    assert config is not None
    assert config["base_url"] == "https://models.example.test/v1"


def test_article_index_is_empty_only_when_missing(tmp_path):
    path = tmp_path / "index.json"
    assert daily_article.load_index(path) == []

    path.write_text('[{"slug":"first"},{"slug":"second"}]', encoding="utf-8")
    assert [row["slug"] for row in daily_article.load_index(path)] == [
        "first",
        "second",
    ]

    path.write_text('{"slug":"not-a-list"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="not a list of objects"):
        daily_article.load_index(path)

    path.write_text('{"slug":"one","slug":"two"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid JSON"):
        daily_article.load_index(path)


def datasets():
    evidence_status = {
        "status": "PERIOD_END_PROXY_CONSTRUCTION_PIT",
        "validated_backtest_eligible": False,
        "real_money_eligible": False,
        "filing_lag_days": 60,
    }
    board = {
        "as_of": "2026-08-14",
        "tiers": {"red": 0, "orange": 1, "yellow": 1, "green": 4},
        "excluded_stale": [{"slug": "old-bank"}],
        "historical_evidence": evidence_status,
        "market_layer": {"as_of": "2026-08-11"},
        "method_note": "Only current vetted dossiers are shown.",
        "quadrant_rule": "orange for a material level or deterioration",
        "rows": [{
            "slug": "example-sfb", "name": "Example Small Finance Bank",
            "inst_type": "sfb", "label": "stressed_survivor",
            "as_of": "2025-09-30", "quarter": "FY26Q2",
            "knowledge_time_proxy": "2025-11-29", "age_months": 11,
            "score": 66.0, "grade": "BBB", "tier": "yellow",
            "hazard": {
                "pd_12m": 0.0042, "basis": ["GNPA 8.5%"],
                "historical_evidence": evidence_status,
            },
            "movement": {"delta_pd_12m": 0.0008, "reference": {"from_q": "FY25Q2"}},
            "pca": {
                "framework": None, "status": "not_applicable", "breaches": [],
                "headroom": [{"indicator": "CRAR", "headroom_pp": 5.9}],
                "not_assessed": ["Tier-1 leverage"],
            },
            "funding": {
                "index": 0.0, "band": "stable", "flags": [],
                "dark_lenses": ["wholesale_reliance", "lcr_headroom"],
                "basis": ["worst deposit QoQ +5.3%"],
            },
            "forensics": {"fired": False},
            "market": {
                "dd": 1.927, "pd_merton_1y": 0.02696, "as_of": "2026-08-11",
                "basis": ["market cap Rs 2,056 cr", "sigma_E 42.9%"],
            },
            "signals_fired": ["market_dd_below_2"],
            "peer_percentile": {"universe": 100},
        }],
    }
    validation = {
        "historical_evidence": evidence_status,
        "pca_replay": {
            "summary": {"failed_institutions": 15, "entered_action_zone_first": 5, "median_lead_months": 41},
            "failures": [{
                "slug": "altico", "inst_type": "nbfc", "default_date": "2019-09-20",
                "first_action_zone": None, "lead_months": None, "fraud_masked": False,
            }],
        },
        "funding_replay": {
            "summary": {"failed_institutions": 15, "with_liability_disclosures": 10,
                        "funding_signal_fired_first": 4, "median_lead_months": 38},
            "failures": [{
                "slug": "altico", "inst_type": "nbfc", "scoreable": True,
                "first_signal": {
                    "period_end": "2017-03-31", "knowledge_time_proxy": "2017-05-30",
                    "index": 23.7, "band": "stable", "flags": ["CP reliance 29%"],
                },
                "lead_months": 27,
            }],
        },
        "hazard": {"panel": {"rows": 205, "events": 9, "institutions": 27},
                   "historical_evidence": evidence_status},
    }
    return {
        "board": board,
        "validation": validation,
        "markets": {"markets": [{"key": "india", "institutions": 48,
                                    "historical_evidence": evidence_status}]},
        "ndfi": {"as_of": "2026-03-31", "historical_evidence": evidence_status,
                 "system_context": {"available": False}, "ndfi_watch": []},
        "seiche": {"generated_at": "2026-08-15T04:00:00Z",
                   "editorial": {"thesis": "The calendar leads while cash prices remain calm."},
                   "engines": {"composite": {"value": 45.2, "regime": "STRAIN"}}},
        "undertow": {"asof": "2026-08-15", "segments": {
            "UST": {"tier": "PARTIAL", "candidate_tier": "NORMAL", "n_measures": 19,
                    "n_qualifying": 6, "score_withheld_reason": "failed negative control"}
        }},
    }


def test_first_changed_board_gets_current_analysis():
    article = daily_article.build_article(
        datasets(), date="2026-08-15", recent_index=[], configured_model=None,
        published_at=datetime(2026, 8, 15, 7, 21, 34, tzinfo=timezone.utc),
    )
    assert article["article_type"] == "current_analysis"
    assert article["topic"] == "example-sfb"
    assert article["word_count"] >= 850
    assert article["quality_gate"]["status"] == "PASS"
    assert "market warning is fresher" in article["headline"]
    assert "****" not in article["body_md"]
    assert "forensic lens fired is **none published**" in article["body_md"]
    assert article["published_at"] == "2026-08-15T07:21:34Z"
    assert article["published_at"] != "2026-08-15T11:15:00Z"


def test_unchanged_board_opens_historical_record():
    data = datasets()
    previous = [{"board_signature": daily_article.board_signature(data["board"]),
                 "topic": "some-other-case"}]
    article = daily_article.build_article(
        data, date="2026-08-16", recent_index=previous, configured_model=None,
    )
    assert article["article_type"] == "historical_replay"
    assert article["topic"] == "altico"
    assert "not current news and not a forecast" in article["body_md"]
    assert "construction-PIT" in article["body_md"]


def test_recent_current_topic_cools_down_to_historical_record():
    data = datasets()
    recent = [{
        "board_signature": "different-fingerprint",
        "article_type": "current_analysis",
        "topic": "example-sfb",
        "date": "2026-08-14",
    }]
    article = daily_article.build_article(
        data, date="2026-08-15", recent_index=recent, configured_model=None,
    )
    assert article["article_type"] == "historical_replay"
    assert article["topic"] == "altico"


def test_current_topic_is_eligible_after_cooldown():
    data = datasets()
    older = [{
        "board_signature": "different-fingerprint",
        "article_type": "current_analysis",
        "topic": "example-sfb",
        "date": "2026-08-01",
    }]
    article = daily_article.build_article(
        data, date="2026-08-15", recent_index=older, configured_model=None,
    )
    assert article["article_type"] == "current_analysis"
    assert article["topic"] == "example-sfb"


def test_model_cannot_publish_an_invented_number(monkeypatch):
    data = datasets()
    safe = daily_article.build_article(
        data, date="2026-08-15", recent_index=[], configured_model=None,
    )

    def invented(_dossier, _config):
        return {
            "headline": safe["headline"], "dek": safe["dek"],
            "body_md": safe["body_md"] + "\nDeposits vanished by 987654321%.",
            "review_notes": [],
        }

    monkeypatch.setattr(daily_article, "draft_with_model", invented)
    monkeypatch.setattr(
        daily_article, "repair_with_model",
        lambda _dossier, candidate, _failures, _config: candidate,
    )
    article = daily_article.build_article(
        data, date="2026-08-15", recent_index=[],
        configured_model={"key": "x", "base_url": "https://invalid", "model": "test"},
    )
    assert article["generation"]["mode"] == "deterministic_fallback"
    assert "unsupported numbers" in article["generation"]["fallback_reason"]
    assert "987654321" not in article["body_md"]


def test_gate_feedback_can_repair_copy(monkeypatch):
    data = datasets()
    safe = daily_article.build_article(
        data, date="2026-08-15", recent_index=[], configured_model=None,
    )
    rejected = {
        "headline": safe["headline"], "dek": safe["dek"],
        "body_md": safe["body_md"] + "\nDeposits vanished by 987654321%.",
        "review_notes": [],
    }
    observed_failures = []
    monkeypatch.setattr(daily_article, "draft_with_model", lambda *_args: rejected)

    def repair(_dossier, _candidate, failures, _config):
        observed_failures.extend(failures)
        return {
            "headline": safe["headline"], "dek": safe["dek"],
            "body_md": safe["body_md"].replace("12-month", "one-year"),
            "review_notes": ["Removed unsupported copy."],
        }

    monkeypatch.setattr(daily_article, "repair_with_model", repair)
    article = daily_article.build_article(
        data, date="2026-08-15", recent_index=[],
        configured_model={"key": "x", "base_url": "https://invalid", "model": "test"},
    )
    assert any("unsupported numbers" in issue for issue in observed_failures)
    assert article["generation"]["mode"] == "model_assisted"
    assert article["generation"]["passes"] == 3


def test_boundary_overlay_adds_only_fixed_disclosures():
    candidate = {"headline": "Held", "dek": "Held", "body_md": "Evidence-led copy."}
    overlaid, applied = daily_article.apply_boundary_overlay(
        candidate, article_type="historical_replay",
    )
    assert applied == [
        "historical_news_and_forecast_boundary",
        "not_a_credit_rating",
        "not_investment_advice",
    ]
    assert overlaid["headline"] == candidate["headline"]
    assert "not current news and not a forecast" in overlaid["body_md"].lower()
    assert "not a credit rating" in overlaid["body_md"].lower()
    assert "not investment advice" in overlaid["body_md"].lower()


def test_write_builds_page_archive_feed_and_discovery(tmp_path):
    (tmp_path / "sitemap.xml").write_text(
        '<?xml version="1.0"?><urlset><url><loc>https://liquilens.in/</loc></url></urlset>\n'
    )
    (tmp_path / "llms.txt").write_text("# LiquiLens\n")
    article = daily_article.build_article(
        datasets(), date="2026-08-15", recent_index=[], configured_model=None,
    )
    daily_article.write_article(article, root=tmp_path)
    article_dir = tmp_path / "articles"
    article_page = (article_dir / article["slug"] / "index.html").read_text()
    assert article["headline"] in article_page
    assert "/tools/ews-coverage-check/?utm_source=liquilens" in article_page
    assert "/access/?utm_source=liquilens" in article_page
    title = re.search(r"<title>(.*?)</title>", article_page).group(1)
    description = re.search(
        r'<meta name="description" content="(.*?)">', article_page
    ).group(1)
    assert len(unescape(title)) <= 63
    assert len(unescape(description)) <= 155
    assert '<meta name="twitter:card" content="summary_large_image">' in article_page
    assert article["headline"] in (article_dir / "index.html").read_text()
    assert "<feed xmlns=" in (article_dir / "feed.xml").read_text()
    json_feed = json.loads((article_dir / "feed.json").read_text())
    assert json_feed["version"] == "https://jsonfeed.org/version/1.1"
    assert json_feed["items"][0]["content_text"] == article["body_md"]
    assert json_feed["items"][0]["_liquidity_lab"]["quality_gate"]["status"] == "PASS"
    assert article["canonical_url"] in (tmp_path / "sitemap.xml").read_text()
    assert f"{article['slug']}.md" in (tmp_path / "llms.txt").read_text()
    sidecar = json.loads((article_dir / f"{article['slug']}.json").read_text())
    assert sidecar["quality_gate"]["status"] == "PASS"
    learning = json.loads((article_dir / "learning.json").read_text())
    assert learning["schema"] == "editorial.learning-feed.v1"
    assert learning["authority"]["training_allowed"] is False
    assert learning["articles"][0]["body_markdown"] == article["body_md"]


def test_html_renderer_escapes_untrusted_markup():
    rendered = daily_article.markdown_to_html("A <script>x</script> [bad](javascript:alert(1))")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert 'href="#"' in rendered


def test_tag_only_editorial_memory_is_bound_and_applied():
    identity = {
        "schema": "mqdnse.editorial-memory.v1",
        "generated_at": "2026-08-15T09:00:00Z",
        "source_run_id": "sha256:" + "a" * 64,
        "source_manifest_sha256": "sha256:" + "b" * 64,
        "rubric_version": "mqdnse.editorial-rubric.v1",
        "global_directives": ["show_mechanism"],
        "products": {
            "liquilens": {
                "articleId": "liquilens:article:prior",
                "articleRevisionSha256": "sha256:" + "c" * 64,
                "criticStatus": "validated_shadow_critique",
                "verdict": "publishable",
                "score": 12,
                "directives": ["tighten_evidence_boundary"],
            }
        },
        "authority": daily_article.EDITORIAL_MEMORY_AUTHORITY,
    }
    payload = {**identity, "memory_fingerprint": daily_article.memory_sha(identity)}
    memory = daily_article.validate_editorial_memory(
        payload,
        now=datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
    )
    article = daily_article.build_article(
        datasets(),
        date="2026-08-15",
        recent_index=[],
        configured_model=None,
        editorial_memory=memory,
    )

    assert memory["directives"] == ["tighten_evidence_boundary", "show_mechanism"]
    assert article["generation"]["editorial_memory"] == memory
    assert article["quality_gate"]["status"] == "PASS"
