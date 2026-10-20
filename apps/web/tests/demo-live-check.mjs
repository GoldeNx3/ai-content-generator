// Explicit opt-in: run against a LOCAL demo-enabled API, never ordinary candidates.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
import { loginLive, applySession } from './fixtures/auth.mjs';
// API wymaga sesji: wszystkie bezpośrednie wywołania z Node idą z ciasteczkiem zalogowanego konta.
const session=await loginLive(null);
const fetch=(url,init={})=>globalThis.fetch(url,{...init,headers:{...init.headers,Cookie:session}});
const API='http://localhost:8000/api', WEB='http://localhost:3000';
const PREFIX='https://demo.content-engine.invalid/';
const catalog=await (await fetch(`${API}/candidates?page_size=100&sort=created_at&order=desc`)).json();
const candidate=catalog.items.find(c=>c.external_url.startsWith(PREFIX+'checks/'));
assert(candidate, 'Create a dedicated demo checks candidate first; this check never modifies seeded scenarios.');
assert(candidate.is_demo);
async function call(path, body) {
 const response=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const value=await response.json();
 assert.equal(response.status,202,JSON.stringify(value));
 return value;
}
async function finish(job) {
 for(let i=0;i<120;i++){
  const current=await(await fetch(`${API}/jobs/${job.id}`)).json();
  if(current.status==='succeeded')return current;
  assert.notEqual(current.status,'failed',current.error_message);
  await new Promise(r=>setTimeout(r,500));
 }
 throw Error('Demo worker timeout');
}
await finish(await call(`/candidates/${candidate.id}/classify`));
await finish(await call(`/candidates/${candidate.id}/research`));
await finish(await call(`/candidates/${candidate.id}/article`,{length:'short'}));
let versions=await(await fetch(`${API}/candidates/${candidate.id}/articles`)).json();
const original=versions[0];
await finish(await call(`/articles/${original.id}/qa`));
const qa=await(await fetch(`${API}/articles/${original.id}/qa`)).json();
assert.equal(qa.overall_score,75);assert.equal(qa.unsupported_claims_count,1);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',err=>errors.push(err.message));
 await applySession(page,session);
 await page.goto(`${WEB}/candidates/${candidate.id}`);
 await page.getByText('Tryb demo · 0 kosztów AI.',{exact:true}).waitFor();
 assert.equal(await page.locator('[data-cost="paid"]').count(),0);
 const panel=page.locator('[data-workflow-step="5"]');
 await page.getByRole('navigation',{name:'Nawigacja po temacie i artykule'}).getByRole('link',{name:'QA / jakość',exact:true}).click();
 await panel.getByText(/Problemy: 1 · automatycznie: 1/).waitFor();
 await panel.getByRole('button',{name:'Przejdź do poprawek i zatwierdzenia',exact:true}).click();
 const fixButton=page.locator('[data-workflow-step="6"]').getByRole('button',{name:'Popraw automatycznie · demo · bezpłatne',exact:true});
 await fixButton.click();
 for(let i=0;i<120;i++){
  versions=await(await fetch(`${API}/candidates/${candidate.id}/articles`)).json();
  if(versions[0].id!==original.id)break;
  await new Promise(r=>setTimeout(r,500));
 }
 const child=versions[0];assert.notEqual(child.id,original.id);assert.equal(child.status,'draft');
 await finish(await call(`/articles/${child.id}/qa`));
 const checked=await(await fetch(`${API}/articles/${child.id}`)).json();assert.equal(checked.status,'ready_for_approval');
 // Load the current version and approve through the real UI.
 await page.reload();
 const approval=page.locator('[data-workflow-step="6"]');
 await page.getByRole('navigation',{name:'Nawigacja po temacie i artykule'}).getByRole('link',{name:'Poprawki i zatwierdzenie',exact:true}).click();
 await approval.getByRole('button',{name:'Zatwierdź wersję',exact:true}).click();
 await approval.getByText(/zatwierdzon/i).first().waitFor();
 const approved=await(await fetch(`${API}/articles/${child.id}`)).json();
 assert.equal(approved.status,'approved');assert.equal(approved.parent_version_id,original.id);
 const old=await(await fetch(`${API}/articles/${original.id}`)).json();assert(old.content.includes('47%'));assert(!approved.content.includes('47%'));
 const report=await(await fetch(`${API}/articles/${child.id}/qa`)).json();assert(report.qa_passed);assert.equal(Number(report.estimated_cost_usd),0);
 const fixes=await(await fetch(`${API}/article-versions/${child.id}/fixes`)).json();assert.equal(fixes[0].issues_fixed,1);assert.equal(Number(fixes[0].estimated_cost_usd),0);
 assert.deepEqual(errors,[]);
 await page.screenshot({path:'/tmp/content-engine-demo.png',fullPage:true});
 console.log(JSON.stringify({candidate_id:candidate.id,source_version:original.id,result_version:child.id,qa_score:report.overall_score,approved:true,ai_cost:0}));
}finally{await browser.close();}
