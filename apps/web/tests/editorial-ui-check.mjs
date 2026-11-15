// Karta „Profil redakcyjny” w Ustawieniach z lokalnym API: odczyt, zapis wszystkich pól, zakazane zwroty z listy.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3107';
let profile = {audience:'',voice:'',topics_scope:'',banned_phrases:[],example_post:'',style_rules:[]};
const patches = [];
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1280,height:1100}});
 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (['127.0.0.1','localhost'].includes(url.hostname) && url.port === port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  let body;
  if (url.pathname === '/api/usage/report') body = {month:'2026-11',total_usd:'0.000000',unknown_cost_calls:0,by_kind:[],by_stage:[],articles:{topics:0,cost_usd:'0.000000',average_usd:null}};
  else if (url.pathname === '/api/usage') body = {period_start:'2026-11-01T00:00:00+00:00',spent_usd:'0',budget_usd:'10',remaining_usd:'10',exceeded:false,unknown_cost_calls:0};
  else if (url.pathname === '/api/wordpress/connection') body = null;
  else if (url.pathname === '/api/workspace/automation') body = {auto_fetch_enabled:false,auto_fetch_interval_minutes:60,auto_classify_enabled:false,auto_classify_batch_limit:20,last_auto_run_at:null,last_auto_run_result:null,next_auto_run_at:null,paused_at:null,automation_enabled_globally:true};
  else if (url.pathname === '/api/workspace/editorial' && route.request().method() === 'PATCH') { const change = JSON.parse(route.request().postData()); patches.push(change); profile = {...profile, ...change}; body = profile; }
  else if (url.pathname === '/api/workspace/editorial') body = profile;
  else throw new Error(`Unexpected request ${route.request().method()} ${url.pathname}`);
  await route.fulfill({status:200,contentType:'application/json',headers:corsHeaders(route),body:JSON.stringify(body)});
 });
 await authenticate(page);
 await page.goto(`http://localhost:${port}/settings`);
 await page.getByRole('heading', {name:'Profil redakcyjny', exact:true}).waitFor();
 await page.getByLabel('Czytelnik').fill('Programiści PHP');
 await page.getByLabel('Ton i głos').fill('Rzeczowo');
 await page.getByLabel('Zakres tematów').fill('Laravel, DevOps');
 await page.getByLabel('Zakazane zwroty').fill('rewolucja\ngame changer\n\n');
 await page.getByLabel('Zasady stylu').fill('Krótkie akapity.\n');
 await page.getByLabel('Wzorcowy wpis').fill('## Wzorzec');
 await page.getByRole('button', {name:'Zapisz profil', exact:true}).click();
 await page.getByText('Profil zapisany.', {exact:true}).waitFor();
 assert.deepEqual(patches[0], {audience:'Programiści PHP',voice:'Rzeczowo',topics_scope:'Laravel, DevOps',banned_phrases:['rewolucja','game changer'],example_post:'## Wzorzec',style_rules:['Krótkie akapity.']});
 await page.reload();
 assert.equal(await page.getByLabel('Zakazane zwroty').inputValue(), 'rewolucja\ngame changer');
 console.log('PASS: editorial profile loads, saves all fields (banned phrases one per line), reloads. No real API calls.');
} finally { await browser.close(); }
