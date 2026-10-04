import { test } from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const exports = {};
vm.runInNewContext(ts.transpile(readFileSync(new URL('../lib/jobs.ts',import.meta.url),'utf8'),{module:ts.ModuleKind.CommonJS}),{exports});
const stamp = '2026-10-04T10:00:00Z';
const qa = {id:'qa',kind:'qa_article',article_id:10,status:'running',created_at:stamp,started_at:stamp};
test('running QA blocks other actions without marking Auto Fix as running',()=>{
  const state=exports.selectStageJobs([qa],'auto_fix_article',10);
  assert.equal(state.active,qa);
  assert.equal(state.ownActive,undefined);
  assert.equal(state.latest,undefined);
  assert.equal(exports.selectStageJobs([qa],'qa_article',10).ownActive,qa);
});
test('progress belongs to the selected version and stays separate from history',()=>{
  const old={...qa,id:'old',article_id:9};
  const finished={...qa,id:'finished',status:'succeeded'};
  const state=exports.selectStageJobs([old,finished],'qa_article',10);
  assert.equal(state.active,old);
  assert.equal(state.ownActive,undefined);
  assert.equal(state.latest,finished);
  assert.equal(state.history.length,1);
});
test('elapsed time uses execution start and survives a refreshed page',()=>{
  assert.equal(exports.jobElapsedSeconds({...qa,created_at:'2026-10-04T09:00:00Z'},Date.parse(stamp)+12500),12);
  assert.equal(exports.jobElapsedSeconds({...qa,status:'queued',started_at:null},Date.parse(stamp)+4500),4);
  assert.equal(exports.jobElapsedSeconds({...qa,started_at:'invalid'},Date.parse(stamp)),null);
  assert.equal(exports.jobElapsedSeconds(qa,Date.parse(stamp)-1000),0);
});
