// Logowanie w testach UI. Mockowane checki: ciasteczko sesji (proxy.ts przepuszcza do panelu) i atrapa
// /api/auth/me. Live checki: prawdziwe logowanie przez API (UI_TEST_EMAIL / UI_TEST_PASSWORD).

export const SESSION_COOKIE = process.env.SESSION_COOKIE_NAME || 'ce_session';
export const TEST_ME = { user: { id: 1, email: 'test@example.com' }, workspace: { id: 1, name: 'test' } };

// fetch z credentials: "include" odrzuca "Access-Control-Allow-Origin: *"; odpowiadamy originem żądania.
export function corsHeaders(route) {
  return {
    'Access-Control-Allow-Origin': route.request().headers().origin || '*',
    'Access-Control-Allow-Credentials': 'true',
  };
}

// Wywołać PO page.route('**/*'): późniejsza trasa Playwright ma pierwszeństwo.
// Atrapa Sanctum: ciasteczko XSRF-TOKEN (front odsyła je w nagłówku) i odpowiedź /sanctum/csrf-cookie.
export async function fakeCsrf(page) {
  await page.context().addCookies([{ name: 'XSRF-TOKEN', value: 'ui-test-xsrf', domain: 'localhost', path: '/' }]);
  await page.route('**/sanctum/csrf-cookie', route => route.fulfill({ status: 204, headers: corsHeaders(route), body: '' }));
}

export async function authenticate(page) {
  await fakeCsrf(page);
  await page.context().addCookies([{ name: SESSION_COOKIE, value: 'ui-test', domain: 'localhost', path: '/' }]);
  await page.route('**/api/auth/me', route => route.fulfill({
    contentType: 'application/json', headers: corsHeaders(route), body: JSON.stringify(TEST_ME),
  }));
}

// Live: logowanie przez Sanctum (ciasteczko XSRF-TOKEN + sesja) na prawdziwe API Laravela.
// Zwraca nagłówek Cookie; liveHeaders() dokłada X-XSRF-TOKEN i Origin do zapisów z Node.
const ORIGIN = process.env.UI_TEST_ORIGIN || 'http://localhost:3000';

function cookiesFrom(response, jar = {}) {
  for (const line of response.headers.getSetCookie()) {
    const [pair] = line.split(';');
    const index = pair.indexOf('=');
    jar[pair.slice(0, index)] = pair.slice(index + 1);
  }
  return jar;
}

const header = jar => Object.entries(jar).map(([k, v]) => `${k}=${v}`).join('; ');

export function liveHeaders(cookie) {
  const xsrf = cookie.split('; ').find(c => c.startsWith('XSRF-TOKEN='));
  return { Cookie: cookie, Origin: ORIGIN, Referer: ORIGIN + '/', Accept: 'application/json',
    ...(xsrf ? { 'X-XSRF-TOKEN': decodeURIComponent(xsrf.slice('XSRF-TOKEN='.length)) } : {}) };
}

export async function loginLive(page, api = 'http://localhost:8000/api') {
  const email = process.env.UI_TEST_EMAIL;
  const password = process.env.UI_TEST_PASSWORD;
  if (!email || !password) throw new Error('Ustaw UI_TEST_EMAIL i UI_TEST_PASSWORD (konto z `php artisan users:create`).');
  const base = api.replace(/\/api$/, '');
  const jar = cookiesFrom(await fetch(`${base}/sanctum/csrf-cookie`, { headers: { Origin: ORIGIN, Referer: ORIGIN + '/' } }));
  const response = await fetch(`${api}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...liveHeaders(header(jar)) }, body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(`Logowanie nieudane: ${response.status}`);
  cookiesFrom(response, jar);
  if (!jar[SESSION_COOKIE]) throw new Error('API nie ustawiło ciasteczka sesji');
  const cookie = header(jar);
  if (page) await applySession(page, cookie);
  return cookie;
}

export async function applySession(page, cookie) {
  await page.context().addCookies(cookie.split('; ').map(pair => {
    const index = pair.indexOf('=');
    return { name: pair.slice(0, index), value: pair.slice(index + 1), domain: 'localhost', path: '/' };
  }));
}
