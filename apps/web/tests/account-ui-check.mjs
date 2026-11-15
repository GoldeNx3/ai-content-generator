// Ustawienia → Konto z całkowicie lokalnym API: kategorie, dane konta i zmiana hasła (walidacja, błąd, sukces).
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders, TEST_ME } from './fixtures/auth.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3000';
const automation = {auto_fetch_enabled:false,auto_fetch_interval_minutes:60,auto_classify_enabled:false,auto_classify_batch_limit:20,
 last_auto_run_at:null,last_auto_run_result:null,next_auto_run_at:null,paused_at:null,automation_enabled_globally:true};
const passwordPosts = [];
let demoPosts = 0;
let sources = [];
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1280,height:1000}});
 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (['127.0.0.1','localhost'].includes(url.hostname) && url.port===port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  let body; let status = 200;
  if (url.pathname === '/api/auth/password') {
   assert.equal(route.request().method(),'POST');
   const data = route.request().postDataJSON();
   passwordPosts.push(data);
   if (data.current_password !== 'stare-haslo-123') { status = 422; body = {detail:{code:'invalid_current_password'}}; }
   else status = 204;
  }
  else if (url.pathname === '/api/usage/report') body = {month:'2026-11',total_usd:'0.000000',unknown_cost_calls:0,by_kind:[],by_stage:[],articles:{topics:0,cost_usd:'0.000000',average_usd:null}};
  else if (url.pathname === '/api/usage') body = {period_start:'2026-11-01T00:00:00+00:00',spent_usd:'0.00',budget_usd:'10.00',remaining_usd:'10.00',exceeded:false,unknown_cost_calls:0};
  else if (url.pathname === '/api/wordpress/connection') body = null;
  else if (url.pathname === '/api/sources') body = sources;
  else if (url.pathname === '/api/demo/reset') {
   assert.equal(route.request().method(),'POST');
   demoPosts++; status = 201; body = {removed: sources.length ? 3 : 0, created: 3};
   sources = [{id:9,name:'[DEMO] Scenariusze pipeline — 0 kosztów AI',type:'rss',url:'https://demo.content-engine.invalid/feed.xml',active:false,last_fetched_at:null,created_at:'2026-11-15T10:00:00Z',updated_at:'2026-11-15T10:00:00Z'}];
  }
  else if (url.pathname === '/api/workspace/editorial') body = {audience:'',voice:'',topics_scope:'',banned_phrases:[],example_post:'',style_rules:[]};
  else if (url.pathname === '/api/workspace/automation') body = automation;
  else throw new Error(`Unexpected request ${route.request().method()} ${url.pathname}`);
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:status === 204 ? '' : JSON.stringify(body)});
 });
 await authenticate(page);
 await page.goto(`http://localhost:${port}/settings`);

 const nav = page.getByRole('navigation',{name:'Kategorie ustawień'});
 for (const label of ['Konto','Budżet i koszty','Automatyzacja','Redakcja','Integracje','Tryb demo']) await nav.getByRole('link',{name:new RegExp(`^${label}`)}).waitFor();
 for (const heading of ['Konto','Automatyka','Profil redakcyjny','Zmiana hasła']) await page.getByRole('heading',{name:heading,exact:true}).waitFor();
 await page.locator('main').getByText(TEST_ME.user.email,{exact:true}).waitFor();

 const submit = page.getByRole('button',{name:'Zmień hasło',exact:true});
 assert.equal(await submit.isDisabled(),true,'empty form cannot be sent');
 await page.getByLabel('Obecne hasło',{exact:true}).fill('stare-haslo-123');
 await page.getByLabel('Nowe hasło',{exact:true}).fill('krotkie');
 await page.getByLabel('Powtórz nowe hasło',{exact:true}).fill('krotkie');
 assert.equal(await submit.isDisabled(),true,'too short password is blocked locally');
 await page.getByLabel('Nowe hasło',{exact:true}).fill('nowe-dlugie-haslo-42');
 await page.getByLabel('Powtórz nowe hasło',{exact:true}).fill('inne-dlugie-haslo-42');
 await page.getByText('Hasła są takie same – niespełnione').waitFor({state:'attached'});
 assert.equal(await submit.isDisabled(),true,'mismatched confirmation is blocked locally');
 await page.getByLabel('Powtórz nowe hasło',{exact:true}).fill('nowe-dlugie-haslo-42');

 await page.getByLabel('Obecne hasło',{exact:true}).fill('zle-haslo-000');
 await submit.click();
 await page.getByRole('alert').getByText('Obecne hasło jest nieprawidłowe.',{exact:true}).waitFor();
 assert.equal(page.url().endsWith('/settings'),true,'wrong current password does not log out');

 await page.getByLabel('Obecne hasło',{exact:true}).fill('stare-haslo-123');
 await page.getByRole('button',{name:'Pokaż: Obecne hasło'}).click();
 assert.equal(await page.getByLabel('Obecne hasło',{exact:true}).getAttribute('type'),'text');
 await submit.click();
 await page.getByRole('status').getByText('Hasło zmienione. Pozostałe sesje zostały wylogowane.',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Obecne hasło',{exact:true}).inputValue(),'','form is cleared after success');
 assert.deepEqual(passwordPosts.at(-1),{current_password:'stare-haslo-123',password:'nowe-dlugie-haslo-42',password_confirmation:'nowe-dlugie-haslo-42'});
 assert.equal(passwordPosts.length,2);

 const demo = page.locator('#demo');
 await demo.getByRole('button',{name:'Utwórz tematy demo',exact:true}).click();
 await demo.getByRole('status').getByText(/Utworzono 3 nowe tematy demo/).waitFor();
 assert.equal(demoPosts,1,'first creation needs no confirmation');
 await page.reload();
 await demo.getByRole('button',{name:'Zresetuj tematy demo',exact:true}).click();
 const confirmDemo = demo.getByRole('alertdialog',{name:'Potwierdź reset tematów demo'});
 await confirmDemo.getByText(/Prawdziwe tematy nie zostaną zmienione/).waitFor();
 assert.equal(demoPosts,1,'reset of existing demo asks first');
 await confirmDemo.getByRole('button',{name:'Usuń i utwórz od nowa',exact:true}).click();
 await demo.getByRole('status').getByText(/Usunięto 3 poprzednie tematy demo/).waitFor();
 assert.equal(demoPosts,2);
 await nav.getByRole('link',{name:/^Integracje/}).click();
 await page.waitForFunction(() => location.hash === '#integracje');

 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'/tmp/content-settings-mobile.png',fullPage:true});
 await page.setViewportSize({width:1280,height:1000});
 await page.evaluate(() => window.scrollTo(0, 0));
 await page.screenshot({path:'/tmp/content-settings.png',fullPage:true});
 console.log('PASS: settings categories, account data, password change validation, wrong current password, success + cleared form, demo create/reset with confirmation, mobile. No real API calls.');
} finally {await browser.close();}
