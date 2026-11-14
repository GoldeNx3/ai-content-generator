// Karta Automatyka w Ustawieniach z całkowicie lokalnym API: zapis ustawień, pauza i widok tylko do odczytu.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3000';
const stamp = '2026-11-14T12:00:00+00:00';
const settings = {auto_fetch_enabled:false,auto_fetch_interval_minutes:60,auto_classify_enabled:false,auto_classify_batch_limit:20,
 last_auto_run_at:null,last_auto_run_result:null,next_auto_run_at:null,paused_at:null,automation_enabled_globally:true,can_edit:true};
const patches = [];
let pausePosts = 0;
let resumePosts = 0;
const until = async (check, label) => { for (let i = 0; i < 50; i++) { if (check()) return; await new Promise(r => setTimeout(r, 100)); } throw new Error(`Timeout: ${label}`); };
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1280,height:1000}});
 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (['127.0.0.1','localhost'].includes(url.hostname) && url.port===port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  let body;
  if (url.pathname==='/api/usage') body={period_start:'2026-11-01T00:00:00+00:00',spent_usd:'0.00',budget_usd:'10.00',remaining_usd:'10.00',exceeded:false,unknown_cost_calls:0};
  else if (url.pathname==='/api/wordpress/connection') body=null;
  else if (url.pathname==='/api/workspace/automation' && route.request().method()==='PATCH') {
   const change=JSON.parse(route.request().postData());patches.push(change);Object.assign(settings,change);
   settings.next_auto_run_at=settings.auto_fetch_enabled && !settings.paused_at ? stamp : null;body=settings;
  } else if (url.pathname==='/api/workspace/automation') body=settings;
  else if (url.pathname==='/api/workspace/pause') {pausePosts++;settings.paused_at=stamp;settings.next_auto_run_at=null;body={paused_at:stamp};}
  else if (url.pathname==='/api/workspace/resume') {resumePosts++;settings.paused_at=null;body={paused_at:null,resumed_jobs:0};}
  else throw new Error(`Unexpected request ${route.request().method()} ${url.pathname}`);
  await route.fulfill({status:200,contentType:'application/json',headers:corsHeaders(route),body:JSON.stringify(body)});
 });
 await authenticate(page);
 await page.goto(`http://localhost:${port}/settings`);
 await page.getByRole('heading',{name:'Automatyka',exact:true}).waitFor();
 const fetchBox=page.getByLabel('Automatycznie pobieraj RSS (bezpłatne)');
 assert.equal(await fetchBox.isChecked(),false,'automation is off by default');
 await page.getByText('wyłączone',{exact:true}).waitFor();

 await fetchBox.check();
 await until(()=>patches.length===1,'fetch toggle saved');
 assert.deepEqual(patches[0],{auto_fetch_enabled:true});
 await page.getByLabel('Częstotliwość pobierania').selectOption('30');
 await until(()=>patches.length===2,'interval saved');
 assert.deepEqual(patches[1],{auto_fetch_interval_minutes:30});
 await page.getByLabel(/Po pobraniu od razu zlecaj ocenę/).check();
 await until(()=>patches.length===3,'classify saved');
 assert.deepEqual(patches[2],{auto_classify_enabled:true});
 await page.getByLabel('Najwyżej ocen na przebieg').fill('5');
 await page.getByLabel('Najwyżej ocen na przebieg').blur();
 await until(()=>patches.length===4,'limit saved');
 assert.deepEqual(patches[3],{auto_classify_batch_limit:5});

 await page.getByRole('button',{name:'Wstrzymaj workspace',exact:true}).click();
 await page.getByRole('button',{name:'Wznów workspace',exact:true}).waitFor();
 await page.getByText(/Workspace wstrzymany od/).waitFor();
 assert.equal(pausePosts,1);
 await page.getByRole('button',{name:'Wznów workspace',exact:true}).click();
 await page.getByRole('button',{name:'Wstrzymaj workspace',exact:true}).waitFor();
 assert.equal(resumePosts,1);

 settings.can_edit=false;
 await page.reload();
 await page.getByText("Zmieniać może tylko właściciel workspace'u.",{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Automatycznie pobieraj RSS (bezpłatne)').isDisabled(),true);
 assert.equal(await page.getByLabel('Częstotliwość pobierania').isDisabled(),true);
 assert.equal(await page.getByRole('button',{name:'Wstrzymaj workspace'}).count(),0);

 settings.automation_enabled_globally=false;
 await page.reload();
 await page.getByText(/Administrator wyłączył automatykę/).waitFor();
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'/tmp/content-automation-mobile.png',fullPage:true});
 console.log('PASS: automation defaults, fetch/interval/classify/limit saves, pause and resume, read-only member view, global switch banner, mobile. No real API calls.');
} finally {await browser.close();}
