import test from 'node:test';
import assert from 'node:assert/strict';
import {coverageRows} from '../agents/source-data.mjs';
import {configuration} from '../start/core.mjs';

test('coverage preserves zero, missingness, clocks and source restrictions', () => {
  const rows = coverageRows({schema: 'liquilens.research-data.v1', datasets: [
    {id: 'a', available: 0, series_count: 3, latest_observation: '2026-06-30', last_success: '2026-09-26T01:00:00Z',
      refresh_state: 'current', observation_state: 'stale', metadata: {source_url: 'https://example.org/data', rights_state: 'source_native_unverified'}},
    {id: 'b', available: null, series_count: null, metadata: {source_url: 'javascript:alert(1)'}},
  ]});
  assert.deepEqual(rows[0].cells, ['0', '3', '2026-06-30', '2026-09-26T01:00:00Z', 'current collection / stale observations']);
  assert.equal(rows[1].cells[0], 'Not published');
  assert.equal(rows[1].source, null);
  assert.equal(rows[0].rights, 'source_native_unverified');
});

test('source history connection is generated for every supported client', () => {
  for (const client of ['hermes','openclaw','claude','codex','cursor','vscode']) {
    assert.match(configuration(client, ['research-data']), /https:\/\/api\.seiche\.info\/api\/v2\/research-data\/mcp/);
  }
});

test('unknown catalog format never becomes an empty healthy table', () => {
  assert.throws(() => coverageRows({datasets: []}));
});
