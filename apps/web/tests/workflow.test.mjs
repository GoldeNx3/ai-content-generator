import { test } from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const compiled = ts.transpile(readFileSync(new URL('../lib/workflow.ts', import.meta.url), 'utf8'), { module: ts.ModuleKind.CommonJS });
const output = {};
vm.runInNewContext(compiled, { exports: output });
const { costLabel, researchState, articleState } = output;
test('unknown cost is never presented as free', () => {
  assert.equal(costLabel(null), 'Koszt nieznany');
  assert.equal(costLabel('0'), '≈ $0.0000');
  assert.equal(costLabel('0.01234'), '≈ $0.0123');
});
test('research distinguishes absent, queued, running, completed and failed', () => {
  assert.equal(researchState(null, false), 'Ładowanie…');
  assert.equal(researchState(null, true), 'Do uruchomienia');
  for (const [status, expected] of Object.entries({ pending: 'W kolejce', running: 'W toku', completed: 'Zakończony', failed: 'Błąd' })) {
    assert.equal(researchState({status}, true), expected);
  }
});
test('an existing draft remains completed when new research is unfinished', () => {
  assert.equal(articleState(true, false, false, true), 'Zakończony');
  assert.equal(articleState(false, false, false, true), 'Najpierw ukończ research');
  assert.equal(articleState(false, false, true, true), 'Do uruchomienia');
  assert.equal(articleState(true, true, true, true), 'W toku');
  assert.equal(articleState(false, false, true, false), 'Ładowanie…');
});

test('QA distinguishes stale reports and queue status', () => {
  assert.equal(output.qaState(null, false), 'Ładowanie…');
  assert.equal(output.qaState(null, true), 'Do uruchomienia');
  assert.equal(output.qaState({status: 'completed', is_stale: true}, true), 'Wymaga ponownej oceny');
  assert.equal(output.qaState({status: 'completed', is_stale: false}, true), 'Zakończony');
  assert.equal(output.qaState({status: 'pending'}, true), 'W kolejce');
});
