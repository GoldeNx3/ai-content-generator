import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const source = readFileSync(new URL('../components/article/markdown.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX },
}).outputText.replace(/from (["'])([^"']+)\1/g, (_, quote, name) => `from ${quote}${import.meta.resolve(name)}${quote}`);
const { Markdown } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const render = (text) => renderToStaticMarkup(createElement(Markdown, { children: text }));

test('comparison table renders as a table inside a scrollable region', () => {
  const html = render('| Model | Cena |\n| --- | ---: |\n| A | 10 USD |');
  assert.match(html, /<table/);
  assert.match(html, /<th[^>]*>Cena<\/th>/);
  assert.match(html, /<td[^>]*>10 USD<\/td>/);
  assert.match(html, /overflow-x-auto/);
});

test('fenced code preserves language, indentation and syntax highlighting', () => {
  const html = render('```python\ndef greet(name):\n    return name\n```');
  assert.match(html, /language-python/);
  assert.match(html, /hljs-keyword/);
  assert.match(html, /python/);
  assert.match(html, /<pre/);
  assert.match(html, /\n    /);
});

test('unknown and unlabelled code remain readable without guessing a language', () => {
  assert.match(render('```unknown-example\nexample & value\n```'), /example &amp; value/);
  assert.match(render('```\nexample\n```'), /Kod/);
});

test('inline code and source HTML are handled safely', () => {
  const html = render('Uruchom `npm install`.\n\n<script>alert("x")</script>');
  assert.match(html, /<code[^>]*>npm install<\/code>/);
  assert.doesNotMatch(html, /<script/);
  assert.doesNotMatch(html, /<pre/);
});
