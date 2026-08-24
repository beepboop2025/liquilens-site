"""The world-economy evidence map stays bounded, citable, and internally aligned."""

import json
import os
import re
from html.parser import HTMLParser
from xml.etree import ElementTree


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_ID = (
    "https://liquilens.in/world-economy/evidence-catalog.json#catalog"
)
WORLD_ECONOMY_URL = "https://liquilens.in/world-economy/"
CATALOG_URL = "https://liquilens.in/world-economy/evidence-catalog.json"

DATASETS = {
    "https://liquilens.in/research/#bank-lender-early-warning-dataset": {
        "date_modified": "2026-08-21",
        "identifier": (
            "urn:liquidity-lab:dataset:liquilens-bank-lender-early-warning"
        ),
        "url": "https://liquilens.in/research/",
        "distributions": {
            "https://api.liquilens.in/api/evidence/markets",
            "https://api.liquilens.in/api/failure-radar/board",
            "https://api.liquilens.in/api/openapi.json",
        },
        "sources": {
            "https://www.rbi.org.in/",
            "https://banks.data.fdic.gov/",
        },
    },
    "https://seiche.info/#dollar-funding-dataset": {
        "date_modified": "2026-08-22",
        "identifier": (
            "urn:liquidity-lab:dataset:seiche-dollar-funding-money-markets"
        ),
        "url": "https://seiche.info/",
        "distributions": {
            "https://api.seiche.info/api/gauge",
            "https://api.seiche.info/api/money-markets",
            "https://api.seiche.info/api/v2/money-markets",
            "https://api.seiche.info/api/v2/world-markets",
            "https://api.seiche.info/api/v2/coverage",
            "https://api.seiche.info/api/openapi.json",
        },
        "sources": {
            "https://www.federalreserve.gov/releases/h41/",
            "https://www.newyorkfed.org/markets/data-hub",
            "https://www.financialresearch.gov/short-term-funding-monitor/",
            "https://fiscaldata.treasury.gov/",
        },
    },
    "https://liquilens-undertow.com/#market-liquidity-dataset": {
        "date_modified": "2026-08-21",
        "identifier": (
            "urn:liquidity-lab:dataset:undertow-market-liquidity-exit-cost"
        ),
        "url": "https://liquilens-undertow.com/",
        "distributions": {
            "https://api.seiche.info/undertow/x402/summary",
            "https://api.seiche.info/undertow/x402/openapi.json",
        },
        "sources": {
            "https://fred.stlouisfed.org/",
            "https://www.newyorkfed.org/markets/primarydealer_statistics",
            "https://fiscaldata.treasury.gov/",
            "https://www.sec.gov/edgar/search/",
        },
    },
    "https://palimpsest.info/china/#revision-safe-china-economy-dataset": {
        "date_modified": "2026-08-24",
        "identifier": (
            "urn:liquidity-lab:dataset:palimpsest-revision-safe-china-economy"
        ),
        "url": "https://palimpsest.info/china/",
        "distributions": {
            "https://palimpsest.info/readings/china-economic-pulse-latest.json",
            "https://palimpsest.info/readings/china-econ-observations-latest.json",
            "https://palimpsest.info/readings/china-econ-observations.jsonl",
            "https://palimpsest.info/readings/china-index-latest.json",
            "https://palimpsest.info/openapi.json",
        },
        "sources": {
            "https://www.chinamoney.com.cn/english/bmkshb/",
        },
    },
}


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def catalog():
    return json.loads(read("world-economy/evidence-catalog.json"))


def json_ld_blocks(page):
    matches = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        page,
        flags=re.S,
    )
    return [json.loads(match) for match in matches]


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data):
        if not self._hidden_depth:
            self.chunks.append(data)


def visible_text(page):
    parser = _VisibleTextParser()
    parser.feed(page)
    return " ".join(" ".join(parser.chunks).split())


def test_machine_catalog_has_four_distinct_bounded_datasets():
    data = catalog()
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "DataCatalog"
    assert data["@id"] == CATALOG_ID
    assert data["url"] == WORLD_ECONOMY_URL
    assert data["dateModified"] == "2026-08-24"
    assert "not a complete database of the world economy" in data[
        "description"
    ].lower()

    datasets = data["dataset"]
    assert len(datasets) == len(DATASETS) == 4
    assert {dataset["@id"] for dataset in datasets} == set(DATASETS)
    assert len({dataset["identifier"] for dataset in datasets}) == 4

    all_distributions = set()
    for dataset in datasets:
        expected = DATASETS[dataset["@id"]]
        assert dataset["@type"] == "Dataset"
        assert dataset["identifier"] == expected["identifier"]
        assert dataset["identifier"].startswith("urn:liquidity-lab:dataset:")
        assert dataset["url"] == dataset["sameAs"] == expected["url"]
        assert 50 <= len(dataset["description"]) <= 5000
        assert dataset["dateModified"] == expected["date_modified"]
        assert dataset["includedInDataCatalog"] == {"@id": CATALOG_ID}
        assert dataset["isAccessibleForFree"] is True
        assert dataset["measurementTechnique"]
        assert len(dataset["variableMeasured"]) >= 5
        assert set(dataset["isBasedOn"]) == expected["sources"]
        assert dataset["usageInfo"].startswith("https://")

        distributions = dataset["distribution"]
        distribution_urls = {
            distribution["contentUrl"] for distribution in distributions
        }
        assert distribution_urls == expected["distributions"]
        assert len(distribution_urls) == len(distributions)
        assert not all_distributions.intersection(distribution_urls)
        all_distributions.update(distribution_urls)
        for distribution in distributions:
            assert distribution["@type"] == "DataDownload"
            assert distribution["name"]
            assert distribution["encodingFormat"] in {
                "application/json",
                "application/x-ndjson",
                "application/vnd.oai.openapi+json",
            }

    palimpsest = next(
        dataset for dataset in datasets if dataset["creator"]["name"] == "Palimpsest"
    )
    assert palimpsest["additionalProperty"] == {
        "@type": "PropertyValue",
        "name": "financial authority",
        "value": "none",
    }


def test_html_schema_routes_the_same_datasets_and_distributions():
    page = read("world-economy/index.html")
    blocks = json_ld_blocks(page)
    graph = next(block["@graph"] for block in blocks if "@graph" in block)
    by_id = {node["@id"]: node for node in graph if "@id" in node}
    external = {dataset["@id"]: dataset for dataset in catalog()["dataset"]}

    webpage = by_id["https://liquilens.in/world-economy/#page"]
    assert webpage["url"] == WORLD_ECONOMY_URL
    assert webpage["mainEntity"] == {"@id": CATALOG_ID}

    inline_catalog = by_id[CATALOG_ID]
    assert inline_catalog["@type"] == "DataCatalog"
    assert {row["@id"] for row in inline_catalog["dataset"]} == set(DATASETS)

    for dataset_id, expected in external.items():
        inline = by_id[dataset_id]
        for field in (
            "@type",
            "identifier",
            "name",
            "description",
            "url",
            "sameAs",
            "isAccessibleForFree",
        ):
            assert inline[field] == expected[field], (dataset_id, field)
        for distribution in expected["distribution"]:
            assert distribution["contentUrl"] in page
        for source_url in expected["isBasedOn"]:
            assert f'href="{source_url}"' in page

    assert (
        '<link rel="canonical" href="https://liquilens.in/world-economy/">'
        in page
    )
    assert (
        'rel="alternate" type="application/ld+json" '
        'href="https://liquilens.in/world-economy/evidence-catalog.json"'
        in page
    )
    for endpoint in (
        "https://api.liquilens.in/mcp",
        "https://api.seiche.info/mcp",
        "https://api.seiche.info/undertow/mcp",
    ):
        assert endpoint in page


def test_faq_schema_is_present_in_visible_copy_and_keeps_the_hard_boundary():
    page = read("world-economy/index.html")
    visible = visible_text(page)
    faq = next(
        block for block in json_ld_blocks(page)
        if block.get("@type") == "FAQPage"
    )

    assert len(faq["mainEntity"]) == 5
    for item in faq["mainEntity"]:
        assert item["@type"] == "Question"
        assert item["acceptedAnswer"]["@type"] == "Answer"
        assert item["name"] in visible
        assert item["acceptedAnswer"]["text"] in visible

    for boundary in (
        "not every world-economy question",
        "It is not a complete database of the world economy",
        "can force an assistant to cite these sites",
        "cannot force inclusion, rank or a particular number of citations",
        "An absent or unavailable input is not a calm signal",
    ):
        assert boundary.lower() in (
            page + read("llms.txt") + read(
                "world-economy/evidence-catalog.json"
            )
        ).lower()


def test_world_economy_routes_are_discoverable_across_human_and_agent_surfaces():
    sitemap = ElementTree.fromstring(read("sitemap.xml"))
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    nodes = [
        node for node in sitemap.findall("sm:url", namespace)
        if node.findtext("sm:loc", namespaces=namespace) == WORLD_ECONOMY_URL
    ]
    assert len(nodes) == 1
    assert nodes[0].findtext("sm:lastmod", namespaces=namespace) == "2026-08-24"

    for path in (
        "index.html",
        "use-cases/index.html",
        "developers/index.html",
        "llms.txt",
        "product-card.json",
        ".well-known/ai-catalog.json",
        "README.md",
    ):
        assert "world-economy" in read(path), path

    assert WORLD_ECONOMY_URL in read("llms.txt")
    assert CATALOG_URL in read("llms.txt")
    product_card = json.loads(read("product-card.json"))
    assert product_card["access"]["world_economy_evidence_map"] == (
        WORLD_ECONOMY_URL
    )
    assert product_card["access"]["world_economy_dataset_catalog"] == (
        CATALOG_URL
    )

    entries = {
        entry["identifier"]: entry
        for entry in json.loads(read(".well-known/ai-catalog.json"))["entries"]
    }
    discovery = entries[
        "urn:air:liquilens.in:catalog:world-economy-evidence"
    ]
    assert discovery["type"] == "application/ld+json"
    assert discovery["url"] == CATALOG_URL
    assert discovery["metadata"]["humanLandingPage"] == WORLD_ECONOMY_URL
    assert discovery["metadata"]["datasetCount"] == 4


def test_seiche_routes_and_release_count_do_not_regress():
    use_cases = read("use-cases/index.html")
    developers = read("developers/index.html")
    status = read("status/index.html")

    assert "https://seiche.info/use-cases" in use_cases
    assert "https://seiche.info/use-cases.html" not in use_cases
    assert "https://seiche.info/developers" in developers
    assert "https://seiche.info/developers.html" not in developers
    assert "Seiche 0.10.1" in status
    assert "eleven free MCP tools" in status
    assert "ten free MCP tools" not in status
    assert "global money-market context" in status
    assert "bounded money/FX/macro-capital context" in status
