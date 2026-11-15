import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
(async () => {
 const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
 try {
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const errors = [];
 page.on("pageerror", error => errors.push(error.message));
 const uiPort = process.env.UI_TEST_PORT || "3107";
 let research = null;
 const stamp = '2026-10-03T10:00:00Z';
 const candidate = {id:1,source_id:1,source_name:'Test RSS',external_url:'https://example.com/article',title:'Testowy temat',summary:'Materiał testowy',original_published_at:stamp,status:'pending',relevance_score:null,freshness_score:null,search_potential_score:null,commercial_potential_score:null,total_score:null,category:null,llm_reason:null,classified_at:null,created_at:stamp,updated_at:stamp};
 const report = {id:1,candidate_id:1,status:'completed',summary:'Podsumowanie',why_it_matters:'Znaczenie',suggested_angle:'Perspektywa',search_queries:[],uncertainties:[],conflicts:[],error:null,llm_model:'test-model',llm_input_tokens:10,llm_output_tokens:10,estimated_cost_usd:null,started_at:stamp,completed_at:stamp,created_at:stamp,updated_at:stamp,sources:[],facts:[]};
 const jobs=[];
 function job(kind,status='succeeded',result_id=1) {
  const value={id:`job-${jobs.length+1}`,candidate_id:1,kind,status,stage:status==='running'?'analysing':'saving',attempt_count:1,max_attempts:3,available_at:stamp,created_at:stamp,started_at:stamp,finished_at:status==='succeeded'?stamp:null,result_id,result_type:kind==='write'?'article':kind==='research'?'research':'candidate',error_code:null,error_message:null};
  jobs.unshift(value); return value;
 }

 await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (['localhost', '127.0.0.1'].includes(url.hostname) && url.port === uiPort) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  let body; let status = 200;
  const path = url.pathname;
  if (path === '/api/candidates/1/jobs') body={items:jobs,total:jobs.length,page:1,page_size:25};
  else if (/^\/api\/jobs\/[^/]+\/attempts$/.test(path)) body=[];
  else if (path.startsWith('/api/jobs/')) body=jobs.find(j=>j.id===path.split('/').at(-1));
  else if (path === '/api/pricing') body={models:{},rates:{}};
  else if (path === '/api/candidates/1') body=candidate;
  else if (path === '/api/candidates/1/articles') body=[];
  else if (path === '/api/candidates/1/research/retry') {body=job('research','queued');status=202;}
  else if (path === '/api/candidates/1/research') {
   if (route.request().method() === 'POST') {research={...report,status:'running',completed_at:null};body=job('research','running');status=202;}
   else if (research) body=research; else {status=404;body={detail:'No research'};}
  } else throw new Error('Unexpected request '+path);
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:JSON.stringify(body)});
 });

 const go = async n => {
   if(page.viewportSize().width < 1024) await page.getByRole('combobox',{name:'Wybierz etap pipeline'}).selectOption(`#workflow-step-${n}`);
   else await page.locator(`nav a[href="#workflow-step-${n}"]`).click();
 };
 await authenticate(page);
 await page.goto(`http://localhost:${uiPort}/candidates/1`);
 await go(2);
 await page.getByRole('button',{name:'Przejdź do researchu',exact:true}).waitFor();
 await go(3);
 const step=page.locator('[data-workflow-step="3"]');
 const next=step.getByRole('button',{name:'Przejdź do generowania',exact:true});
 await next.waitFor();assert.equal(await next.isDisabled(),false,'navigation to the next stage is never blocked');
 await step.getByText('Generowanie odblokuje się po ukończeniu researchu ze zweryfikowanymi faktami.',{exact:true}).waitFor();
 assert.equal(await step.getByLabel("Adres dodatkowego źródła",{exact:true}).count(),1,"manual source form is available before the first research");
 research={...report,sources:[{id:1,url:'https://example.com',title:'Źródło',fetch_status:'success',source_type:'original',content_length:1000}]};
 await page.reload();
 await step.getByRole('button',{name:'Zaktualizuj research · płatne',exact:true}).waitFor();
 assert.equal(await step.getByRole('button',{name:/Ponów analizę|Nowy research/}).count(),0);
 const saved=step.getByRole('radio',{name:/Analizuj zapisane źródła/});
 assert.equal(await saved.isChecked(),true);
 let request=page.waitForRequest(r=>r.url().endsWith('/research/retry')&&r.method()==='POST');
 await step.getByRole('button',{name:'Zaktualizuj research · płatne',exact:true}).click();
 await request;
 jobs.length=0;await page.reload();
 await step.getByRole('radio',{name:/Wyszukaj źródła od nowa/}).check();
 request=page.waitForRequest(r=>r.url().endsWith('/research')&&r.method()==='POST');
 await step.getByRole('button',{name:'Zaktualizuj research · płatne',exact:true}).click();
 await request;
 jobs.length=0;research={...report,sources:[{id:1,url:'https://example.com',title:'Źródło',fetch_status:'success',source_type:'original',content_length:1000}]};await page.reload();
 const input=step.getByLabel('Adres dodatkowego źródła',{exact:true});await input.waitFor();
 assert.ok(await input.evaluate(el=>el.getBoundingClientRect().height>=44));
 assert.notEqual(await input.evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
 await go(4);
 await page.getByText('Ukończ research ze zweryfikowanymi faktami, aby odblokować generowanie.',{exact:true}).waitFor();
 await go(6);
 assert.equal(await page.getByRole('button',{name:'Zatwierdź wersję',exact:true}).isDisabled(),true);
 await go(8);
 assert.equal(await page.getByRole('button',{name:'Utwórz szkic w WordPressie',exact:true}).isDisabled(),true);
 for(const width of [1440,1024,768,375]) {
   await page.setViewportSize({width,height:1000});
   for(const n of [1,2,3,4,5,6,8]) {await go(n);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`stage ${n} at ${width}px`);}
   await go(3);await page.screenshot({path:`/tmp/candidate-actions-${width}.png`,fullPage:true});
 }
 assert.deepEqual(errors, []);
 console.log('PASS: research endpoints, persistent actions, prerequisites, visible forms, seven stages at four widths.');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
