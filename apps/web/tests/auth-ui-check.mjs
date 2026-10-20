// Logowanie w panelu z całkowicie mockowanym API: przekierowanie bez sesji (proxy.ts), logowanie z powrotem
// na ?next, ochrona przed open redirect, błędne hasło, wygasła sesja (401) i wylogowanie.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { corsHeaders, SESSION_COOKIE, TEST_ME } from './fixtures/auth.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3107';
const web = `http://localhost:${port}`;

const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const context = page.context();
 let sessionValid = false;
 let logins = 0;
 const setSession = () => context.addCookies([{name:SESSION_COOKIE,value:'ui-test',domain:'localhost',path:'/'}]);

 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.hostname === 'localhost' && url.port === port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  const method = route.request().method();
  let status = 200; let body;
  if (url.pathname === '/api/auth/login' && method === 'POST') {
   logins++;
   const {password} = route.request().postDataJSON();
   if (password === 'dobre-haslo-123') { sessionValid = true; await setSession(); body = TEST_ME; }
   else { status = 401; body = {detail:{code:'invalid_credentials'}}; }
  } else if (url.pathname === '/api/auth/logout' && method === 'POST') {
   sessionValid = false; await context.clearCookies(); status = 204;
  } else if (!sessionValid) {
   status = 401; body = {detail:{code:'not_authenticated'}};
  } else if (url.pathname === '/api/auth/me') body = TEST_ME;
  else if (url.pathname === '/api/jobs/stats') body = {queued:0,running:0,retrying:0,failed:0,succeeded:0,total:0};
  else if (url.pathname === '/api/jobs') body = {items:[],total:0,page:1,page_size:25};
  else if (url.pathname === '/api/sources') body = [];
  else if (url.pathname === '/api/candidates') body = {items:[],total:0,page:1,page_size:25};
  else if (url.pathname === '/api/stats') body = {candidates_today:0,new_today:0,approved:0,ignored:0,average_score:null};
  else body = {};
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:status === 204 ? '' : JSON.stringify(body)});
 });

 // 1. Bez ciasteczka proxy.ts kieruje na /login z zachowaną ścieżką.
 await page.goto(`${web}/queue?status=failed`);
 await page.waitForURL(/\/login\?next=/);
 assert.equal(new URL(page.url()).searchParams.get('next'), '/queue?status=failed');
 await page.getByRole('heading', {name:'Zaloguj się'}).waitFor();
 assert.equal(await page.getByRole('link', {name:'Wyloguj'}).count() + await page.getByRole('button', {name:'Wyloguj'}).count(), 0, 'nawigacja ukryta na /login');

 // 2. Złe hasło: komunikat, bez przekierowania.
 await page.getByLabel('Email').fill('test@example.com');
 await page.getByLabel('Hasło').fill('zle-haslo');
 await page.getByRole('button', {name:'Zaloguj'}).click();
 await page.getByRole('alert').filter({hasText:'Nieprawidłowy email lub hasło.'}).waitFor();
 assert.match(page.url(), /\/login/);

 // 3. Poprawne hasło: powrót na ?next, email w nawigacji.
 await page.getByLabel('Hasło').fill('dobre-haslo-123');
 await page.getByRole('button', {name:'Zaloguj'}).click();
 await page.waitForURL(`${web}/queue?status=failed`);
 await page.getByText('test@example.com').waitFor();
 assert.equal(logins, 2);

 // 4. Wygasła sesja po stronie API: 401 z dowolnego zapytania wraca na /login z bieżącą ścieżką.
 sessionValid = false;
 await page.goto(`${web}/sources`);
 await page.waitForURL(/\/login\?next=%2Fsources/);

 // 5. next spoza aplikacji jest ignorowany (open redirect).
 sessionValid = true;
 await page.goto(`${web}/login?next=//evil.example/phish`);
 await page.waitForURL(`${web}/`);

 // 6. Wylogowanie kasuje sesję i wraca na /login; panel znowu niedostępny.
 await page.getByRole('button', {name:'Wyloguj'}).click();
 await page.waitForURL(/\/login$/);
 await page.goto(`${web}/queue`);
 await page.waitForURL(/\/login\?next=%2Fqueue/);

 // 7. Rejestracja jest osiągalna bez sesji i ma link powrotny z zachowanym next.
 await page.getByRole('link', {name:'Zarejestruj się'}).click();
 await page.waitForURL(/\/register\?next=%2Fqueue/);
 await page.getByRole('heading', {name:'Załóż konto'}).waitFor();

 console.log('PASS: redirect to /login with next, wrong password, login returns to next, 401 re-login, open-redirect guard, logout, register link. All API mocked.');
} finally {
 await browser.close();
}
