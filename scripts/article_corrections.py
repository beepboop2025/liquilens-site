#!/usr/bin/env python3
"""Add dated correction and update notes to published articles, and keep them.

Articles are dated publications. When the record an article cites changes,
its text stays as published and gains a short dated note at the top saying
what changed and why. A fact the article stated wrongly is corrected in place,
and the note says so. Notes live in the article's Markdown, so the page, the
.md file and every feed carry them, and a daily surface refresh keeps them.

Two notes are registered for the November 2026 India correction:

  co-operative-bank-onset   a Correction on every article that quoted the
                            pre-correction India figures or stated a
                            licence-cancellation date as a default date
  failure-radar-tier-pause  an Update on every other article that shows
                            Failure Radar tier states, while tiers are paused

    python3 scripts/article_corrections.py                  apply both notes
    python3 scripts/article_corrections.py --check          fail on any drift
    python3 scripts/article_corrections.py --date YYYY-MM-DD redate the notes
    python3 scripts/article_corrections.py --refreeze       re-read the figures
                                                           from the capture (only
                                                           before notes publish)

After applying, rebuild the pages and feeds with
`python3 scripts/daily_article.py --refresh-surfaces`.

Each note is recorded once in articles/corrections/<id>.json. The regenerated
figures and onset dates are read from the India evidence capture
(tests/fixtures/india-evidence.json) when that record is first written, then
frozen: a published note does not move when a later capture changes. Only an
explicit --date or --refreeze rewrites the notes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import date as Date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
CAPTURE = ROOT / "tests" / "fixtures" / "india-evidence.json"
SITE = "https://liquilens.in"

CORRECTION_ID = "co-operative-bank-onset"
UPDATE_ID = "failure-radar-tier-pause"
NOTE_LEAD = "**Correction, "
UPDATE_LEAD = "**Update, "
NOTE_LEADS = (NOTE_LEAD, UPDATE_LEAD)
DEFAULT_DATE = "2026-11-03"
DECISION_DATE = "2026-11-02"

# The three failures re-dated from licence cancellation to onset, each with
# the RBI release that states the onset. The previous dates are what the old
# record served; the onset dates are read from the capture.
ONSETS = (
    {
        "slug": "madhavpura-mercantile-co-operative-bank",
        "name": "Madhavpura Mercantile Co-operative Bank",
        "previous_date": "2012-06-04",
        "source_label": "7 June 2012",
        "source_url": "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=26606",
    },
    {
        "slug": "ckp-co-operative-bank",
        "name": "CKP Co-operative Bank",
        "previous_date": "2020-04-30",
        "source_label": "5 May 2014",
        "source_url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=31124",
    },
    {
        "slug": "rupee-co-operative-bank",
        "name": "Rupee Co-operative Bank",
        "previous_date": "2022-09-22",
        "source_label": "25 February 2013",
        "source_url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=28200",
    },
)

# The India headline the affected articles quoted, as served before the
# correction. An article is affected when its body quotes either figure.
PREVIOUS = {"recall_ex_fraud_pct": 88.9, "median_lead_months": 21.5}
CITES_RECALL = re.compile(r"(?<![\d.])88\.9(?:%| percent)")
CITES_LEAD = re.compile(r"(?<![\d.])21\.5[*`]*[- ]months?\b")
TIER_WORD = r"(?:red|orange|yellow|green)"
MENTIONS_TIERS = re.compile(
    rf"\b\d+\*{{0,2}}\s+{TIER_WORD}\b"
    rf"|\b{TIER_WORD}\b[^.\n]{{0,40}}\btiers?\b|\btiers?\b[^.\n]{{0,40}}\b{TIER_WORD}\b"
    rf"|\b{TIER_WORD}[- ](?:tier|watch|names?|rows?|institutions?)\b",
    re.I,
)

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
ONSET_SUMMARY = (
    "Three co-operative bank failures in the India crisis record are dated at their onset, "
    "the first RBI directions restricting depositors, instead of the later licence "
    "cancellation. The India figures were regenerated, and Failure Radar tier publication "
    "is paused pending re-validation."
)
UPDATE_SUMMARY = (
    "Failure Radar tier publication is paused pending re-validation, after three "
    "co-operative bank failures in the India crisis record were re-dated to their onset. "
    "Tier states and counts in dated articles are as served on their publication date."
)


def long_date(iso: str) -> str:
    day = Date.fromisoformat(iso)
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def compact(value: float) -> str:
    text = f"{float(value):.1f}"
    return text[:-2] if text.endswith(".0") else text


def registry_path(note_id: str) -> Path:
    return ARTICLES / "corrections" / f"{note_id}.json"


def registry_url(note_id: str) -> str:
    return f"{SITE}/articles/corrections/{note_id}.json"


def frozen_record() -> dict:
    """The regenerated figures and onset dates, read from the capture once."""
    raw = CAPTURE.read_bytes()
    evidence = json.loads(raw)
    by_slug = {row["slug"]: row for row in evidence["institutions"]}
    onsets = []
    for onset in ONSETS:
        row = by_slug[onset["slug"]]
        if row["default_date"] == onset["previous_date"]:
            raise ValueError(f"{onset['slug']}: the capture still serves the licence-cancellation date")
        if row["verdict"] != "insufficient_data":
            raise ValueError(f"{onset['slug']}: the capture no longer reports insufficient data")
        onsets.append({**onset, "onset_date": row["default_date"], "verdict": row["verdict"]})
    ex = evidence["uncertainty"]["recall_ex_fraud"]
    summary = evidence["summary"]
    return {
        "onsets": onsets,
        "record": {
            "source": "https://api.liquilens.in/api/evidence/summary",
            "capture_sha256": hashlib.sha256(raw).hexdigest(),
            "recall_ex_fraud_pct": summary["recall_ex_fraud_pct"],
            "flagged_ex_fraud": ex["k"],
            "failed_ex_fraud": ex["n"],
            "median_lead_months": summary["median_lead_months"],
            "previous": dict(PREVIOUS),
        },
    }


def load_registries(note_date: str | None, refreeze: bool = False) -> tuple[dict, dict]:
    path = registry_path(CORRECTION_ID)
    if path.exists():
        onset = json.loads(path.read_text(encoding="utf-8"))
        if refreeze:
            onset.update(frozen_record())
    else:
        onset = {
            "schema": "liquilens.article-correction.v1", "id": CORRECTION_ID, "kind": "correction",
            "date": DEFAULT_DATE, "decision_date": DECISION_DATE, "summary": ONSET_SUMMARY,
            **frozen_record(),
            "tier_publication": "paused pending re-validation; probabilities are research only",
            "articles": [],
        }
    path = registry_path(UPDATE_ID)
    if path.exists():
        update = json.loads(path.read_text(encoding="utf-8"))
    else:
        update = {
            "schema": "liquilens.article-correction.v1", "id": UPDATE_ID, "kind": "update",
            "date": DEFAULT_DATE, "decision_date": DECISION_DATE, "summary": UPDATE_SUMMARY,
            "related": registry_url(CORRECTION_ID),
            "tier_publication": "paused pending re-validation; probabilities are research only",
            "articles": [],
        }
    if note_date:
        Date.fromisoformat(note_date)
        onset["date"] = update["date"] = note_date
    return onset, update


def onset_sentence(registry: dict) -> str:
    parts = [f"{o['name']} on {long_date(o['onset_date'])} (previously {long_date(o['previous_date'])})"
             for o in registry["onsets"]]
    sources = [f"[{o['source_label']}]({o['source_url']})" for o in registry["onsets"]]
    return (
        "LiquiLens now dates three co-operative bank failures in its India crisis record at their "
        "onset, the first RBI directions restricting depositors, instead of the later licence "
        f"cancellation: {parts[0]}, {parts[1]} and {parts[2]}. Sources: RBI press releases of "
        f"{sources[0]}, {sources[1]} and {sources[2]}. Each bank's only scored filing fell after "
        "its onset, so all three are now unscored for insufficient data rather than flagged."
    )


def render_note(registry: dict, flags: dict) -> str:
    record = registry["record"]
    previous = record["previous"]
    sentences = [onset_sentence(registry)]
    for fix in flags["dates_corrected"]:
        sentences.append(
            f"This article originally gave {fix['from']}, the day {fix['name']}'s licence "
            f"cancellation took effect, as its default date; the text below now gives {fix['to']}.")
    recall_from = f"{compact(previous['recall_ex_fraud_pct'])}%"
    recall_to = (f"{compact(record['recall_ex_fraud_pct'])}% ({record['flagged_ex_fraud']} of "
                 f"{record['failed_ex_fraud']})")
    lead_from = compact(previous["median_lead_months"])
    lead_to = f"{compact(record['median_lead_months'])} months"
    if flags["cites_recall"] and flags["cites_lead"]:
        sentences.append(
            "The India figures cited below were regenerated: the share of non-fraud failures "
            f"flagged moved from {recall_from} to {recall_to}, and the median lead from "
            f"{lead_from} to {lead_to}.")
    elif flags["cites_recall"]:
        sentences.append(
            "The share of non-fraud failures flagged that this article cites moved from "
            f"{recall_from} to {recall_to} on the regenerated record.")
    elif flags["cites_lead"]:
        sentences.append(
            f"The median lead this article cites moved from {lead_from} to {lead_to} on the "
            "regenerated record.")
    if flags["mentions_tiers"]:
        sentences.append("Failure Radar tiers are now paused pending re-validation.")
    sentences.append("Board states and validation statistics below are as served on the publication "
                     "date, and the text is otherwise as published.")
    return f"{NOTE_LEAD}{long_date(registry['date'])}.** " + " ".join(sentences)


def render_update(registry: dict) -> str:
    return (
        f"{UPDATE_LEAD}{long_date(registry['date'])}.** Failure Radar tier publication is paused "
        "pending re-validation, after three co-operative bank failures in the India crisis record "
        "were re-dated to their onset. The tier states and counts below are as served on the "
        "publication date. They are not a current reading, and they do not show that any "
        "institution is safe. The text is otherwise as published."
    )


def plain(note: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", note)
    return text.replace("**", "")


def article_flags(body: str, previous_entry: dict | None) -> dict:
    """What the published text cites, read from the article itself."""
    if previous_entry is not None:
        fixed = previous_entry.get("dates_corrected", [])
    else:
        fixed = [{"bank": o["slug"], "name": o["name"], "from": o["previous_date"], "to": None}
                 for o in ONSETS if o["previous_date"] in body]
    return {
        "cites_recall": bool(CITES_RECALL.search(body)),
        "cites_lead": bool(CITES_LEAD.search(body)),
        "mentions_tiers": bool(MENTIONS_TIERS.search(body)),
        "dates_corrected": fixed,
    }


def strip_note(body: str, entry: dict | None) -> str:
    if entry and entry.get("note") and body.startswith(entry["note"]):
        return body[len(entry["note"]):].lstrip("\n")
    return body


def entry_for(registry: dict, note: str, **extra) -> dict:
    return {
        "id": registry["id"], "kind": registry["kind"], "date": registry["date"],
        "url": registry_url(registry["id"]), "summary": registry["summary"],
        "note": note, "text": plain(note), **extra,
    }


def annotate(slug: str, body: str, sidecar: dict, onset: dict, update: dict):
    """Return (new body, new sidecar, note id, listing) or None for an unaffected article."""
    entries = {e.get("id"): e for e in sidecar.get("corrections") or []}
    text = body
    for note_id in (CORRECTION_ID, UPDATE_ID):
        text = strip_note(text, entries.get(note_id))
    flags = article_flags(text, entries.get(CORRECTION_ID))
    held = copy.deepcopy(sidecar)
    others = [e for e in held.get("corrections") or [] if e.get("id") not in (CORRECTION_ID, UPDATE_ID)]
    if flags["cites_recall"] or flags["cites_lead"] or flags["dates_corrected"]:
        onset_by_slug = {o["slug"]: o for o in onset["onsets"]}
        for fix in flags["dates_corrected"]:
            row = onset_by_slug[fix["bank"]]
            fix["to"] = row["onset_date"]
            text = text.replace(row["previous_date"], row["onset_date"])
            subject = held.get("subject") if isinstance(held.get("subject"), dict) else {}
            if subject.get("slug") == row["slug"]:
                for block in (subject, subject.get("pca") if isinstance(subject.get("pca"), dict) else {}):
                    if block.get("default_date") == row["previous_date"]:
                        block["default_date"] = row["onset_date"]
        note = render_note(onset, flags)
        held["corrections"] = others + [entry_for(onset, note, dates_corrected=flags["dates_corrected"])]
        listing = {
            "slug": slug, "url": f"{SITE}/articles/{slug}/",
            "cites_recall": flags["cites_recall"], "cites_lead": flags["cites_lead"],
            "mentions_tiers": flags["mentions_tiers"],
            "dates_corrected": [{"from": f["from"], "to": f["to"]} for f in flags["dates_corrected"]],
        }
        return note + "\n\n" + text, held, CORRECTION_ID, listing
    if flags["mentions_tiers"]:
        note = render_update(update)
        held["corrections"] = others + [entry_for(update, note)]
        return note + "\n\n" + text, held, UPDATE_ID, {"slug": slug, "url": f"{SITE}/articles/{slug}/"}
    return None


def dump(value: dict) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def run(*, check: bool, note_date: str | None = None, refreeze: bool = False) -> list[str]:
    onset, update = load_registries(None if check else note_date, refreeze=refreeze and not check)
    problems: list[str] = []
    listings: dict[str, list] = {CORRECTION_ID: [], UPDATE_ID: []}
    writes: dict[Path, str] = {}
    for md in sorted(ARTICLES.glob("2026-*.md")):
        slug = md.stem
        sidecar_path = ARTICLES / f"{slug}.json"
        body = md.read_text(encoding="utf-8")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        result = annotate(slug, body, sidecar, onset, update)
        if result is None:
            continue
        new_body, new_sidecar, note_id, listing = result
        listings[note_id].append(listing)
        text_after_note = new_body.split("\n\n", 1)[1]
        for row in onset["onsets"]:
            if row["previous_date"] in text_after_note:
                problems.append(f"{slug}: the text still states {row['previous_date']}")
            if row["previous_date"] in json.dumps(new_sidecar.get("subject")):
                problems.append(f"{slug}: the sidecar subject still states {row['previous_date']}")
        writes[md] = new_body
        writes[sidecar_path] = dump(new_sidecar)
    writes[registry_path(CORRECTION_ID)] = dump({**onset, "articles": listings[CORRECTION_ID]})
    writes[registry_path(UPDATE_ID)] = dump({**update, "articles": listings[UPDATE_ID]})
    for path, content in writes.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if check:
            problems.append(f"{path.relative_to(ROOT)}: a note or its record differs; "
                            "run scripts/article_corrections.py")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when a note or record drifts")
    parser.add_argument("--date", help="rewrite the note date (YYYY-MM-DD), for example at publication")
    parser.add_argument("--refreeze", action="store_true",
                        help="re-read the regenerated figures and onset dates from the capture")
    args = parser.parse_args(argv)
    if args.check and (args.date or args.refreeze):
        parser.error("--date and --refreeze rewrite notes; they cannot be combined with --check")
    problems = run(check=args.check, note_date=args.date, refreeze=args.refreeze)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems and not args.check:
        print("notes applied; now run: python3 scripts/daily_article.py --refresh-surfaces")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
