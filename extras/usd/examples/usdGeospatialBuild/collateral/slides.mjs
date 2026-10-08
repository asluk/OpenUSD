// Quality-first editable deck derived from README story sections.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [skillDir,runtimePython,workspaceDir,name='geospatial-quality-v1.pptx']=process.argv.slice(2);
const {finalizePresentation,resolvePresentationFont}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
if(createHash('sha256').update(await fs.readFile(path.join(root,'README.md'))).digest('hex')!==story.readme_sha256)throw Error('README changed; derive again');
const font=resolvePresentationFont();const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#163641',teal:'#117E89',muted:'#526D76',paper:'#F5F8F9',white:'#FFFFFF',light:'#E4EFF1',amber:'#AC6A18'};
const clean=t=>String(t).replace(/\[([^\]]+)\]\([^)]+\)/g,'$1').replace(/[`*]/g,'');
function text(s,value,x,y,w,h,size=25,color=C.ink,bold=false){const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});o.text=clean(value);o.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none',verticalAlignment:'middle'};return o;}
async function img(s,n,x,y,w,h){s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'delivery',n))),contentType:'image/png',alt:n,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function paras(c){return c.split('\n\n').filter(x=>!x.startsWith('![')&&!x.startsWith('|')&&!x.startsWith('#')&&!x.startsWith('['));}
function tables(c){const groups=[];let cur=[];for(const l of c.split('\n')){if(l.startsWith('|'))cur.push(l);else if(cur.length){groups.push(cur);cur=[];}}if(cur.length)groups.push(cur);return groups.map(g=>g.filter(l=>!/^\|[\s:\-|]+\|$/.test(l)).map(l=>l.split('|').slice(1,-1).map(x=>clean(x.trim()))));}
function table(s,values,x,y,w,h,widths,size=23){const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});t.borders.assign({style:'solid',fill:C.white,width:1});for(let i=0;i<values.length;i++)for(let j=0;j<values[0].length;j++){const c=t.getCell(i,j);c.fill=i===0?C.ink:(i%2?C.white:C.light);c.text.style={typeface:font,fontSize:size,color:i===0?C.white:C.ink,bold:i===0,autoFit:'none'};}return t;}
function bulletLines(s,lines,y=305,size=25,gap=95){for(let i=0;i<lines.length;i++){text(s,String(i+1).padStart(2,'0'),52,y+i*gap,55,40,21,C.teal,true);text(s,lines[i],128,y+i*gap,1096,gap-10,size);}}
for(let index=0;index<story.slides.length;index++){
 const d=story.slides[index],s=p.slides.add();s.background.fill=C.paper;
 text(s,d.title,52,44,1174,92,39,C.ink,true);
 text(s,'PROPOSAL READINESS: BLOCKED • EXPERIMENTAL EVIDENCE',52,681,1100,22,13,C.muted);text(s,String(index+1).padStart(2,'0'),1180,681,45,22,14,C.muted);
 const ps=paras(d.content),ts=tables(d.content);
 if(d.kind==='readiness'){
  text(s,'Not yet independently implementable',52,178,1170,100,44,C.amber,true);
  text(s,d.summary,52,310,1148,159,27);
  text(s,ps[1],52,518,1148,128,23,C.muted);
 }else if(d.kind==='gaps'){
  text(s,d.summary,52,148,1174,104,24);
  const [lo,hi]=d.table_slice;const rows=ts[0];table(s,[rows[0],...rows.slice(lo+1,hi+1)],52,280,1176,345,[90,750,336],23);
  text(s,'Existing functional intent → complete the missing model and runtime contract before dependent derivation.',52,636,1160,32,20,C.muted);
 }else if(d.kind==='process'){
  text(s,ps[0],52,156,1174,126,25);
  const statements=ps[1].split(/(?<=\.)\s+/).slice(0,3);bulletLines(s,statements,305,25,94);
  text(s,ps.at(-1),52,605,1174,63,20,C.teal,true);
 }else if(d.kind==='repairs'){
  text(s,ps[0],52,157,1160,133,24);
  text(s,ps[1],52,316,1160,167,24);
  text(s,ps[2],52,519,1160,142,21,C.muted);
 }else if(d.kind==='dependency'){
  text(s,ps[0],52,157,1160,133,27);
  text(s,ps[1],52,328,1160,135,26,C.teal,true);
  text(s,ps[2],52,510,1160,141,24,C.muted);
 }else if(d.kind==='extent'){
  text(s,ps[0],52,152,1172,132,25);
  const rows=ts[0].map((r,i)=>i===0?[r[0],'Points',r[2]]:[r[0],r[1],(()=>{const m=parseFloat(r[2]);return m<.001?(m*1e6).toPrecision(3)+' µm':m<.1?(m*1000).toPrecision(4)+' mm':m.toPrecision(4)+' m';})()]);
  table(s,rows,52,311,655,297,[250,100,305],22);
  text(s,ps[2].split(/(?<=\.)\s+/).slice(0,2).join(' '),759,319,467,207,28,C.amber,true);
  text(s,ps[3].split(/(?<=\.)\s+/)[0],759,550,467,94,20,C.muted);
 }else if(d.kind==='numeric'){
  text(s,ps[0],52,152,1172,118,25);
  table(s,ts[0],52,312,1176,228,[429,249,249,249],23);
  text(s,ps[1],52,574,1176,84,23,C.muted);
 }else if(d.kind==='images'){
  text(s,d.summary,52,151,1176,89,24);
  await img(s,d.images[0],52,268,570,298);await img(s,d.images[1],657,268,570,298);
  const evidence=ps.find(x=>x.startsWith('The first image'))||ps.find(x=>x.startsWith('The LandXML'))||ps.find(x=>x.startsWith('The initial scalar'));
  text(s,evidence||ps[1],52,591,1176,73,19,C.muted);
 }else if(d.kind==='single'){
  text(s,d.summary,52,148,1176,d.section.startsWith('Composition')?126:96,24);
  await img(s,d.images[0],52,d.section.startsWith('Composition')?296:268,815,d.section.startsWith('Composition')?338:367);
  let evidence;
  if(d.section.startsWith('Composition')){const sentences=ps[1].split(/(?<=\.)\s+/);evidence=sentences[0]+'\n\n'+sentences.at(-1);}
  else{const block=d.content.split('\n\n').find(x=>x.startsWith('[Selected GeoJSON'));evidence=block.split(/(?<=\.)\s+/).slice(1).join(' ');}
  text(s,evidence,919,d.section.startsWith('Composition')?309:280,309,318,23,C.muted);
 }else if(d.kind==='closure'){
  text(s,ps[0],52,154,1174,194,29,C.teal,true);
  text(s,ps[1],52,396,1174,164,26);
  text(s,ps[2],52,606,1174,59,22,C.muted);
 }
 s.speakerNotes.textFrame.setText(`Canonical README section: ${d.section}. README SHA-256: ${story.readme_sha256}\n${d.content}\nProposal readiness is blocked. Experimental choices and evidence do not approve the standard.`);
}
const staging=path.join(workspaceDir,'.codex-finalizer');await fs.mkdir(staging,{recursive:true});
const candidate=path.join(staging,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const output=path.join(workspaceDir,'presentation-output',name);await fs.mkdir(path.dirname(output),{recursive:true});
const count=story.slides.length,native=story.native_table_slides;
const result=await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath:output,pythonExecutable:runtimePython,
 integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...native.flatMap(i=>['--require-native-table-slide',String(i)])],
 explicitTotalSlideCount:count,requiredNativeTableOwnerSlides:native,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(staging,name+'.validation.json')});
const final=await PresentationFile.importPptx(await FileBlob.load(output));const previews=path.join(staging,'rendered');await fs.mkdir(previews,{recursive:true});
for(let i=0;i<count;i++){const blob=await final.export({slide:final.slides.getItem(i),format:'png',scale:1});await fs.writeFile(path.join(previews,`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));}
await fs.writeFile(path.join(staging,'delivery.json'),JSON.stringify({final:output,readme_sha256:story.readme_sha256,font,slides:count,finalizer:result},null,2));
console.log(JSON.stringify({final:output,previews,font,slides:count}));
