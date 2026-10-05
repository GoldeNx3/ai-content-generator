import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const port=process.env.UI_TEST_PORT||'3001';
const stamp='2026-10-05T00:00:00Z';
const candidate={id:1,source_id:1,source_name:'RSS',external_url:'https://example.com/article',title:'Temat ze statusem publikacji',summary:'Test',original_published_at:stamp,status:'approved',workflow_status:'published',total_score:90,category:'news',created_at:stamp,updated_at:stamp};
let observedFilter;
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(['localhost','127.0.0.1'].includes(url.hostname)&&url.port===port)return route.continue();
  let body;
  if(url.pathname==='/api/candidates'){
   observedFilter=url.searchParams.get('workflow_status');
   const items=!observedFilter||observedFilter===candidate.workflow_status?[candidate]:[];
   body={items,total:items.length,page:1,page_size:25};
  } else if(url.pathname==='/api/stats')body={candidates_today:1,new_today:1,approved:1,ignored:0,average_score:90};
  else if(url.pathname==='/api/sources')body=[];
  else if(url.pathname==='/api/jobs')body={items:[],total:0,page:1,page_size:100};
  else throw new Error('Unexpected request '+url.pathname);
  assert.equal(route.request().method(),'GET','status checks never publish or invoke an agent');
  await route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto(`http://localhost:${port}/`);
 const table=page.getByRole('table',{name:'Lista tematów',exact:true});
 for(const [status,label] of [['published','Opublikowane'],['draft','Draft'],['approved','Zatwierdzony'],['scheduled','Zaplanowane']]){
  candidate.workflow_status=status;
  await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
  await table.getByText(label,{exact:true}).waitFor();
 }
 candidate.workflow_status='published';
 await page.getByRole('combobox',{name:'Status',exact:true}).click();
 await page.getByRole('option',{name:'Opublikowane',exact:true}).click();
 await table.getByText('Opublikowane',{exact:true}).waitFor();
 assert.equal(observedFilter,'published','filter uses the same workflow status as the badge');
 await page.getByRole('combobox',{name:'Status',exact:true}).click();
 await page.getByRole('option',{name:'Draft',exact:true}).click();
 await table.getByText('Brak tematów. Dodaj źródło RSS i wybierz „Pobierz RSS”.',{exact:true}).waitFor();
 assert.equal(observedFilter,'draft');
 console.log('PASS: published/draft/approved/scheduled badges, refresh on return, matching workflow filter. No writes.');
}finally{await browser.close();}
