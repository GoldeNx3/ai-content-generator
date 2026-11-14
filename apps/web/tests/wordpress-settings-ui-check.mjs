// Ustawienia → WordPress z mockowanym API: start autoryzacji (przekierowanie do WP), powrót na callback
// (hasło usunięte z paska adresu, dane wysłane do API), połączenie ręczne, widok połączenia i rozłączenie.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3107';
const web = `http://localhost:${port}`;
const connected = {site_url:'https://blog.example',api_url:null,username:'editor',seo_plugin:'yoast',default_status:'draft',
  default_author_id:null,default_category_id:null,wp_user_id:5,wp_user_name:'Ed Itor',can_publish:true,
  last_checked_at:'2026-10-20T10:00:00Z',last_error:null};

const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page = await browser.newPage({viewport:{width:1280,height:900}});
 let connection = null; const calls = []; let authorizeUrl = null;
 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.hostname === 'localhost' && url.port === port) return route.continue();
  if (url.hostname === 'blog.example') return route.fulfill({contentType:'text/html',body:'<h1>Autoryzuj aplikację (WP)</h1>'});
  if (!url.pathname.startsWith('/api/')) return route.abort();
  const method = route.request().method(); const path = url.pathname;
  let status = 200; let body = null;
  if (method !== 'GET' && method !== 'OPTIONS') calls.push([method, path, route.request().postDataJSON?.() ?? null]);
  if (path === '/api/usage') body = {period_start:'2026-10-01T00:00:00Z',spent_usd:'10.42',budget_usd:'10.00',remaining_usd:'0',exceeded:true,unknown_cost_calls:1};
  else if (path === '/api/wordpress/connection' && method === 'GET') body = connection;
  else if (path === '/api/wordpress/connection/authorize') body = {authorize_url:authorizeUrl};
  else if (path === '/api/wordpress/connection/authorize/complete') { connection = connected; body = connected; }
  else if (path === '/api/wordpress/connection' && method === 'POST') {
   const data = route.request().postDataJSON();
   if (data.app_password !== 'good pass') { status = 422; body = {detail:{code:'wordpress_http_401'}}; }
   else { connection = {...connected, site_url:data.site_url}; body = connection; }
  }
  else if (path === '/api/wordpress/connection' && method === 'DELETE') { connection = null; status = 204; }
  else if (path === '/api/wordpress/connection/test') body = connection;
  else body = {};
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:status === 204 ? '' : JSON.stringify(body)});
 });
 await authenticate(page);

 // 1. Brak połączenia: formularz, start autoryzacji przenosi do WordPressa.
 await page.goto(`${web}/settings`);
 await page.getByRole('heading', {name:'WordPress'}).waitFor();
 // Zużycie AI: kwota, pasek i blokada po wyczerpaniu budżetu.
 await page.getByText('$10.42').waitFor();
 assert.equal(await page.getByRole('progressbar', {name:'Wykorzystanie budżetu AI'}).getAttribute('aria-valuenow'), '100');
 await page.getByText('Budżet wyczerpany').waitFor();
 await page.getByLabel('Adres strony WordPress').fill('https://blog.example');
 // Adres autoryzacji spoza http(s) (np. javascript:) nie może zostać otwarty w panelu.
 authorizeUrl = 'javascript:document.title="pwned"';
 await page.getByRole('button', {name:'Połącz z WordPressem'}).click();
 await page.getByText('WordPress zwrócił nieprawidłowy adres autoryzacji.').waitFor();
 assert.notEqual(await page.title(), 'pwned');
 assert.match(page.url(), /\/settings$/);
 authorizeUrl = 'https://blog.example/wp-admin/authorize-application.php?app_name=Content+Engine';
 await page.getByRole('button', {name:'Połącz z WordPressem'}).click();
 await page.waitForURL(/blog\.example\/wp-admin\/authorize-application\.php/);
 assert.deepEqual(calls.at(-1)[2], {site_url:'https://blog.example', api_url:null});

 // 2. Powrót z WP: hasło znika z adresu, API dostaje state + dane, przekierowanie do ustawień.
 await page.goto(`${web}/settings/wordpress/callback?state=s3cr3t-state-value&site_url=https%3A%2F%2Fblog.example&user_login=editor&password=abcd+efgh+ijkl`);
 await page.waitForURL(`${web}/settings?wordpress=connected`);
 const complete = calls.find(([, path]) => path.endsWith('/authorize/complete'));
 assert.deepEqual(complete[2], {state:'s3cr3t-state-value', user_login:'editor', password:'abcd efgh ijkl', confirm_site_change:false});
 const history = await page.evaluate(() => window.history.length);
 assert.ok(history >= 1);
 await page.getByText('Połączono', {exact:true}).waitFor();
 await page.getByText('Ed Itor').waitFor();
 assert.equal(await page.getByText('abcd efgh ijkl').count(), 0);

 // 3. Odrzucenie w WP: komunikat, bez wywołania API.
 const before = calls.length;
 await page.goto(`${web}/settings/wordpress/callback?state=x&rejected=1`);
 await page.getByRole('alert').filter({hasText:'Odrzucono dostęp'}).waitFor();
 assert.equal(calls.length, before);
 assert.equal(new URL(page.url()).search, '');

 // 4. Rozłączenie z potwierdzeniem, potem połączenie ręczne (złe i dobre hasło aplikacji).
 await page.goto(`${web}/settings`);
 await page.getByRole('button', {name:'Rozłącz'}).click();
 await page.getByRole('button', {name:'Rozłącz'}).first().click();
 await page.getByRole('button', {name:'Połącz z WordPressem'}).waitFor();
 await page.getByRole('button', {name:'Połącz ręcznie (hasło aplikacji)'}).click();
 await page.getByLabel('Adres strony WordPress').fill('https://blog.example');
 await page.getByLabel('Login WordPress').fill('editor');
 await page.getByLabel('Hasło aplikacji').fill('wrong');
 await page.getByRole('button', {name:'Połącz', exact:true}).click();
 await page.getByRole('alert').filter({hasText:'WordPress odrzucił login lub hasło aplikacji.'}).waitFor();
 await page.getByLabel('Hasło aplikacji').fill('good pass');
 await page.getByRole('button', {name:'Połącz', exact:true}).click();
 await page.getByText('Połączono', {exact:true}).waitFor();

 // 5. Telefon: bez poziomego przewijania.
 await page.setViewportSize({width:375,height:800});
 assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'brak poziomego scrolla');
 console.log('PASS: usage card (exceeded budget), authorize redirect, callback strips password and completes, reject, disconnect, manual connect (401 + success), mobile. All API mocked.');
} finally {
 await browser.close();
}
