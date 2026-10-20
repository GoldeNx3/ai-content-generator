// Logowanie w testach UI. Mockowane checki: ciasteczko sesji (proxy.ts przepuszcza do panelu) i atrapa
// /api/auth/me. Live checki: prawdziwe logowanie przez API (UI_TEST_EMAIL / UI_TEST_PASSWORD).

export const SESSION_COOKIE = process.env.SESSION_COOKIE_NAME || 'ce_session';
export const TEST_ME = { user: { id: 1, email: 'test@example.com' }, workspace: { id: 1, name: 'test', role: 'owner' } };

// fetch z credentials: "include" odrzuca "Access-Control-Allow-Origin: *"; odpowiadamy originem żądania.
export function corsHeaders(route) {
  return {
    'Access-Control-Allow-Origin': route.request().headers().origin || '*',
    'Access-Control-Allow-Credentials': 'true',
  };
}

// Wywołać PO page.route('**/*'): późniejsza trasa Playwright ma pierwszeństwo.
export async function authenticate(page) {
  await page.context().addCookies([{ name: SESSION_COOKIE, value: 'ui-test', domain: 'localhost', path: '/' }]);
  await page.route('**/api/auth/me', route => route.fulfill({
    contentType: 'application/json', headers: corsHeaders(route), body: JSON.stringify(TEST_ME),
  }));
}

// Live: loguje się na prawdziwe API; zwraca nagłówek Cookie do bezpośrednich wywołań fetch z Node.
export async function loginLive(page, api = 'http://localhost:8000/api') {
  const email = process.env.UI_TEST_EMAIL;
  const password = process.env.UI_TEST_PASSWORD;
  if (!email || !password) throw new Error('Ustaw UI_TEST_EMAIL i UI_TEST_PASSWORD (konto z `make create-user`).');
  const response = await fetch(`${api}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error(`Logowanie nieudane: ${response.status}`);
  const token = response.headers.getSetCookie().map(c => c.split(';')[0]).find(c => c.startsWith(`${SESSION_COOKIE}=`));
  if (!token) throw new Error('API nie ustawiło ciasteczka sesji');
  if (page) await applySession(page, token);
  return token;
}

export async function applySession(page, token) {
  const value = token.slice(SESSION_COOKIE.length + 1);
  await page.context().addCookies([{ name: SESSION_COOKIE, value, domain: 'localhost', path: '/' }]);
}
