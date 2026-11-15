// Grupowanie tematów z kilku RSS: plakietka na liście, filtr duplikatów, informacja w kroku 2 i „Oceń mimo to”.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3107';
const stamp = '2026-11-14T10:00:00Z';
const base = {source_id:1,status:'pending',original_published_at:stamp,relevance_score:80,freshness_score:70,search_potential_score:60,commercial_potential_score:50,
 total_score:68,category:'news',classified_at:stamp,created_at:stamp,updated_at:stamp,summary:'Opis'};
const primary = {...base,id:1,source_name:'RSS A',external_url:'https://a.example/1',title:'OpenAI wydało nowy model',llm_reason:'Ocena AI.',group_size:2,topic_group_id:null,topic_group:null};
const duplicate = {...base,id:2,source_name:'RSS B',external_url:'https://b.example/2',title:'Nowy model GPT-6',llm_reason:'Ten sam temat co #1.',group_size:1,topic_group_id:1,duplicate_similarity:0.91,
 topic_group:{primary_id:1,members:[{id:1,title:'OpenAI wydało nowy model',external_url:'https://a.example/1',source_name:'RSS A'}]}};
const listQueries = []; const classifyBodies = []; const takeBodies = []; const groupCalls = [];
const solo = {...base,id:4,source_name:'RSS C',external_url:'https://c.example/4',title:'GPT-6 premiera',llm_reason:'Ocena AI.',group_size:1,topic_group_id:null,topic_group:null};
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const errors = []; page.on('pageerror', error => errors.push(error.message));
 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (['localhost','127.0.0.1'].includes(url.hostname) && url.port === port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  const path = url.pathname; let body; let status = 200;
  if (path === '/api/candidates') { listQueries.push(url.search); const all = url.searchParams.get('duplicates') === '1'; const items = all ? [primary, duplicate] : [primary]; body = {items,total:items.length,page:1,page_size:25}; }
  else if (path === '/api/stats') body = {candidates_today:0,new_today:0,approved:0,ignored:0,average_score:null};
  else if (path === '/api/sources') body = [];
  else if (path === '/api/usage') body = {period_start:'2026-11-01T00:00:00+00:00',spent_usd:'1.25',budget_usd:'10.00',remaining_usd:'8.75',exceeded:false,unknown_cost_calls:0};
  else if (path === '/api/workspace/automation') body = {auto_fetch_enabled:false,auto_fetch_interval_minutes:60,auto_classify_enabled:false,auto_classify_batch_limit:10,last_auto_run_at:null,last_auto_run_result:null,next_auto_run_at:null,paused_at:null,automation_enabled_globally:true};
  else if (path === '/api/jobs') body = {items:[],total:0,page:1,page_size:100};
  else if (path === '/api/candidates/2/ungroup') { groupCalls.push(path); body = {...duplicate,topic_group_id:null,topic_group:null,llm_reason:'Ten sam temat co #1. Odłączono ręcznie od grupy tematu #1.'}; }
  else if (path === '/api/candidates/4') body = solo;
  else if (path === '/api/candidates/4/similar') body = [{id:1,title:'OpenAI wydało nowy model',source_name:'RSS A',topic_group_id:null,total_score:68,similarity:0.81}];
  else if (path === '/api/candidates/4/group') { groupCalls.push([path, route.request().postDataJSON()]); body = {...solo,topic_group_id:1,
   topic_group:{primary_id:1,members:[{id:1,title:'OpenAI wydało nowy model',external_url:'https://a.example/1',source_name:'RSS A'}]}}; }
  else if (['/api/candidates/4/jobs','/api/candidates/4/articles','/api/candidates/4/suggestions','/api/candidates/2/suggestions','/api/candidates/2/similar'].includes(path)) body = path.endsWith('/jobs') ? {items:[],total:0,page:1,page_size:25} : [];
  else if (path === '/api/candidates/4/research') { status = 404; body = {detail:'Research not found'}; }
  else if (path === '/api/candidates/2/editor-take') { const data = route.request().postDataJSON(); takeBodies.push(data); duplicate.editor_take = data.editor_take; body = duplicate; }
  else if (path === '/api/candidates/2') body = duplicate;
  else if (path === '/api/candidates/2/jobs') body = {items:[],total:0,page:1,page_size:25};
  else if (path === '/api/candidates/2/articles') body = [];
  else if (path === '/api/candidates/2/research') { status = 404; body = {detail:'Research not found'}; }
  else if (path === '/api/pricing') body = {models:{},rates:{}};
  else if (path === '/api/candidates/2/classify') { classifyBodies.push(route.request().postDataJSON?.() ?? null); status = 202;
   body = {id:'job-1',candidate_id:2,kind:'classify',status:'queued',stage:null,attempt_count:0,max_attempts:3,available_at:stamp,created_at:stamp,started_at:null,finished_at:null,result_id:null,result_type:null,error_code:null,error_message:null}; }
  else if (path === '/api/jobs/job-1') body = {id:'job-1',candidate_id:2,kind:'classify',status:'queued',stage:null,attempt_count:0,max_attempts:3,available_at:stamp,created_at:stamp,started_at:null,finished_at:null,result_id:null,result_type:null,error_code:null,error_message:null};
  else throw new Error(`Unexpected request ${route.request().method()} ${path}`);
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:JSON.stringify(body)});
 });
 await authenticate(page);

 await page.goto(`http://localhost:${port}/`);
 await page.getByText('OpenAI wydało nowy model').waitFor();
 await page.getByText('+1 źródło', {exact:true}).waitFor();
 assert.equal(await page.getByText('Nowy model GPT-6').count(), 0, 'duplicates are hidden by default');
 await page.getByLabel('Pokaż duplikaty').check();
 await page.getByText('Nowy model GPT-6').waitFor();
 await page.getByText('duplikat #1', {exact:true}).waitFor();
 assert.ok(listQueries.some(query => query.includes('duplicates=1')), 'filter sends duplicates=1');

 await page.goto(`http://localhost:${port}/candidates/2`);
 await page.locator('nav a[href="#workflow-step-2"]').click();
 const note = page.getByRole('note');
 await note.getByText('Ten sam temat co inne wpisy z RSS').waitFor();
 assert.equal(await note.getByRole('link', {name:'OpenAI wydało nowy model'}).getAttribute('href'), '/candidates/1');
 await note.getByRole('button', {name:/Oceń mimo to osobno · płatne/}).click();
 await page.waitForFunction(() => true);
 for (let i = 0; i < 30 && classifyBodies.length === 0; i++) await new Promise(r => setTimeout(r, 100));
 assert.deepEqual(classifyBodies[0], {force:true});
 const take = page.getByLabel('Nasze zdanie (opcjonalnie)');
 assert.equal(await take.isVisible(), false, '„Nasze zdanie” należy do kroku 4, nie do oceny tematu');
 await page.locator('nav a[href="#workflow-step-4"]').click();
 await page.locator('#workflow-step-4').getByLabel('Nasze zdanie (opcjonalnie)').fill('Używamy tego w trzech projektach.');
 await page.getByRole('button', {name:'Zapisz komentarz · bezpłatne', exact:true}).click();
 await page.getByText('Komentarz zapisany.', {exact:true}).waitFor();
 assert.deepEqual(takeBodies[0], {editor_take:'Używamy tego w trzech projektach.'});
 await page.locator('nav a[href="#workflow-step-2"]').click();
 // Ręczna korekta grup: odłączenie duplikatu i połączenie z podobnym tematem (bezpłatne).
 await note.getByRole('button', {name:'Odłącz od grupy · bezpłatne'}).click();
 await page.getByText('Odłączono ręcznie od grupy tematu #1.', {exact:false}).first().waitFor();
 assert.deepEqual(groupCalls[0], '/api/candidates/2/ungroup');
 await page.goto(`http://localhost:${port}/candidates/4`);
 await page.locator('nav a[href="#workflow-step-2"]').click();
 const similar = page.getByRole('region', {name:'Podobne tematy'});
 await similar.getByText('OpenAI wydało nowy model').waitFor();
 await similar.getByText('podobieństwo 0.81', {exact:false}).waitFor();
 await similar.getByRole('button', {name:'To ten sam temat · bezpłatne'}).click();
 await page.getByRole('note').getByText('Ten sam temat co inne wpisy z RSS').waitFor();
 assert.deepEqual(groupCalls[1], ['/api/candidates/4/group', {primary_id:1}]);
 assert.deepEqual(errors, []);
 console.log('PASS: manual ungroup and join, group badge, hidden duplicates + filter, step-2 group note with links, forced separate classification, editor take saved. No real API calls.');
} finally { await browser.close(); }
