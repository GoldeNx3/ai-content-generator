// Panel kolejki z całkowicie lokalnym API: żadnych żądań OpenAI ani realnego retry.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = process.env.UI_TEST_PORT || '3000';
const stamp = '2026-10-03T10:00:00Z';
const uuid = number => `00000000-0000-4000-8000-${String(number).padStart(12,'0')}`;
const statuses = ['failed','queued','running','retrying','succeeded'];
const jobs = Array.from({length:27},(_,index)=>({
 id:uuid(index+1),candidate_id:index+1,candidate_title:`Temat kolejki ${index+1}`,
 kind:['write','research','classify'][index%3],status:statuses[index%5],stage:index%5===1?null:'writing',
 attempt_count:index%5===1?0:1,max_attempts:3,created_at:stamp,available_at:stamp,
 started_at:index%5===1?null:stamp,finished_at:['failed','succeeded'].includes(statuses[index%5])?stamp:null,
 result_type:index%5===4?'article':null,result_id:index%5===4?index+1:null,
 error_code:index%5===0?'llm_http_503':null,error_message:index%5===0?'Dostawca nie odpowiedział.':null,
}));
const attempts = () => [{number:1,started_at:stamp,finished_at:stamp,outcome:'failed',error_message:'Dostawca nie odpowiedział.',llm_calls:[
 {stage:'building_brief',finished:true,estimated_cost_usd:'0.001200',usage:{model:'test-model',input_tokens:120,output_tokens:30}},
 {stage:'writing',finished:false,estimated_cost_usd:null,usage:null},
]}];
let retryPosts=0;
let staleAttemptReads=0;
let temporaryListFailure=false;
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.route('**/*', async route=>{
  const url=new URL(route.request().url());
  if (url.hostname==='127.0.0.1' && url.port===port) return route.continue();
  if (!url.pathname.startsWith('/api/')) return route.abort();
  let body; let status=200;
  if (url.pathname==='/api/jobs/stats') {
   body={queued:0,running:0,retrying:0,succeeded:0,failed:0,total:jobs.length};
   for (const job of jobs) body[job.status]++;
  } else if (url.pathname==='/api/jobs') {
   if (temporaryListFailure) {temporaryListFailure=false;status=503;body={detail:'Testowy błąd odczytu'};}
   else {
    const filter=url.searchParams.get('status');const kind=url.searchParams.get('kind');
    const selected=jobs.filter(job=>(filter==='all'||!filter||job.status===filter||(filter==='active'&&['queued','running','retrying'].includes(job.status)))&&(!kind||job.kind===kind));
    const number=Number(url.searchParams.get('page')||1);const size=Number(url.searchParams.get('page_size')||25);
    body={items:selected.slice((number-1)*size,number*size),total:selected.length,page:number,page_size:size};
   }
  } else if (url.pathname.endsWith('/retry')) {
   assert.equal(route.request().method(),'POST');
   assert.match(route.request().headers()['idempotency-key'], /^[a-f0-9-]{36}$/);
   const old=jobs.find(job=>job.id===url.pathname.split('/')[3]);
   const next={...old,id:uuid(100+retryPosts),status:'queued',stage:null,attempt_count:0,started_at:null,finished_at:null,error_code:null,error_message:null};
   jobs.unshift(next);body=next;status=202;retryPosts++;
  } else if (url.pathname.endsWith('/attempts')) {
   const current=jobs.find(job=>job.id===url.pathname.split('/')[3]);body=current.attempt_count?attempts():[];
   if (current.id===uuid(5)) {
    body[0].outcome=staleAttemptReads++===0?'running':'succeeded';
    if (body[0].outcome==='succeeded') body[0].llm_calls[1]={stage:'writing',finished:true,estimated_cost_usd:'0.009000',usage:{model:'test-model',input_tokens:10,output_tokens:20}};
   }
  } else if (url.pathname.startsWith('/api/jobs/')) body=jobs.find(job=>job.id===url.pathname.split('/')[3]);
  else throw new Error(`Unexpected request ${url.pathname}`);
  await route.fulfill({status,contentType:'application/json',headers:{'Access-Control-Allow-Origin':'*'},body:JSON.stringify(body)});
 });
 await page.goto(`http://127.0.0.1:${port}/queue`);
 await page.getByRole('heading',{name:'Kolejka zadań',exact:true}).waitFor();
 await page.getByText('27 zadań · strona 1/2',{exact:true}).waitFor();
 assert.equal(await page.getByRole('link',{name:'Kolejka',exact:true}).count(),1);
 await page.getByRole('button',{name:'Następna',exact:true}).click();
 await page.getByText('Temat kolejki 27',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Filtr: Błędy',exact:true}).click();
 await page.getByText('6 zadań · strona 1/1',{exact:true}).waitFor();
 assert.equal(await page.locator('tbody tr').count(),6);
 await page.getByRole('button',{name:`Szczegóły zadania ${uuid(1)}`,exact:true}).click();
 const dialog=page.getByRole('dialog');
 await dialog.getByText('Historia prób',{exact:true}).waitFor();
 await dialog.getByText('Zapisany koszt: ≈ $0.001200',{exact:true}).waitFor();
 await dialog.getByText('Koszt nieznany',{exact:true}).waitFor();
 assert.equal(await dialog.getByRole('link',{name:'Otwórz temat #1'}).getAttribute('href'),'/candidates/1');
 await dialog.getByRole('button',{name:'Ponów zadanie · płatne',exact:true}).click();
 await dialog.getByText('Worker jeszcze nie rozpoczął tego zadania.',{exact:true}).waitFor();
 assert.equal(retryPosts,1);
 assert.equal(await dialog.getByRole('button',{name:'Ponów zadanie · płatne',exact:true}).count(),0);
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Filtr: Oczekujące',exact:true}).click();
 await page.getByText('7 zadań · strona 1/1',{exact:true}).waitFor();
 jobs[0].status='succeeded';jobs[0].stage='saving';jobs[0].finished_at=stamp;
 await page.getByText('6 zadań · strona 1/1',{exact:true}).waitFor(); // polling bez kliknięcia
 await page.getByRole('button',{name:'Filtr: Sukcesy',exact:true}).click();
 await page.getByRole('combobox',{name:'Etap',exact:true}).click();
 await page.getByRole('option',{name:'Research',exact:true}).click();
 await page.getByText('2 zadań · strona 1/1',{exact:true}).waitFor();
 // Odczyty mogą przeciąć końcowy commit: sukces joba nie zamraża starej próby.
 await page.getByRole('button',{name:`Szczegóły zadania ${uuid(5)}`,exact:true}).click();
 await dialog.getByText('Zapisany koszt: ≈ $0.009000',{exact:true}).waitFor();
 assert.ok(staleAttemptReads>=2,'terminal job details still refresh attempt ledger');
 await page.keyboard.press('Escape');
 temporaryListFailure=true;
 await page.getByRole('button',{name:'Odśwież',exact:true}).click();
 await page.locator('main [role="alert"]').getByText(/Testowy błąd odczytu/).waitFor();
 assert.equal(await page.locator('tbody tr').count(),2,'failed refresh keeps previous results');
 await page.locator('main [role="alert"]').waitFor({state:'hidden'});
 await page.reload();
 await page.getByText('28 zadań · strona 1/2',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'/tmp/content-queue-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});
 await page.screenshot({path:'/tmp/content-queue.png',fullPage:true});
 console.log('PASS: global status counts, filters, paging, attempts/costs, retry, live updates, read-error recovery, reload and mobile. No real API calls.');
} finally {await browser.close();}
