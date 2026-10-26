import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1280,height:1000},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.join(root,'delivery/deck-build/readme.html')).href);await page.waitForLoadState('load');
 const images=await page.locator('img').evaluateAll(items=>items.map(x=>({src:x.getAttribute('src'),ok:x.complete&&x.naturalWidth>0})));
 if(images.some(x=>!x.ok))throw Error('README contains a missing image');
 await page.screenshot({path:path.join(root,'delivery/deck-build/readme-top.png')});
 for(const [name,title]of [['profiles','Profiles lets a consumer detect the dependency early'],['limits','Separate proposal quality from prototype coverage']]){
  await page.getByRole('heading',{name:title,exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root,`delivery/deck-build/readme-${name}.png`)});
 }
 await fs.writeFile(path.join(root,'delivery/deck-build/readme-visual-check.json'),JSON.stringify({images,headings:await page.locator('h2').allTextContents()},null,2));
 console.log('README rendered; all source figures loaded');
}finally{await browser.close();}
