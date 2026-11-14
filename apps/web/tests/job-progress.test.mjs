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
test('cancelled jobs are terminal and labelled',()=>{
  assert.equal(exports.isActiveJob({...qa,status:'cancelled'}),false);
  assert.equal(exports.STATUS_LABELS.cancelled,'Anulowane');
  assert.ok(exports.STATUS_STYLES.cancelled);
});
test('cancel is offered for waiting jobs and running AI jobs only',()=>{
  assert.equal(exports.cancelAction({...qa,status:'queued'}),'cancel');
  assert.equal(exports.cancelAction({...qa,status:'retrying'}),'cancel');
  assert.equal(exports.cancelAction({...qa,status:'running',cancel_requested_at:null}),'stop');
  assert.equal(exports.cancelAction({...qa,status:'running',cancel_requested_at:stamp}),'stopping');
  assert.equal(exports.cancelAction({...qa,kind:'publish_wordpress',status:'running',cancel_requested_at:null}),null);
  assert.equal(exports.cancelAction({...qa,status:'succeeded'}),null);
  assert.equal(exports.cancelAction({...qa,status:'cancelled'}),null);
});
test('search calls show Tavily credits instead of an unknown model', () => {
  assert.equal(exports.callModelLabel({usage:{provider:'tavily',search_credits:2,input_tokens:0,output_tokens:0}}), 'Tavily · 2 kredyty');
  assert.equal(exports.callModelLabel({usage:{provider:'tavily',search_credits:1,input_tokens:0,output_tokens:0}}), 'Tavily · 1 kredyt');
  assert.equal(exports.callModelLabel({usage:{model:'gpt-4.1-mini',input_tokens:1,output_tokens:2}}), 'gpt-4.1-mini');
  assert.equal(exports.callModelLabel({usage:null}), null);
  assert.equal(exports.callTokensLabel({usage:{provider:'tavily',search_credits:2,input_tokens:0,output_tokens:0}}), 'nie dotyczy');
  assert.equal(exports.callTokensLabel({usage:{model:'m',input_tokens:5,output_tokens:7}}), '5 / 7');
  assert.equal(exports.callTokensLabel({usage:{model:'m',input_tokens:5,output_tokens:7,recorded:false}}), 'nieznane');
  assert.equal(exports.stageLabel('searching_sources'), 'Wyszukiwanie (Tavily)');
});
