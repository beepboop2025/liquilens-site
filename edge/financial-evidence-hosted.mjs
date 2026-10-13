// Transport destinations are separate from the original evidence provenance.
const SOURCE_DATASETS = Object.freeze({
  "https://api.seiche.info/api/v2/money-markets": "seiche.money_markets",
  "https://api.seiche.info/api/v2/world-markets?section=capital_markets": "seiche.capital_markets",
  "https://www.palimpsest.info/readings/china-index-latest.json": "palimpsest.china_index",
  "https://api.seiche.info/api/v2/world-markets?section=china_macro": "seiche.china_macro",
  "https://api.liquilens.in/api/failure-radar/board": "liquilens.failure_radar",
  "https://api.seiche.info/undertow/x402/summary": "undertow.summary",
  "https://api.seiche.info/api/v2/gift-city": "seiche.gift_city",
  "https://api.seiche.info/api/v2/world-markets?section=forex": "seiche.forex",
});

export function hostedEndpoint(sourceUrl) {
  if (!Object.hasOwn(SOURCE_DATASETS, sourceUrl)) {
    throw new Error("source URL is outside the hosted dataset catalog");
  }
  return `https://agents.seiche.info/v1/data/${SOURCE_DATASETS[sourceUrl]}`;
}
