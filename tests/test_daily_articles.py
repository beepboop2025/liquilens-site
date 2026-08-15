"""Daily editorial cadence and evidence boundaries for LiquiLens."""

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import daily_article  # noqa: E402


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
    )
    assert article["article_type"] == "current_analysis"
    assert article["topic"] == "example-sfb"
    assert article["word_count"] >= 850
    assert article["quality_gate"]["status"] == "PASS"
    assert "market warning is fresher" in article["headline"]
    assert "****" not in article["body_md"]
    assert "forensic lens fired is **none published**" in article["body_md"]


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
    article = daily_article.build_article(
        data, date="2026-08-15", recent_index=[],
        configured_model={"key": "x", "base_url": "https://invalid", "model": "test"},
    )
    assert article["generation"]["mode"] == "deterministic_fallback"
    assert "unsupported numbers" in article["generation"]["fallback_reason"]
    assert "987654321" not in article["body_md"]


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
    assert article["headline"] in (article_dir / article["slug"] / "index.html").read_text()
    assert article["headline"] in (article_dir / "index.html").read_text()
    assert "<feed xmlns=" in (article_dir / "feed.xml").read_text()
    assert article["canonical_url"] in (tmp_path / "sitemap.xml").read_text()
    assert f"{article['slug']}.md" in (tmp_path / "llms.txt").read_text()
    sidecar = json.loads((article_dir / f"{article['slug']}.json").read_text())
    assert sidecar["quality_gate"]["status"] == "PASS"


def test_html_renderer_escapes_untrusted_markup():
    rendered = daily_article.markdown_to_html("A <script>x</script> [bad](javascript:alert(1))")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert 'href="#"' in rendered
