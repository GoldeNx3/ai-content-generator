// Wnioski z poprawek redaktora: płatny krok na stronie tematu, lista propozycji, akceptacja i pominięcie (darmowe).
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
import { wordpressState } from './fixtures/wordpress-state.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3107';
const stamp = '2026-11-15T10:00:00Z';
const candidate = {id:3,source_id:1,source_name:'RSS',external_url:'https://a.example/3',title:'Laravel 13',summary:'Opis',original_published_at:stamp,status:'pending',
 relevance_score:null,freshness_score:null,search_potential_score:null,commercial_potential_score:null,total_score:null,category:'news',llm_reason:null,classified_at:null,created_at:stamp,updated_at:stamp};
const research = {id:1,candidate_id:3,status:'completed',summary:'s',why_it_matters:'w',suggested_angle:'a',search_queries:[],uncertainties:[],conflicts:[],error:null,llm_model:'m',
 llm_input_tokens:1,llm_output_tokens:1,estimated_cost_usd:null,started_at:stamp,completed_at:stamp,created_at:stamp,updated_at:stamp,sources:[],facts:[{id:1,claim:'F',confidence:90,importance:'critical',source_ids:[]}]};
const article = {id:7,candidate_id:3,version:2,is_current:true,status:'draft',title:'Laravel 13 – co nowego',article_type:'news',article_format:'news',word_count:10,is_edited:true,
 parent_version_id:6,created_by:'manual_edit',creation_reason:'Manual edit',content_hash:'h',auto_fix_iterations_remaining:2,auto_fix_iteration:0,approved_at:null,approved_by:null,
 rejection_reason:null,qa_score:null,qa_status:'missing',qa_passed:false,estimated_cost_usd:'0',llm_model:null,created_at:stamp,updated_at:stamp,research_id:1,slug:'l13',lead:'Lead',
 content:'## A\n\nLaravel 13 wyszedł we wtorek.',generated_content:'## A\n\nW dzisiejszym świecie.',meta_title:'T',meta_description:'D',angle:null,brief:{key_points:[],required_facts:[],optional_facts:[],section_plan:[]},
 sections:[],lead_fact_ids:[],generation_options:{},research_snapshot:{facts:[],sources:[]},validation_warnings:[],sections_count:1,facts_used_count:0,facts_available_count:1,source_count:0,
 llm_input_tokens:0,llm_output_tokens:0,brief_llm_model:null,brief_input_tokens:0,brief_output_tokens:0,brief_cost_usd:null,writer_input_tokens:0,writer_output_tokens:0,writer_cost_usd:null};
let suggestions = [];
const jobs = [];
const job = (status) => ({id:'fb-1',candidate_id:3,kind:'learn_feedback',status,stage:status === 'running' ? 'learning_feedback' : null,attempt_count:1,max_attempts:3,available_at:stamp,
 created_at:stamp,started_at:stamp,finished_at:status === 'succeeded' ? stamp : null,result_id:status === 'succeeded' ? 3 : null,result_type:status === 'succeeded' ? 'suggestions' : null,error_code:null,error_message:null});
const calls = [];
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const errors = []; page.on('pageerror', error => errors.push(error.message));
 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (['localhost','127.0.0.1'].includes(url.hostname) && url.port === port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  const path = url.pathname; const method = route.request().method(); let body; let status = 200;
  if (method === 'POST') calls.push(path);
  if (path === '/api/candidates/3') body = candidate;
  else if (path === '/api/candidates/3/jobs') body = {items:jobs,total:jobs.length,page:1,page_size:100};
  else if (path === '/api/candidates/3/research') body = research;
  else if (path === '/api/candidates/3/articles') body = [article];
  else if (path === '/api/articles/7') body = article;
  else if (path === '/api/articles/7/qa') { status = 404; body = {detail:'No QA yet'}; }
  else if (/^\/api\/article-versions\/7\/(fixes)$/.test(path)) body = [];
  else if (path === '/api/article-versions/7/wordpress') body = wordpressState();
  else if (path === '/api/pricing') body = {models:{},rates:{}};
  else if (path === '/api/candidates/3/suggestions') body = suggestions;
  else if (path === '/api/candidates/3/feedback') { jobs.unshift(job('queued')); status = 202; body = jobs[0]; }
  else if (/^\/api\/suggestions\/\d+\/(accept|dismiss)$/.test(path)) {
   const [, , , id, action] = path.split('/'); const item = suggestions.find(s => s.id === Number(id));
   item.status = action === 'accept' ? 'accepted' : 'dismissed'; body = item; }
  else if (path.startsWith('/api/jobs/')) body = jobs[0];
  else throw new Error(`Unexpected request ${method} ${path}`);
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:JSON.stringify(body)});
 });
 await authenticate(page);

 await page.goto(`http://localhost:${port}/candidates/3`);
 await page.locator('nav a[href="#workflow-step-4"]').click();
 const panel = page.getByRole('region', {name:'Wnioski z Twoich poprawek', includeHidden:true});
 await panel.waitFor({state:'attached'});
 await panel.getByRole('button', {name:'Wnioski z Twoich poprawek', exact:true}).click();
 await panel.getByRole('button', {name:'Zaproponuj reguły · płatne', includeHidden:true}).click();
 for (let i = 0; i < 30 && !calls.includes('/api/candidates/3/feedback'); i++) await new Promise(r => setTimeout(r, 100));
 assert.ok(calls.includes('/api/candidates/3/feedback'), 'paid feedback step is enqueued');
 jobs[0] = job('succeeded');
 suggestions = [
  {id:1,candidate_id:3,kind:'style_rule',text:'Pierwsze zdanie podaje konkretny fakt z datą.',why:'Tak poprawiasz wstępy.',status:'pending',created_at:stamp},
  {id:2,candidate_id:3,kind:'banned_phrase',text:'w dzisiejszym świecie',why:'Usuwasz ten zwrot.',status:'pending',created_at:stamp}];
 await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
 await panel.getByText('Pierwsze zdanie podaje konkretny fakt z datą.', {includeHidden:true}).waitFor({state:'attached'});
 await panel.getByText('Zasada stylu', {exact:true, includeHidden:true}).first().waitFor({state:'attached'});
 await panel.getByText('Zakazany zwrot', {exact:true, includeHidden:true}).first().waitFor({state:'attached'});
 await panel.getByRole('button', {name:'Dodaj do profilu · bezpłatne', includeHidden:true}).first().click();
 await panel.getByText('Dodano do profilu', {exact:true, includeHidden:true}).waitFor({state:'attached'});
 await panel.getByRole('button', {name:'Pomiń', includeHidden:true}).click();
 await panel.getByText('Pominięto', {exact:true, includeHidden:true}).waitFor({state:'attached'});
 assert.deepEqual(calls.filter(c => c.startsWith('/api/suggestions')), ['/api/suggestions/1/accept', '/api/suggestions/2/dismiss']);
 assert.deepEqual(errors, []);
 console.log('PASS: feedback step enqueued from the topic page, suggestions listed with kinds, accept and dismiss are free. No real API calls.');
} finally { await browser.close(); }
