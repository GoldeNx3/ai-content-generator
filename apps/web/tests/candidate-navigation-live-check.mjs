import assert from 'node:assert/strict';
import{createRequire}from'node:module';
const require=createRequire(import.meta.url);const{chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});let writes=0;const errors=[];
 page.on('request',r=>{if(!['GET','HEAD'].includes(r.method())&&r.url().includes('/api/'))writes++;});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`http://localhost:${process.env.UI_TEST_PORT || '3000'}/candidates/${process.env.UI_TEST_CANDIDATE || '259'}`);
 const reader=page.locator('#article-workspace');await reader.getByRole('heading',{name:'Wybrany artykuł',exact:true}).waitFor();
 await reader.locator('article h2').first().waitFor();
 const nav=page.getByRole('navigation',{name:'Nawigacja po temacie i artykule'});await nav.getByRole('link',{name:'Artykuł',exact:true}).click();
 assert.equal(await reader.locator('article').isVisible(),true);assert.equal(await page.locator('#article-workspace').count(),1);
 assert.equal(await nav.getByRole('link',{name:'Artykuł',exact:true}).getAttribute('aria-current'),'location');
 for(const [label,id] of [['Temat','workflow-step-1'],['Ocena tematu','workflow-step-2'],['Research','workflow-step-3'],['Generowanie','workflow-step-4'],['QA · jakość','workflow-step-5'],['Poprawki i zatwierdzenie','workflow-step-6']]) {
   await nav.getByRole('link',{name:label,exact:true}).click();
   await page.locator('#'+id).waitFor({state:'visible'});
   assert.equal(await nav.getByRole('link',{name:label,exact:true}).getAttribute('aria-current'),'location');
   const panel=page.locator('#'+id);
   await panel.getByText('Jak działa ten etap?',{exact:true}).click();
   for(const label of ['Cel etapu','Warunki uruchomienia','Co dalej','Przebieg zadania','Wynik etapu','Podsumowanie uruchomienia']) {
     await panel.getByText(label,{exact:true}).waitFor();
   }
   await page.screenshot({path:`/tmp/content-${id}.png`,fullPage:true});
   assert.equal(await panel.locator('[data-stage-guide]').count(),1);
   assert.equal(await panel.locator('[data-stage-result]').count(),1);
   assert.equal(await reader.isVisible(),false);
   assert.equal(await page.locator('[data-workflow-step]:visible').count(),1);
 }
 await nav.getByRole('link',{name:'Artykuł',exact:true}).click();
 await reader.waitFor({state:'visible'});
 await page.goBack();
 await page.locator('#workflow-step-6').waitFor({state:'visible'});
 await page.goForward();
 await reader.waitFor({state:'visible'});
 await reader.getByRole('button',{name:/Historia wersji/}).click();await reader.getByRole('heading',{name:'Historia wersji',exact:true}).waitFor();
 await nav.getByRole('link',{name:'Artykuł',exact:true}).click();await reader.locator('article').waitFor();
 for(const width of [1440,768,390]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`overflow at ${width}`);await nav.getByRole('link',{name:'Artykuł',exact:true}).click();await page.screenshot({path:`/tmp/content-reader-${width}.png`,fullPage:width===1440});}
 await page.keyboard.press('Control+Home');await page.keyboard.press('Tab');await page.getByRole('link',{name:'Przejdź do treści',exact:true}).press('Enter');assert.equal(await page.evaluate(()=>document.activeElement?.id),'main-content');
 assert.equal(writes,0);assert.deepEqual(errors,[]);console.log('PASS: real candidate, 7 active views, isolated panels, history/read navigation, desktop/tablet/mobile, skip link, zero API writes.');
}finally{await browser.close();}
