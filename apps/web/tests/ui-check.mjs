import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';
(async () => {
 const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const uiPort = process.env.UI_TEST_PORT || "3107";
 let research = null;
 let article = null;
 let articles = [];
 let savedId = null;
 let resultReadFailures = 0;
 const pricing = {models:{classifier:'gpt-4.1-mini',research:'gpt-6.1-sol',brief:'gpt-4.1-mini',writer:'gpt-6.1-sol'},rates:{'gpt-4.1-mini':{input:0.4,output:1.6,cached_input:0.1},'gpt-6.1-sol':{input:2,output:10,cached_input:0.1,long_context_threshold:272000,long_input:4,long_output:15,long_cached_input:0.2}},source_url:'https://developers.openai.com/api/docs/pricing',verified_at:'2026-10-03'};
 const markdownFixture = '## Porównanie\n\n| Model | Cena |\n| --- | ---: |\n| A | 10 USD |\n\n```python\ndef greet(name):\n    return name\n```\n\nPolecenie `npm install`.';
 const stamp = '2026-10-03T10:00:00Z';
 const candidate = {id:1,source_id:1,source_name:'Test RSS',external_url:'https://example.com/article',title:'Testowy temat',summary:'Materiał testowy',original_published_at:stamp,status:'pending',relevance_score:null,freshness_score:null,search_potential_score:null,commercial_potential_score:null,total_score:null,category:null,llm_reason:null,classified_at:null,created_at:stamp,updated_at:stamp};
 const source = {id:1,name:'Test RSS',type:'rss',url:'https://example.com/rss',active:true,last_fetched_at:null,created_at:stamp,updated_at:stamp};
 const report = {id:1,candidate_id:1,status:'completed',summary:'Podsumowanie',why_it_matters:'Znaczenie',suggested_angle:'Perspektywa',search_queries:[],uncertainties:[],conflicts:[],error:null,llm_model:'test-model',llm_input_tokens:10,llm_output_tokens:10,estimated_cost_usd:null,started_at:stamp,completed_at:stamp,created_at:stamp,updated_at:stamp,sources:[],facts:[]};
 let posts = 0;
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
  if (route.request().method() === 'POST') posts++;
  if (path === '/api/jobs') body={items:jobs.filter(j=>['queued','running','retrying'].includes(j.status)),total:jobs.filter(j=>['queued','running','retrying'].includes(j.status)).length,page:1,page_size:100};
  else if (path === '/api/candidates/1/jobs') body={items:jobs,total:jobs.length,page:1,page_size:25};
  else if (/^\/api\/jobs\/[^/]+\/attempts$/.test(path)) body=[];
  else if (path.startsWith('/api/jobs/')) body=jobs.find(j=>j.id===path.split('/').at(-1));
  else if (path === '/api/pricing') body=pricing;
  else if (path === '/api/candidates/1/classify') { Object.assign(candidate,{total_score:79,relevance_score:90,freshness_score:80,search_potential_score:70,commercial_potential_score:60,category:'news',llm_reason:'Testowe uzasadnienie',classified_at:stamp,llm_model:'gpt-4.1-mini',llm_input_tokens:1000,llm_output_tokens:200,estimated_cost_usd:'0.000720'});body=job('classify');status=202;}
  else if (path === '/api/sources/fetch') { body={sources_processed:1,items_found:3,new_candidates:2,duplicates:1,skipped_old:0,errors:0};source.last_fetched_at=stamp; }
  else if (path === '/api/candidates/classify-pending') body={job_ids:[],enqueued:1,existing:0,skipped_busy:1};
  else if (path === '/api/sources') body=[source];
  else if (path === '/api/stats') body={candidates_today:1,new_today:1,approved:0,ignored:0,average_score:null};
  else if (path === '/api/candidates') body={items:[candidate],total:1,page:1,page_size:25};
  else if (path === '/api/candidates/1') body=candidate;
  else if (path === '/api/candidates/1/articles') {if (resultReadFailures>0) {resultReadFailures--;status=503;body={detail:'temporary read error'};} else body=articles;}
  else if (/^\/api\/articles\/\d+$/.test(path)) {
   body=articles.find(item=>item.id===Number(path.split('/').at(-1)));
   if (route.request().method()==='PATCH') {savedId=body.id;Object.assign(body,route.request().postDataJSON());}
  }
  else if (path === '/api/candidates/1/article') { article={id:1,candidate_id:1,version:1,is_current:true,status:'draft',title:'Testowy artykuł',article_type:'news',word_count:10,is_edited:false,estimated_cost_usd:'0.004720',llm_model:'gpt-6.1-sol',created_at:stamp,updated_at:stamp,research_id:1,slug:'test',lead:'Testowy lead',content:markdownFixture,generated_content:markdownFixture,meta_title:'Test',meta_description:'Test',angle:null,brief:{primary_angle:'Test',target_audience:'Test',key_points:[],required_facts:[],optional_facts:[],uncertainties_to_avoid:[],conflicts_to_mention:[],desired_length_words:100},sections:[],lead_fact_ids:[],generation_options:{},research_snapshot:{facts:[],sources:[]},validation_warnings:[],sections_count:0,facts_used_count:0,facts_available_count:0,source_count:0,llm_input_tokens:2000,llm_output_tokens:400,brief_llm_model:'gpt-4.1-mini',brief_input_tokens:1000,brief_output_tokens:200,brief_cost_usd:'0.000720',writer_input_tokens:1000,writer_output_tokens:200,writer_cost_usd:'0.004000'}; articles=[article];resultReadFailures=1;body=job('write');status=202;}
  else if (path === '/api/candidates/1/research') {
   if (route.request().method() === 'POST') {research={...report,status:'running',completed_at:null};body=job('research','running');status=202;}
   else if (research) body=research; else {status=404;body={detail:'No research'};}
  } else throw new Error('Unexpected request '+path);
  await route.fulfill({status,contentType:'application/json',headers:{'Access-Control-Allow-Origin':'*'},body:JSON.stringify(body)});
 });
 await page.goto(`http://localhost:${uiPort}`);
 await page.getByText('Testowy temat',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Pobierz RSS',exact:true}).click();
 await page.getByText(/Pobieranie RSS: 1 źródeł/).waitFor();
 await page.getByRole('button',{name:'Oceń nieocenione · płatne',exact:true}).click();
 await page.getByText(/Ocena AI: W kolejce: 1 nowych zadań/).waitFor();
 await page.screenshot({path:'/tmp/content-dashboard.png',fullPage:true});
 await page.getByText('Testowy temat',{exact:true}).click();
 await page.getByRole('link',{name:'Candidates',exact:true}).click();
 await page.getByText(/Pobieranie RSS: 1 źródeł/).waitFor();
 await page.getByText(/Ocena AI: W kolejce: 1 nowych zadań/).waitFor();
 await page.getByText('Testowy temat',{exact:true}).click();
 const generate=page.getByRole('button',{name:'Generuj artykuł · płatne',exact:true});
 await generate.waitFor(); assert.equal(await generate.isDisabled(),true);
 assert.equal(await page.locator('section[data-workflow-step]').count(), 4, 'each stage must own its content');
 for (let step = 1; step <= 4; step++) {
  const section = page.locator(`section[data-workflow-step="${step}"]`);
  assert.equal(await section.locator('header [role="status"]').count(), 1, 'one status in the shared header');
  assert.equal(await section.locator('header [data-cost]').count(), 1, 'one cost badge in the shared header');
  assert.equal(await section.locator('footer').getByText('Podsumowanie uruchomienia', {exact:true}).count(),1);
 }
 assert.equal(await page.locator('section[data-workflow-step="1"]').getByText('Materiał testowy', {exact:true}).count(), 1);
 assert.equal(await page.locator('section[data-workflow-step="2"] header').getByRole('button', {name:'Oceń temat · płatne',exact:true}).count(), 1);
 assert.equal(await page.locator('section[data-workflow-step="3"] header').getByRole('button', {name:'Uruchom research · płatne',exact:true}).count(), 1);
 assert.equal(await page.locator('section[data-workflow-step="4"] header').getByRole('button', {name:'Generuj artykuł · płatne',exact:true}).count(), 1);
 await page.locator('section[data-workflow-step="2"] header').getByRole('button',{name:'Oceń temat · płatne',exact:true}).click();
 await page.getByText('Testowe uzasadnienie',{exact:true}).waitFor();
 await page.locator('section[data-workflow-step="2"] footer').getByText('1000 / 200',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Uruchom research · płatne',exact:true}).click();
 await page.getByText('Research w toku…',{exact:true}).waitFor();
 assert.equal(await generate.isDisabled(),true);
 // Odświeżenie musi odtworzyć aktywne zadanie i zablokować drugą akcję.
 await page.reload();
 await page.getByText('Możesz zamknąć przeglądarkę. Zadanie wykona worker.',{exact:true}).waitFor();
 assert.equal(await generate.isDisabled(),true);
 jobs.find(j=>j.kind==='research').status='succeeded';
 research=report;
 await generate.waitFor();
 await page.waitForFunction(()=> [...document.querySelectorAll('button')].some(b=>b.textContent.includes('Generuj artykuł · płatne')&&!b.disabled));
 await page.locator('section[data-workflow-step="3"] footer').getByText('Koszt nieznany',{exact:true}).waitFor();
 await generate.click();
 await page.getByRole('button',{name:'Generuj · płatne wywołanie AI',exact:true}).waitFor();
 await page.screenshot({path:'/tmp/content-generate.png',fullPage:true});
 await page.getByRole('button',{name:'Generuj · płatne wywołanie AI',exact:true}).click();
 await page.getByRole('heading',{name:'Testowy artykuł',exact:true}).waitFor();
 const footer=page.locator('section[data-workflow-step="4"] footer');
 await footer.getByText('gpt-6.1-sol',{exact:true}).waitFor();
 await footer.getByText('gpt-4.1-mini',{exact:true}).waitFor();
 await footer.getByText(/Łączny zapisany koszt tej wersji: ≈ \$0.0047/).waitFor();
 await page.getByRole('dialog').waitFor({state:'hidden'});
 await page.locator('table th').getByText('Cena',{exact:true}).waitFor();
 await page.locator('pre code.language-python .hljs-keyword').first().waitFor();
 assert.match(await page.locator('pre code').innerText(), /\n    return name/);
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'/tmp/content-markdown-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});
 await page.screenshot({path:'/tmp/content-detail.png',fullPage:true});
 // Edytor pozostaje przypięty do v1, choć inne okno/workery kończą v2.
 await page.getByRole('button',{name:'Edytuj',exact:true}).click();
 await page.locator('section[data-workflow-step="4"] form input').first().fill('Ręcznie zmieniony tytuł v1');
 const firstArticle=article;
 article={...article,id:2,version:2,title:'Nowa generacja v2',content:'Nowa treść v2'};
 firstArticle.is_current=false;
 articles=[article,firstArticle];
 job('write','succeeded',2);
 await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
 await page.getByText('Wersja 2 ·',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Save changes',exact:true}).click();
 await page.getByRole('heading',{name:'Ręcznie zmieniony tytuł v1',exact:true}).waitFor();
 assert.equal(savedId,1,'editing v1 must not save into generated v2');
 assert.equal(article.title,'Nowa generacja v2');
 research={...report,llm_model:'gpt-6.1-sol',llm_input_tokens:300000,llm_output_tokens:1000};
 await page.reload();
 const researchFooter=page.locator('section[data-workflow-step="3"] footer');
 await researchFooter.getByText('$2 / $10',{exact:true}).waitFor();
 await researchFooter.getByText('Koszt nieznany',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'/tmp/content-mobile.png',fullPage:true});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 assert.equal(posts,5);
 await browser.close(); console.log('PASS: fetch results, queued batch, research restored after reload, polling, generation gate, paid dialog, mobile width. All API calls intercepted; no OpenAI traffic.');
})().catch(error=>{console.error(error);process.exit(1)});
