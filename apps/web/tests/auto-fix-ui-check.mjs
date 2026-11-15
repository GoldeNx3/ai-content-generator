import { wordpressState } from './fixtures/wordpress-state.mjs';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import { authenticate, corsHeaders } from './fixtures/auth.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const port=process.env.UI_TEST_PORT||'3000';
const stamp='2026-10-04T10:00:00Z';
const candidate={id:1,source_id:1,source_name:'RSS',external_url:'https://example.com/article',title:'Temat Auto Fix',summary:'Test',original_published_at:stamp,status:'approved',relevance_score:90,freshness_score:90,search_potential_score:90,commercial_potential_score:90,classified_at:stamp,llm_reason:'Test',total_score:90,category:'news',created_at:stamp,updated_at:stamp};
const research={id:1,candidate_id:1,status:'completed',summary:'Fakty',search_queries:[],sources:[],facts:[],uncertainties:[],conflicts:[],created_at:stamp,updated_at:stamp};
const first={id:1,candidate_id:1,version:1,is_current:true,status:'needs_changes',title:'Artykuł v1',article_type:'news',article_format:'news',word_count:30,is_edited:false,qa_passed:false,parent_version_id:null,created_by:'generated',auto_fix_iteration:0,auto_fix_iterations_remaining:2,qa_score:75,qa_status:'completed',content_hash:'a',created_at:stamp,updated_at:stamp,
  slug:'artykul-v1',lead:'Potwierdzony lead.',content:'## Test\n\nPotwierdzona treść. Wzrost o 47%.',generated_content:'',meta_title:'Artykuł',meta_description:'Opis',brief:{required_facts:[],optional_facts:[],key_points:[],section_plan:[]},sections:[],generation_options:{},research_snapshot:{facts:[],sources:[]},validation_warnings:[],lead_fact_ids:[],sections_count:1,facts_used_count:0,facts_available_count:0,source_count:0,llm_input_tokens:0,llm_output_tokens:0,brief_input_tokens:0,brief_output_tokens:0,writer_input_tokens:0,writer_output_tokens:0};
const qa1={id:1,article_id:1,article_version:1,status:'completed',overall_score:75,factual_score:70,source_score:90,style_score:90,structure_score:90,seo_score:90,supported_claims_count:4,unsupported_claims_count:1,critical_issue_count:0,warning_count:1,summary:'Niepoparta liczba.',qa_passed:false,pass_score:85,is_stale:false,issues:[{id:41,type:'unsupported_claim',severity:'high',excerpt:'Wzrost o 47%.',reason:'Brak faktu.',suggestion:'Usuń.',section_heading:'Test',fact_ids:[],source_ids:[],auto_fixable:true}]};
let wordpressConflict=false;
let versions=[first],qas={1:qa1},fix=null,jobs=[],posts=0,approveId=null,manualId=null,holdVersionRead=false,releaseVersionRead=null;
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',error=>console.error('PAGE ERROR',error.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url()),path=url.pathname,method=route.request().method();
  if(['localhost','127.0.0.1'].includes(url.hostname)&&url.port===port)return route.continue();
  if(!path.startsWith('/api/'))return route.abort();
  let body,status=200;if(method==='POST')posts++;
  if(path==='/api/candidates/1')body=candidate;
  else if(path==='/api/candidates/1/research')body=research;
  else if(path==='/api/candidates/1/suggestions')body=[];
  else if(path==='/api/candidates/1/articles')body=versions;
  else if(path==='/api/candidates/1/jobs')body={items:jobs,total:jobs.length,page:1,page_size:25};
  else if(path==='/api/pricing')body={models:{classifier:'gpt-4.1',research:'gpt-4.1',writer:'gpt-4.1',brief:'gpt-4.1',qa:'gpt-4.1',auto_fix:'gpt-4.1'},rates:{'gpt-4.1':{input:2,output:8}}};
  else if(/^\/api\/article-versions\/\d+\/wordpress$/.test(path)){body=wordpressState(Boolean(qas[Number(path.split("/")[3])]?.qa_passed));if(wordpressConflict)body.conflict={current_hash:"remote-hash",post_id:123};}
  else if(/^\/api\/article-versions\/\d+\/fixes$/.test(path))body=fix?[fix]:[];
  else if(path==='/api/article-versions/1/auto-fix'){
   assert.match(route.request().headers()['idempotency-key'],/^[a-f0-9-]{36}$/);
   fix={id:1,source_article_version_id:1,result_article_version_id:null,qa_id:1,job_id:'fix-job',status:'pending',iteration:1,issues_requested:1,issues_fixed:0,issues_skipped:0,summary:null,warnings:[],changes:[],issues:[],llm_model:'gpt-4.1',llm_input_tokens:1000,llm_output_tokens:200,estimated_cost_usd:'0.003600'};
   body={id:'fix-job',article_id:1,candidate_id:1,kind:'auto_fix_article',status:'queued',stage:null,attempt_count:0,max_attempts:3,created_at:stamp,available_at:stamp};jobs=[body];status=202;
  }else if(/^\/api\/articles\/\d+\/qa$/.test(path)){
   if(method==='POST') {
     const id=Number(path.split('/')[3]);qas[id]={...qa1,id,article_id:id,article_version:id,status:'pending',qa_passed:false,issues:[]};
     body={id:'qa-job',article_id:id,candidate_id:1,kind:'qa_article',status:'queued',attempt_count:0,max_attempts:3,created_at:stamp};jobs.unshift(body);status=202;
   } else { body=qas[Number(path.split('/')[3])];if(!body){body={detail:'No QA'};status=404;} }
  }else if(/^\/api\/articles\/\d+$/.test(path)){
   body=versions.find(v=>v.id===Number(path.split('/')[3]));
   if(method==='GET' && body.id===1 && holdVersionRead) await new Promise(resolve=>{releaseVersionRead=resolve;});
   if(method==='PATCH'){
    manualId=body.id;const newVersion={...body,...route.request().postDataJSON(),id:3,version:3,parent_version_id:body.id,created_by:'manual_edit',status:'draft',qa_passed:false,is_current:true,qa_score:null,qa_status:'required'};
    versions.forEach(v=>v.is_current=false);versions.unshift(newVersion);body=newVersion;
   }
  }else if(path==='/api/article-versions/2/approve'){
   approveId=2;body=versions.find(v=>v.id===2);body.status='approved';body.approved_at=stamp;
  }else if(/^\/api\/jobs\/.*\/attempts$/.test(path))body=[];
  else throw new Error('Unexpected API '+method+' '+path);
  await route.fulfill({status,contentType:'application/json',headers:corsHeaders(route),body:JSON.stringify(body)});
 });
 await authenticate(page);
 await page.goto(`http://localhost:${port}/candidates/1`);
 assert.equal(await page.locator('html').getAttribute('lang'),'pl');
 const navigation=page.getByRole('navigation',{name:'Nawigacja po temacie i artykule',exact:true});
 await navigation.getByRole('link',{name:'Generowanie',exact:true}).waitFor();
 assert.equal(await navigation.getByRole('link',{name:'Generowanie',exact:true}).getAttribute('href'),'#workflow-step-4');
 assert.equal(await navigation.getByRole('link').count(),7);
 // A running agent owns only its stage; every agent uses the same ticking progress card.
 for(const [kind,number,label] of [['classify',2,'Ocena tematu'],['research',3,'Research'],['write',4,'Generowanie'],['qa_article',5,'QA / jakość'],['auto_fix_article',6,'Poprawki i zatwierdzenie']]) {
   jobs=[{id:`progress-${kind}`,candidate_id:1,article_id:1,kind,status:'running',stage:kind==='qa_article'?'fact_checking':null,attempt_count:1,max_attempts:3,created_at:stamp,started_at:new Date(Date.now()-5000).toISOString()}];
   await page.reload();await navigation.getByRole('link',{name:label,exact:true}).click();
   const progress=page.locator(`[data-workflow-step="${number}"] [data-agent-progress]`);
   await progress.waitFor();
   assert.equal(await page.locator('[data-agent-progress]').count(),1,`${kind} only runs in its own stage`);
   assert.equal(await page.locator(`[data-workflow-step="${number}"]`).getAttribute('data-stage-tone'),'running');
   if(kind==='qa_article') {
     assert.notEqual(await page.locator('[data-workflow-step="6"]').getAttribute('data-stage-tone'),'running','QA never runs Auto Fix');
     const before=Number(await progress.locator('[data-job-elapsed]').getAttribute('data-job-elapsed'));
     await page.waitForFunction(previous=>Number(document.querySelector('[data-agent-progress] [data-job-elapsed]').dataset.jobElapsed)>previous,before);
     await page.reload();await progress.waitFor();
     assert.ok(Number(await progress.locator('[data-job-elapsed]').getAttribute('data-job-elapsed'))>=before,'reload keeps elapsed execution time');
   }
 }
 jobs=[];await page.reload();
 await navigation.getByRole('link',{name:'Generowanie',exact:true}).click();
 const workspace=page.locator('#article-workspace');
 await workspace.getByRole('heading',{name:'Wybrany artykuł',exact:true}).waitFor();
 await workspace.getByRole('heading',{name:'Artykuł v1',exact:true}).waitFor();
 assert.equal(await workspace.getByText('Potwierdzona treść. Wzrost o 47%.',{exact:true}).isVisible(),true);
 const qa=page.locator('[data-workflow-step="5"]'),fixStep=page.locator('[data-workflow-step="6"]');
 // Passed QA may still offer optional editorial fixes before approval.
 qas[1]={...qa1,qa_passed:true,overall_score:94,unsupported_claims_count:0,
   issues:[{...qa1.issues[0],type:'structure_issue',severity:'warning'}]};
 first.status='ready_for_approval';first.qa_passed=true;
 await page.reload();
 await navigation.getByRole('link',{name:'Poprawki i zatwierdzenie',exact:true}).click();
 await page.waitForFunction(()=>Array.from(document.querySelectorAll('[data-workflow-step="6"] button')).some(b=>b.textContent.includes('Popraw automatycznie')&&!b.disabled));
 assert.equal(await fixStep.getByRole('button',{name:'Zatwierdź wersję',exact:true}).isEnabled(),true);
 assert.equal(await fixStep.getAttribute('data-stage-tone'),'attention','passed QA awaits a manual decision; approval step is not complete');
 assert.equal(await fixStep.getByRole('button',{name:'Popraw automatycznie · płatne',exact:true}).isVisible(),true);
 assert.equal(approveId,null,'optional fix is available without approval');
 assert.equal(posts,0,'reading passed QA starts no stage automatically');
 qas[1]=qa1;first.status='needs_changes';first.qa_passed=false;
 await page.reload();
 await navigation.getByRole('link',{name:'QA / jakość',exact:true}).click();
 assert.equal(await navigation.getByRole('link',{name:'QA / jakość',exact:true}).getAttribute('aria-current'),'step');
 assert.equal(await workspace.isVisible(),false);
 await qa.getByText('Problemy: 1 · automatycznie: 1 · ręcznie: 0',{exact:true}).waitFor();
 assert.equal(await qa.getByRole('button',{name:/Napraw automatycznie|Popraw automatycznie|Popraw ręcznie/}).count(),0,'QA only evaluates; correction actions belong to step 6');
 await qa.getByRole('button',{name:'Przejdź do poprawek i zatwierdzenia',exact:true}).click();
 assert.equal(posts,0,'moving from QA to fixes never starts an agent');
 await fixStep.getByRole('button',{name:'Popraw automatycznie · płatne',exact:true}).click();
 await fixStep.waitFor({state:'visible'});
 assert.equal(await navigation.getByRole('link',{name:'Poprawki i zatwierdzenie',exact:true}).getAttribute('aria-current'),'step');
 await fixStep.getByText('Auto Fix · próba 1 · Poprawianie…',{exact:true}).waitFor();
 assert.equal(await fixStep.getByRole('button',{name:'Poprawianie…',exact:true}).isDisabled(),true);
 fix.status='running';jobs[0].status='running';jobs[0].stage='fixing_article';
 await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
 await fixStep.locator('[data-agent-progress]').getByText('Poprawianie artykułu',{exact:true}).waitFor();
 fix.status='completed';fix.result_article_version_id=2;fix.issues_fixed=1;fix.summary='Usunięto niepopartą liczbę.';
 fix.changes=[{field:'content',before:'Wzrost o 47%.',after:'',qa_issue_ids:[41],fact_ids:[],source_ids:[]}];
 fix.issues=[{id:1,qa_issue_id:41,status:'fixed',reason:'Usunięto.',created_at:stamp}];jobs[0].status='succeeded';jobs[0].result_id=1;jobs[0].result_type='article_fix';
 first.is_current=false;
 const second={...first,id:2,version:2,parent_version_id:1,created_by:'auto_fix',auto_fix_iteration:1,auto_fix_iterations_remaining:1,is_current:true,status:'draft',qa_score:null,qa_status:'pending',content:'## Test\n\nPotwierdzona treść.'};versions.unshift(second);
 await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
 await qa.locator('[data-qa-target="2"]').waitFor({state:"attached"});
 await fixStep.getByText('Poprawiono: 1 · pominięto: 0',{exact:true}).waitFor();
 assert.equal(await fixStep.getByRole('button',{name:'Zatwierdź wersję',exact:true}).isDisabled(),true);
 assert.equal(jobs.some(job=>job.kind==='qa_article'),false,'Auto Fix does not automatically queue QA');
 await fixStep.getByRole('button',{name:'Przejdź do QA wybranej wersji',exact:true}).click();
 await qa.getByRole('button',{name:'Uruchom QA · płatne',exact:true}).click();
 const qaJob=jobs.find(job=>job.kind==='qa_article');
 await qa.locator('[data-agent-progress="qa_article"]').waitFor();
 assert.notEqual(await fixStep.getAttribute('data-stage-tone'),'running','QA does not mark fixes as running');
 qas[2]={...qas[2],status:'completed',overall_score:94,critical_issue_count:0,unsupported_claims_count:0,qa_passed:true};qaJob.status='succeeded';second.status='ready_for_approval';second.qa_passed=true;second.qa_score=94;second.qa_status='completed';
 await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
 await qa.getByText("Raport jakości",{exact:true}).waitFor();
 await navigation.getByRole('link',{name:'QA / jakość',exact:true}).click();
 holdVersionRead=true;
 await qa.getByRole('combobox',{name:'Wersja artykułu do QA',exact:true}).click();
 await page.getByRole('option',{name:'Wersja 1',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('[data-workflow-step="5"] [role="combobox"]')?.hasAttribute('aria-disabled') || document.querySelector('[data-workflow-step="5"] [role="combobox"]')?.disabled);
 assert.equal(await fixStep.getByRole('button',{name:'Zatwierdź wersję',exact:true,includeHidden:true}).isDisabled(),true,'approval disabled while selecting another version');
 assert.equal(await fixStep.getByRole('button',{name:'Odrzuć wersję',exact:true,includeHidden:true}).isDisabled(),true);
 assert.equal(await fixStep.getByRole('button',{name:'Edytuj tekst',exact:true,includeHidden:true}).isDisabled(),true);
 for(let i=0;!releaseVersionRead&&i<20;i++)await page.waitForTimeout(50);
 assert.ok(releaseVersionRead);holdVersionRead=false;releaseVersionRead();
 await qa.locator('[data-qa-target="1"]').waitFor();
 await qa.getByRole('combobox',{name:'Wersja artykułu do QA',exact:true}).click();
 await page.getByRole('option',{name:'Wersja 2 · aktualna · QA zaliczone',exact:true}).click();
 await qa.locator('[data-qa-target="2"]').waitFor();
 await navigation.getByRole('link',{name:'Poprawki i zatwierdzenie',exact:true}).click();
 await fixStep.getByRole('button',{name:'Zatwierdź wersję',exact:true}).click();
 await fixStep.getByText(/Zatwierdzono tę wersję/).waitFor();assert.equal(approveId,2);assert.equal(first.status,'needs_changes');
 assert.equal(await fixStep.getAttribute('data-stage-tone'),'success','only manual approval completes the approval stage');
 assert.equal(await fixStep.getByText('Zmienione fragmenty · Before / After',{exact:true}).evaluate(e=>e.closest('details').open),true);
 await fixStep.getByText('Usunięto fragment',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'/tmp/content-auto-fix-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:'/tmp/content-auto-fix.png',fullPage:true});
 assert.equal(await page.locator('#article-workspace').count(),1,'one workspace after repeated version selection');
 await fixStep.getByRole('button',{name:'Przejdź do publikacji',exact:true}).click();
 const wordpress=page.locator('[data-workflow-step="8"]');
 await page.waitForFunction(()=>[...document.querySelectorAll('#workflow-step-8 button')].some(button=>button.textContent==='Utwórz szkic w WordPressie'&&!button.disabled));
 assert.equal(await wordpress.getByRole('button',{name:'Utwórz szkic w WordPressie',exact:true}).isDisabled(),false);
 assert.equal(await wordpress.getByRole('button',{name:'Synchronizuj z WordPressem',exact:true}).isDisabled(),true);
 for(const width of [1440,375]) {
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`WordPress overflow at ${width}px`);
   await page.screenshot({path:`/tmp/candidate-wordpress-${width}.png`,fullPage:true});
 }
 wordpressConflict=true;
 await wordpress.getByRole('button',{name:'Sprawdź stan WordPress',exact:true}).click();
 await wordpress.getByRole('button',{name:'Nadpisz sprawdzoną treść WordPress…',exact:true}).click();
 const confirmation=wordpress.getByRole('alertdialog',{name:'Potwierdź operację WordPress'});
 await confirmation.waitFor();
 assert.equal(await confirmation.evaluate(el=>document.activeElement===el),true,'confirmation receives keyboard focus');
 assert.ok(await confirmation.evaluate(el=>el.getBoundingClientRect().top>=0 && el.getBoundingClientRect().top<innerHeight),'confirmation appears in viewport on mobile');
 for (const width of [375, 1440]) {
   await page.setViewportSize({width,height:900});
   assert.equal(await confirmation.evaluate(el=>{
     const box=el.getBoundingClientRect();
     return Array.from(el.querySelectorAll('button')).every(button=>{
       const rect=button.getBoundingClientRect();
       return rect.left>=box.left && rect.right<=box.right;
     });
   }),true,`confirmation buttons fit their box at ${width}px`);
 }
 await confirmation.getByRole('button',{name:'Anuluj',exact:true}).click();
 wordpressConflict=false;
 await wordpress.getByRole('button',{name:'Sprawdź stan WordPress',exact:true}).click();
 await wordpress.getByRole('button',{name:'Opublikuj teraz',exact:true}).click();
 await confirmation.getByText('Opublikować tę zatwierdzoną wersję teraz? Wpis stanie się publiczny.',{exact:true}).waitFor();
 for (const width of [375, 1440]) {
   await page.setViewportSize({width,height:900});
   assert.equal(await confirmation.evaluate(el=>{
     const box=el.getBoundingClientRect();
     return Array.from(el.querySelectorAll('button')).every(button=>{
       const rect=button.getBoundingClientRect();
       return rect.left>=box.left && rect.right<=box.right;
     });
   }),true,`publication confirmation buttons fit at ${width}px`);
   await page.screenshot({path:`/tmp/wordpress-confirmation-${width}.png`});
 }
 await confirmation.getByRole('button',{name:'Anuluj',exact:true}).click();
 await page.setViewportSize({width:1440,height:1000});
 await navigation.getByRole('link',{name:'Generowanie',exact:true}).click();
 await workspace.getByRole('button',{name:'Edytuj tekst',exact:true}).click();
 await workspace.getByRole('textbox',{name:'Tytuł',exact:true}).fill('Ręcznie poprawiona v3');
 await navigation.getByRole('link',{name:'QA / jakość',exact:true}).click();
 await navigation.getByRole('link',{name:'Generowanie',exact:true}).click();
 assert.equal(await workspace.getByRole('textbox',{name:'Tytuł',exact:true}).inputValue(),'Ręcznie poprawiona v3','view switches preserve unsaved edits');
 await workspace.getByRole('button',{name:'Zapisz nową wersję',exact:true}).click();
 await navigation.getByRole('link',{name:'QA / jakość',exact:true}).click();
 await qa.locator('[data-qa-target="3"]').waitFor();await qa.getByText('QA jeszcze nie uruchomiono',{exact:true}).waitFor();
 assert.equal(manualId,2);assert.equal(second.title,'Artykuł v1');assert.equal(second.status,'approved');assert.equal(posts,3);
 console.log('PASS: Auto Fix queued, new version + manual QA, fixed/skipped/diff, version-specific approval, immutable manual edit, mobile. No LLM traffic.');
} finally {await browser.close();}
