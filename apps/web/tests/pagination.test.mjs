import { test } from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const compiled = ts.transpile(readFileSync(new URL('../lib/pagination.ts', import.meta.url), 'utf8'), { module: ts.ModuleKind.CommonJS });
const output = {};
vm.runInNewContext(compiled, { exports: output });
const { pageCount, pageItems, plural } = output;
const plain = (items) => JSON.parse(JSON.stringify(items));

test('page count never drops below one', () => {
  assert.equal(pageCount(0, 25), 1);
  assert.equal(pageCount(25, 25), 1);
  assert.equal(pageCount(26, 25), 2);
});

test('short ranges list every page', () => {
  assert.deepEqual(plain(pageItems(1, 1)), [1]);
  assert.deepEqual(plain(pageItems(3, 7)), [1, 2, 3, 4, 5, 6, 7]);
});

test('long ranges keep the edges, the neighbours and a fixed width', () => {
  assert.deepEqual(plain(pageItems(1, 20)), [1, 2, 3, 4, 5, 'ellipsis-end', 20]);
  assert.deepEqual(plain(pageItems(4, 20)), [1, 2, 3, 4, 5, 'ellipsis-end', 20]);
  assert.deepEqual(plain(pageItems(10, 20)), [1, 'ellipsis-start', 9, 10, 11, 'ellipsis-end', 20]);
  assert.deepEqual(plain(pageItems(17, 20)), [1, 'ellipsis-start', 16, 17, 18, 19, 20]);
  assert.deepEqual(plain(pageItems(20, 20)), [1, 'ellipsis-start', 16, 17, 18, 19, 20]);
  for (let page = 1; page <= 20; page++) assert.equal(pageItems(page, 20).length, 7);
  assert.equal(pageItems(10, 40, 2).length, 9);
});

test('out-of-range pages are clamped', () => {
  assert.deepEqual(plain(pageItems(99, 20)), plain(pageItems(20, 20)));
  assert.deepEqual(plain(pageItems(0, 20)), plain(pageItems(1, 20)));
});

test('polish plural forms', () => {
  assert.deepEqual([1, 2, 5, 12, 22, 25, 104].map((n) => plural(n, 'temat', 'tematy', 'tematów')),
    ['temat', 'tematy', 'tematów', 'tematów', 'tematy', 'tematów', 'tematy']);
});
