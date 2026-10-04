import { test } from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const output = {};
vm.runInNewContext(ts.transpile(readFileSync(new URL('../lib/article-options.ts', import.meta.url), 'utf8'), {module: ts.ModuleKind.CommonJS}), {exports: output});
const { generationDefaults } = output;

test('new generation defaults to automatic format without an RSS category', () => {
  assert.equal(generationDefaults({}).article_format, 'auto');
  assert.equal(generationDefaults({}).length, 'auto');
});

test('regeneration preserves automatic or manual format, angle and instructions', () => {
  for (const format of ['auto', 'case_study', 'guide']) {
    const result = generationDefaults({article_format: format, article_type: 'guide', length: 'short', angle: 'Dlaczego?', instructions: 'Bez wstępu.'});
    assert.equal(result.article_format, format);
    assert.equal(result.length, 'short');
    assert.equal(result.angle, 'Dlaczego?');
    assert.equal(result.instructions, 'Bez wstępu.');
  }
});

test('old saved article choices remain usable in the new form', () => {
  assert.equal(generationDefaults({article_type: 'guide', length: 'standard'}).article_format, 'guide');
  assert.equal(generationDefaults({article_type: 'release'}).article_format, 'explainer');
  assert.equal(generationDefaults({article_type: 'guide', length: 'standard'}).length, 'auto');
});
