"""Execute the recipe's actual Code node without n8n, network or model calls."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = json.loads((ROOT / "developers/recipes/n8n-bank-review.json").read_text())
CODE = next(node for node in WORKFLOW["nodes"] if node["type"] == "n8n-nodes-base.code")["parameters"]["jsCode"]
NODE_RUNNER = """
const vm = require('node:vm');
let raw = '';
process.stdin.on('data', part => raw += part);
process.stdin.on('end', () => {
  const { code, items } = JSON.parse(raw);
  try {
    const result = vm.runInNewContext('(function () {' + code + '\\n})()',
      { $input: { all: () => items } }, { timeout: 1000 });
    process.stdout.write(JSON.stringify({ result }));
  } catch (error) {
    process.stdout.write(JSON.stringify({ error: error.message }));
  }
});
"""


def record(status="observed"):
    return {
        "schema": "liquilens.bank-specialisation.v1", "slug": "cosmos-ucb",
        "status": status, "scope": "research", "score_authority": False,
        "can_authorize_credit": False, "as_of": "2026-09-05",
        "period_end": "2026-03-31", "available_at": "2026-09-05T07:05:33Z",
        "retrieved_at": "2026-09-05T07:05:33Z",
        "metrics": {"nnpa_pct": {"value": 0, "status": "observed"},
                    "cet1_pct": {"value": None, "status": "not_disclosed"}},
        "sources": ["https://example.org/public-filing.pdf"],
        "historical_evidence": {"validated_backtest_eligible": False, "real_money_eligible": False},
        "interpretation_limits": ["A zero reported NNPA does not prove zero credit risk."],
    }


@unittest.skipUnless(shutil.which("node"), "Node is required to execute the workflow Code node")
class BankRecipeTests(unittest.TestCase):
    def run_code(self, response=None, *, items=None):
        completed = subprocess.run(
            [shutil.which("node"), "-e", NODE_RUNNER],
            input=json.dumps({"code": CODE, "items": items if items is not None else [{"json": response}]}),
            text=True, capture_output=True, check=True, timeout=5,
        )
        return json.loads(completed.stdout)

    def test_preserves_clocks_missing_values_zero_and_limits_for_all_statuses(self):
        for status in ("observed", "stale", "historical", "unavailable"):
            with self.subTest(status=status):
                evidence = record(status)
                if status == "unavailable":
                    evidence.update(period_end=None, available_at=None, retrieved_at=None, metrics={}, reason="No disclosed record")
                self.assertEqual(self.run_code({"structuredContent": evidence}), {"result": [{"json": evidence}]})

    def test_reads_both_n8n_parsed_text_and_original_mcp_text(self):
        evidence = record()
        for text in (evidence, json.dumps(evidence)):
            self.assertEqual(self.run_code({"content": [{"type": "text", "text": text}]}), {"result": [{"json": evidence}]})

    def test_never_turns_tool_errors_into_a_completed_review(self):
        for failure in ({"isError": True}, {"error": {"message": "tool unavailable"}}):
            failure["structuredContent"] = record()
            self.assertIn("MCP request failed", self.run_code(failure)["error"])

    def test_rejects_malformed_missing_or_wrong_evidence(self):
        for response in ({}, {"structuredContent": []}, {"structuredContent": {"schema": "legacy"}},
                         {"content": [{"type": "text", "text": "not JSON"}]}):
            self.assertIn("error", self.run_code(response))

    def test_rejects_new_authority_and_missing_status(self):
        for key, value in (("scope", "credit"), ("score_authority", True),
                           ("can_authorize_credit", True), ("status", "approved"), ("slug", "")):
            evidence = record()
            evidence[key] = value
            self.assertIn("error", self.run_code({"structuredContent": evidence}))

    def test_rejects_accidental_multi_item_fanout(self):
        item = {"json": {"structuredContent": record()}}
        for items in ([], [item, copy.deepcopy(item)]):
            self.assertIn("one manually requested", self.run_code(items=items)["error"])

    def test_request_matches_the_live_tool_contract_without_automatic_execution(self):
        node = next(node for node in WORKFLOW["nodes"] if node["type"].endswith(".mcpClient"))
        params = node["parameters"]
        arguments = json.loads(params["jsonInput"])
        self.assertEqual(params["tool"]["value"], "bank_asset_quality_review")
        self.assertEqual(arguments["slug"], "cosmos-ucb")
        self.assertIs(type(arguments["include_history"]), bool)
        self.assertEqual(set(arguments), {"slug", "include_history"})
        self.assertEqual((params["authentication"], params["serverTransport"]), ("none", "httpStreamable"))
        self.assertEqual(params["endpointUrl"], "https://api.liquilens.in/mcp")
        self.assertEqual(node["typeVersion"], 1.1)  # 1.0 does not propagate tool errors.
        self.assertFalse(node.get("continueOnFail", False))
        self.assertFalse(node.get("retryOnFail", False))
        self.assertFalse(WORKFLOW["active"])
        self.assertEqual({n["type"] for n in WORKFLOW["nodes"]}, {
            "n8n-nodes-base.manualTrigger", "@n8n/n8n-nodes-langchain.mcpClient",
            "n8n-nodes-base.code", "n8n-nodes-base.stickyNote"})
        self.assertTrue(all("credentials" not in n for n in WORKFLOW["nodes"]))


if __name__ == "__main__":
    unittest.main()
