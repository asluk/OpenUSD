// Editable deck derived only from the canonical README's extracted story.
// Usage: node slides.mjs <skill-dir> <runtime-python> <workspace-dir> <output-name>
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [skillDir,runtimePython,workspaceDir,name='geospatial-build-v1.pptx']=process.argv.slice(2);
if(!skillDir||!runtimePython||!workspaceDir)throw Error('Supply skill, Python and workspace locations');
const {finalizePresentation,resolvePresentationFont}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
const readme=await fs.readFile(path.join(root,'README.md'));
if(createHash('sha256').update(readme).digest('hex')!==story.readme_sha256)throw Error('README changed; derive again');
const font=resolvePresentationFont();
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#163641',teal:'#117E89',muted:'#526D76',paper:'#F5F8F9',white:'#FFFFFF',light:'#E4EFF1',amber:'#AC6A18',lime:'#CAE7CD'};
const clean=t=>String(t).replace(/\[([^\]]+)\]\([^)]+\)/g,'$1').replace(/[`*]/g,'');
function text(s,value,x,y,w,h,size=25,color=C.ink,bold=false){
 const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=clean(value);o.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none',verticalAlignment:'middle'};return o;
}
function box(s,x,y,w,h,fill=C.white){return s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:'none',width:0}});}
async function img(s,n,x,y,w,h){s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'delivery',n))),contentType:'image/png',alt:n,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function footer(s,n){text(s,'EXPERIMENTAL CANDIDATE • OCTOBER 2 BUILD',52,680,1000,21,13,C.muted);text(s,String(n).padStart(2,'0'),1180,680,45,22,14,C.muted);}
function title(s,t){text(s,t,52,46,1180,80,39,C.ink,true);box(s,52,134,56,5,C.teal);}
function paragraphs(content){return content.split('\n\n').filter(x=>!x.startsWith('![')&&!x.startsWith('|'));}
function tables(content){const lines=content.split('\n');const groups=[];let cur=[];for(const l of lines){if(l.startsWith('|'))cur.push(l);else if(cur.length){groups.push(cur);cur=[];}}if(cur.length)groups.push(cur);return groups.map(g=>g.filter(l=>!/^\|[\s:\-|]+\|$/.test(l)).map(l=>l.split('|').slice(1,-1).map(x=>clean(x.trim()))));}
function table(s,values,x,y,w,h,widths,size=19){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.borders.assign({style:'solid',fill:C.white,width:1});
 for(let i=0;i<values.length;i++)for(let j=0;j<values[0].length;j++){
  const c=t.getCell(i,j);c.fill=i===0?C.ink:(i%2?C.white:C.light);
  c.text.style={typeface:font,fontSize:size,color:i===0?C.white:C.ink,bold:i===0,autoFit:'none'};
 }
 return t;
}
for(let index=0;index<story.slides.length;index++){
 const d=story.slides[index],s=p.slides.add();s.background.fill=C.paper;footer(s,index+1);
 const paras=paragraphs(d.content),ts=tables(d.content);
 if(d.kind==='hero'){
  box(s,0,0,720,720,C.white);await img(s,d.images[0],0,170,720,450);
  text(s,'GEOSPATIAL IN USD + OV',54,52,640,25,18,C.teal,true);
  text(s,'Geospatial meaning\nthat survives\nUSD composition',54,93,650,156,43,C.ink,true);
  box(s,750,52,478,595,C.light);await img(s,d.images[1],765,73,448,308);
  text(s,d.summary,786,388,414,137,22,C.ink);
  text(s,'Native Hydra render + named coordinate query.\nIllustrative controls; no survey accuracy claim.',786,543,414,75,17,C.muted);
 }else{
  title(s,d.title);
  if(d.kind==='problem'){
   text(s,d.summary,52,164,1150,84,25);
   const sentence=paras[1];const ordinary=sentence.match(/reader returns `([^`]+)`/)[1],resolved=sentence.match(/geospatial reader returns `([^`]+)`/)[1];
   box(s,52,278,358,282,C.white);box(s,460,278,358,282,C.light);box(s,868,278,360,282,C.ink);
   text(s,'LOCAL USD',75,297,312,35,18,C.teal,true);text(s,'Point (3,4,5)\nChild translate (1,0,0)\nModel translate (7,8,9)',75,352,312,141,24);
   text(s,'ORDINARY READER',485,297,310,35,18,C.teal,true);text(s,ordinary,485,366,310,65,35,C.ink,true);text(s,'Ordinary transforms retain\ntheir ordinary interpretation.',485,459,305,79,21,C.muted);
   text(s,'CRS-AWARE READER',891,297,312,35,18,'#85D7DB',true);text(s,resolved,891,364,312,66,34,C.white,true);text(s,'Explicit position + orientation\n+ scale; ordinary transforms after.',891,451,312,88,21,C.white);
   text(s,'A hand-worked noncommuting control catches an origin-only or wrong-order implementation.',52,587,1150,56,22,C.muted);
  }else if(d.kind==='model'){
   text(s,d.summary,52,159,1150,76,24);
   const cards=[['COMPLETE WKT','Definition + component units\nDatum, height and site calibration'],['BINDING','Source association\nIndependent assets retain meaning'],['CRS PLACEMENT','Position + orientation + scale\nLocal geometry stays USD lengths'],['ORDINARY USD','Post-placement adjustments\nWriter conformance stays separate']];
   for(let j=0;j<4;j++){const x=52+j*298;box(s,x,280,280,237,j===3?C.ink:C.white);text(s,String(j+1).padStart(2,'0'),x+22,301,235,35,21,j===3?'#85D7DB':C.teal,true);text(s,cards[j][0],x+22,352,236,37,23,j===3?C.white:C.ink,true);text(s,cards[j][1],x+22,408,236,93,20,j===3?C.white:C.muted);}
   text(s,'Author meaning once. Derive results without altering source layers.',52,559,1150,56,29,C.ink,true);
   text(s,'Exact experimental fields and adjustment context are frozen before code and remain reviewable choices.',52,611,1150,37,19,C.muted);
  }else if(d.kind==='partner'){
   text(s,d.summary,52,157,1150,85,23);
   await img(s,d.images[0],52,261,570,322);await img(s,d.images[1],656,255,570,315);
   text(s,'Native Hydra / original LandXML',64,588,552,31,20,C.teal,true);
   text(s,'Headless query / calibrated site axes',667,588,550,31,20,C.teal,true);
   text(s,'5 Colorado + 59 France controls • Required height grids verified • CSVs use the same PROJ family',52,629,1176,33,18,C.muted);
  }else if(d.kind==='comparison'){
   text(s,d.summary,52,155,1165,84,24);
   const rows=ts[0].map((r,i)=>i===0?['Dataset','Jobs','Native max (mm)','OV max (mm)']:[r[0],r[1],r[3],r[4]]);
   table(s,rows,52,266,1176,343,[536,105,278,257],20);
   text(s,'Actual Hydra matrices / instancers + live OV result readback. Shared PROJ: numerical agreement ≠ independent geodetic accuracy.',52,625,1170,40,18,C.muted);
  }else if(d.kind==='city'){
   text(s,d.summary,52,156,1160,81,23);
   box(s,52,256,942,383,C.white);await img(s,d.images[0],60,265,925,367);
   box(s,1016,256,212,383,C.light);text(s,'1,850',1037,290,170,55,41,C.ink,true);text(s,'selected locations',1037,350,170,54,23,C.teal,true);
   text(s,'Coordinates\nValues\nSource indices\nRecorded times',1037,426,170,155,22);
   text(s,'Synthetic red/NIR and assumed 80 m ellipsoidal height. GeoJSON + paired analysis product accompany the run.',52,641,1170,29,17,C.muted);
  }else if(d.kind==='global'){
   text(s,d.summary,52,155,1165,84,24);
   await img(s,d.images[0],52,253,577,357);await img(s,d.images[1],656,253,572,365);
   text(s,'Scientific query visualizations • Original scalar values / units absent in source • Second time explicitly synthetic',52,624,1170,45,18,C.muted);
  }else if(d.kind==='consumption'){
   text(s,d.summary,52,158,1160,78,24);
   box(s,52,265,630,355,C.white);await img(s,d.images[0],59,278,616,333);
   box(s,710,265,518,355,C.light);
   text(s,'Source edit → consumed placement',736,291,465,39,25,C.ink,true);
   text(s,'Native source notices recompute\nrendered placement; +10 m edit verified.',736,346,465,69,22);
   text(s,'Failure → stale results removed → recovery',736,431,465,61,24,C.ink,true);
   text(s,'Live OV hides invalid model results, clears\nmeasurement results, then recovers.',736,503,465,78,22);
   text(s,'Five explicit exports re-resolved by a fresh reader. Values and recorded times preserved; no private skip flag.',52,629,1168,40,18,C.muted);
  }else if(d.kind==='precision'){
   text(s,d.summary,52,156,1160,91,24);
   const rows=ts[0];const selected=rows.filter((r,i)=>i&&['±100 m','±1,000 m','±10,000 m'].includes(r[0])).map(r=>{const m=parseFloat(r[2]);return [r[0],r[1],m<.01?(m*1000).toFixed(2)+' mm':m.toPrecision(3)+' m'];});table(s,[['Half-extent','Points','Affine discrepancy'],...selected],52,283,688,219,[266,103,319],22);
   box(s,770,283,458,296,C.ink);text(s,'SAMPLED DISCREPANCY',798,310,402,34,18,'#85D7DB',true);text(s,'Finite samples do not\nestablish a continuous\nsurface error bound.',798,363,402,149,30,C.white,true);
   text(s,'Double anchor + small local floats avoids 31.25 mm float spacing at a 481,948 m absolute coordinate.',52,544,685,91,23,C.muted);
   text(s,'R24 needs an extent / approximation contract. This is a design finding, not a deferred demonstration.',52,639,1170,29,18,C.muted);
  }else if(d.kind==='decisions'){
   text(s,d.summary,52,158,1160,105,23);
   box(s,52,295,559,323,C.white);box(s,640,295,588,323,C.light);
   text(s,'REVIEW THE EXPERIMENTAL CONTRACTS',77,317,510,38,20,C.teal,true);
   text(s,'Exact placement fields and axis conventions\nProject adjustment context\nWKT string normalization\nMeasurement association\nDependency and sampled-export records',77,381,510,201,23);
   text(s,'PRESERVE THE ROADMAP',665,317,539,38,20,C.teal,true);
   text(s,'Coordinate epochs fully deferred.\nCRS frame epochs retained in WKT.\nSupported datum / height operations exercised.\nCity and global data remain in scope.\nContinuous extent / error bound stays open.',665,381,539,201,23);
   text(s,'Requirements → frozen model + runtime → independent consumers → audit → evidence → delivery',52,640,1170,29,18,C.muted);
  }
 }
 s.speakerNotes.textFrame.setText(`Canonical source: README.md, section "${d.section}". README SHA-256: ${story.readme_sha256}\n${d.content}\nFigures are executed evidence; synthetic and conditional source assumptions remain labeled. Candidate contracts are experimental.`);
}
const staging=path.join(workspaceDir,'.codex-finalizer');await fs.mkdir(staging,{recursive:true});
const candidate=path.join(staging,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const output=path.join(workspaceDir,'presentation-output',name);await fs.mkdir(path.dirname(output),{recursive:true});
const result=await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath:output,pythonExecutable:runtimePython,
 integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','5','--require-native-table-slide','9'],
 explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[5,9],fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(staging,name+'.validation.json')});
const final=await PresentationFile.importPptx(await FileBlob.load(output));
const previews=path.join(staging,'rendered');await fs.mkdir(previews,{recursive:true});
for(let i=0;i<10;i++){
 const s=final.slides.getItem(i);const blob=await final.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(previews,`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));
}
await fs.writeFile(path.join(staging,'delivery.json'),JSON.stringify({final:output,readme_sha256:story.readme_sha256,font,slides:10,finalizer:result},null,2));
console.log(JSON.stringify({final:output,previews,font,slides:10}));
