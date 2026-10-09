import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const W='C:/Users/aluk/Documents/Codex/2026-09-21/have';
const root='C:/git/worktrees/geospatial-openusd-delivery/extras/usd/examples/usdGeospatialBuild';
const delivery=path.join(root,'delivery/revised-leans-20261008');
const output=path.join(W,'outputs/geospatial-revised-leans-20261008');
const build=path.join(W,'work/geospatial-revised-leans-deck-20261008-v5');
const skill='C:/Users/aluk/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const python='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
await fs.mkdir(build,{recursive:true});
const story=JSON.parse(await fs.readFile(path.join(delivery,'story.json'),'utf8'));
const sha=b=>createHash('sha256').update(b).digest('hex');
if(sha(await fs.readFile(path.join(root,'README.md')))!==story.readme_sha256)throw Error('Stale README');
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#213744',teal:'#157C87',muted:'#536C7B',line:'#D7E1E6',amber:'#A25D20'};
function text(s,v,x,y,w,h,size=30,bold=false,color=C.ink){
 const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=v;o.text.style={typeface:'Arial',fontSize:size,bold,color,autoFit:'none',verticalAlignment:'top'};return o;
}
function table(s,rows,y,h,widths,size=26){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:64,top:y,width:1152,height:h,values:rows,columnWidths:widths});
 t.borders.assign({width:1,fill:C.line,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:rows.length,columnCount:rows[0].length}).assign({margins:{left:12,right:12,top:8,bottom:8}});
 for(let r=0;r<rows.length;r++){t.rows[r].height=h/rows.length;for(let c=0;c<rows[0].length;c++){let cell=t.getCell(r,c);cell.fill=r?'#FFFFFF':C.ink;cell.text.style={typeface:'Arial',fontSize:size,color:r?C.ink:'#FFFFFF',bold:!r,autoFit:'none'};}}
 return t;
}
async function image(s,name,x,y,w,h){s.images.add({blob:new Uint8Array(await fs.readFile(path.join(delivery,name))),contentType:'image/png',alt:name,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
for(let i=0;i<story.slides.length;i++){
 const m=story.slides[i],s=p.slides.add();s.background.fill='#FFFFFF';text(s,m.title,64,35,1152,96,44,true);
 if(i===0){
  text(s,'USD holds a model\'s shape. A coordinate reference system (CRS) explains a position on Earth.',64,157,1152,125,36);
  text(s,'The revised draft spells out instance movement, ordinary USD bake reuse and dependency coverage.',64,312,1152,147,36,true,C.teal);
  text(s,'Fresh evidence supports the reviewed rules. Three prototype limits remain visible. These local leans still need group review.',64,495,1152,162,31);
 }else if(m.image){
  text(s,m.paragraphs[0],64,143,1152,102,30);await image(s,m.image,64,263,840,394);
  text(s,m.paragraphs[1],943,271,273,347,28,false,C.teal);
 }else if(m.images){
  text(s,m.paragraphs[0],64,144,1152,78,30);
  await image(s,m.images[0],64,238,552,348);await image(s,m.images[1],664,238,552,348);
  text(s,'Eiffel model',64,590,552,35,23,true);text(s,'Terrain',664,590,552,35,23,true);
  text(s,m.paragraphs[1],64,639,1152,65,25,false,C.muted);
 }else if(m.chart){
  text(s,m.paragraphs[0],64,145,1152,76,30);
  const chart=s.charts.add('bar',{position:{left:45,top:249,width:836,height:427},categories:['Surface','Physical 3D'],series:[{name:'Separation',values:[+story.surface_km.toFixed(6),+story.physical_km.toFixed(6)],fill:C.teal}],barOptions:{direction:'column',grouping:'clustered',gapWidth:140},hasLegend:false,xAxis:{textStyle:{typeface:'Arial',fontSize:27,fill:C.ink},line:{fill:C.line,width:1}},yAxis:{min:0,max:130,majorUnit:20,title:{text:'Distance (km)',textStyle:{typeface:'Arial',fontSize:24,fill:C.ink}},textStyle:{typeface:'Arial',fontSize:24,fill:C.muted},numberFormatCode:'0',majorGridlines:{fill:'#E9EEF1',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.000',textStyle:{typeface:'Arial',fontSize:27,bold:true,fill:C.ink}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
  applyPresentationChartFont(chart,{fontFamily:'Arial'});text(s,m.paragraphs[1],923,280,293,340,30,false,C.teal);
 }else if(m.examples){
  let y=158;for(const e of story.examples){text(s,e.label+' ('+e.unit+')',64,y,1152,48,28,true,C.teal);
   table(s,[['Component','Python','C++'],...['East','North','Height'].map((v,k)=>[v,...['python','cpp'].map(n=>e[n][k].toLocaleString('en-US',{minimumFractionDigits:6,maximumFractionDigits:6}))])],y+55,148,[280,436,436],25);y+=234;}
  text(s,m.paragraphs[0],64,639,1152,68,25,false,C.muted);
 }else if(m.table){
  table(s,m.table,157,i===11?342:392,m.table[0].length===3?[332,410,410]:[395,757],27);
  text(s,m.paragraphs[0],64,i===11?533:588,1152,i===11?148:112,29,false,(i===10?C.amber:C.teal));
 }
 s.speakerNotes.textFrame.setText(JSON.stringify(m,null,2)+'\nDerived from README SHA-256 '+story.readme_sha256+'\nProposal '+story.proposal_revision+' SHA-256 '+story.proposal_sha256+'\nImmutable execution receipt SHA-256 '+story.receipt_sha256+'\nSource: local full proposal, receipt, analytical controls and independent audits linked from the README.\nNo group approval or exhaustive conformance claimed.\nUSD semantics: https://openusd.org/release/api/class_usd_geom_point_instancer.html and https://openusd.org/release/api/class_usd_geom_xformable.html\nAsset structuring guidance: https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html\nProfiles carrier: https://openusd.org/release/user_guides/schemas/UsdProfiles/overview.html\nEiffel mesh credit (slide 8): SDC PERFORMANCE, https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674 , CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ .\nChart workbook records distances rounded to six decimal places in km; labels show three. Full-precision analytical values remain in story.json. Analytical metric control uses WGS 84 equatorial radius 6378137 m and explicit 400000 m height. Plots show recorded synthetic data, not surveys or photographs.');
}
const draft=path.join(build,'draft.pptx');await(await PresentationFile.exportPptx(p)).save(draft);

const final=path.join(output,'Geospatial-revised-leans-assessment-2026-10-08-v3.pptx');
const result=await finalizePresentation({workspaceDir:W,candidatePath:draft,finalPath:final,pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[3,4,6,7,10,11,12].flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[3,4,6,7,10,11,12],requiredNativeChartOwnerSlides:[5],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
console.log(JSON.stringify({final,status:result.status,readme_sha256:story.readme_sha256}));
