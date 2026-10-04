import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});let writes=0;const errors=[];
 page.on('request',r=>{if(!['GET','HEAD'].includes(r.method())&&r.url().includes('/api/'))writes++;});
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`http://localhost:${process.env.UI_TEST_PORT || '3000'}/candidates/${process.env.UI_TEST_CANDIDATE || '259'}`);
 const nav=page.getByRole('navigation',{name:'Nawigacja po temacie i artykule'});
 await nav.getByRole('link',{name:'Temat',exact:true}).waitFor();
 assert.equal(await nav.getByRole('link').count(),6);
 for(const [index,label] of ['Temat','Ocena tematu','Research','Generowanie','QA / jakość','Poprawki i zatwierdzenie'].entries()) {
  await nav.getByRole('link',{name:label,exact:true}).click();
  const panel=page.locator(`#workflow-step-${index+1}`);await panel.waitFor({state:'visible'});
  assert.equal(await nav.getByRole('link',{name:label,exact:true}).getAttribute('aria-current'),'step');
  assert.equal(await page.locator('[data-workflow-step]:visible').count(),1);
  const main=panel.locator('[data-stage-result]'),side=panel.getByRole('complementary');
  const mainBox=await main.boundingBox(),sideBox=await side.boundingBox();assert.ok(sideBox.x>mainBox.x+mainBox.width,'desktop sidebar next to main');
  await panel.getByText('Jak działa ten etap?',{exact:true}).click();
  for(const text of ['Cel etapu','Warunki uruchomienia','Co dalej','Przebieg zadania','Podsumowanie uruchomienia'])await panel.getByText(text,{exact:true}).waitFor();
  await panel.getByText('Jak działa ten etap?',{exact:true}).click();
  await page.screenshot({path:`/tmp/pipeline-stage-${index+1}-desktop.png`,fullPage:true});
 }
 await nav.getByRole('link',{name:'Generowanie',exact:true}).click();
 const reader=page.locator('#article-workspace');await reader.locator('article h2').first().waitFor();
 await reader.getByRole('button',{name:'SEO',exact:true}).click();await reader.getByRole('region',{name:'Dane SEO artykułu'}).waitFor();
 await reader.getByRole('button',{name:/Historia wersji/}).click();await reader.getByRole('heading',{name:'Historia wersji',exact:true}).waitFor();
 await reader.getByRole('button',{name:'Podgląd',exact:true}).click();await reader.locator('article').waitFor();
 await page.goBack();await page.locator('#workflow-step-6').waitFor({state:'visible'});
 await page.goForward();await reader.waitFor({state:'visible'});
 for(const width of [768,390]) {
  await page.setViewportSize({width,height:1000});
  const selector=nav.getByRole('combobox',{name:'Wybierz etap pipeline'});await selector.waitFor();
  for(let step=1;step<=6;step++){
   await selector.selectOption(`#workflow-step-${step}`);
   const panel=page.locator(`#workflow-step-${step}`);await panel.waitFor({state:'visible'});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`overflow at ${width}, stage ${step}`);
   const main=await panel.locator('[data-stage-result]').boundingBox(),side=await panel.getByRole('complementary').boundingBox();
   assert.ok(side.y>main.y,'mobile sidebar follows main');
   if(width===390)await page.screenshot({path:`/tmp/pipeline-stage-${step}-mobile.png`,fullPage:true});
  }
 }
 await page.keyboard.press('Control+Home');await page.keyboard.press('Tab');await page.getByRole('link',{name:'Przejdź do treści',exact:true}).press('Enter');
 assert.equal(await page.evaluate(()=>document.activeElement?.id),'main-content');
 const duplicates=await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.filter((id,i)=>ids.indexOf(id)!==i);});
 assert.deepEqual(duplicates,[]);assert.equal(writes,0);assert.deepEqual(errors,[]);
 console.log('PASS: six real stages, shared sidebar/help/results, article/SEO/history, back/forward, all stages desktop/tablet/mobile, no duplicate IDs, keyboard, zero API writes.');
}finally{await browser.close();}
