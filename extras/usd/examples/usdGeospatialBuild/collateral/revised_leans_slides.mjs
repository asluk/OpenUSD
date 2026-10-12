import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile} from '@oai/artifact-tool';

const W='C:/Users/aluk/Documents/Codex/2026-09-21/have';
const root='C:/git/worktrees/geospatial-openusd-delivery/extras/usd/examples/usdGeospatialBuild';
const output=path.join(W,'outputs/geospatial-feedback-build-20261012');
const build=path.join(W,'work/geospatial-feedback-assessment-20261012-v1');
const skill='C:/Users/aluk/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const python='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const reference=path.join(W,'outputs/geospatial-human-delivery-20261006/Geospatial-proposal-assessment-2026-10-06-v2.pptx');
process.env.RUNTIME_NODE_MODULES='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
await fs.mkdir(build,{recursive:true});await fs.mkdir(output,{recursive:true});
const sha=b=>createHash('sha256').update(b).digest('hex');
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
const readme=await fs.readFile(path.join(root,'README.md'),'utf8');
if(story.readme_sha256!==sha(Buffer.from(readme))||story.narrative_version!==2||story.slides.length!==14)throw Error('Stale or incompatible standalone narrative');
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#213744',teal:'#157C87',muted:'#526B79',light:'#D7E1E6',amber:'#A25D20'};
const slides=Array.from({length:14},()=>p.slides.add());
const evidence=[];
function text(s,value,x,y,w,h,size=28,bold=false,color=C.ink){
 // Every slide sentence is part of the source README. Labels alone are layout.
 const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:'Arial',fontSize:size,bold,color,autoFit:'none',verticalAlignment:'top'};
 evidence.push({slide:slides.indexOf(s)+1,text:value});return o;
}
function slide(n){const s=slides[n-1];s.background.fill='#FFFFFF';text(s,story.slides[n-1].title,64,34,1152,104,42,true);return s;}
function table(s,rows,y,h,widths,size=25){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:64,top:y,width:1152,height:h,values:rows,columnWidths:widths});
 t.borders.assign({width:1,fill:C.light,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:rows.length,columnCount:rows[0].length}).assign({margins:{left:10,right:10,top:4,bottom:4}});
 for(let r=0;r<rows.length;r++){t.rows[r].height=h/rows.length;for(let c=0;c<rows[0].length;c++){let cell=t.getCell(r,c);cell.fill=r?'#FFFFFF':C.ink;cell.text.style={typeface:'Arial',fontSize:size,color:r?C.ink:'#FFFFFF',bold:!r,autoFit:'none'};}}
 evidence.push({slide:slides.indexOf(s)+1,table:rows});return t;
}
async function image(s,c,x,y,w,h){
 const a=c.image;const im=s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'delivery',a.path))),contentType:'image/png',alt:a.alt,fit:c.kind==='illustration'?'cover':'contain',position:{left:x,top:y,width:w,height:h}});
 if(c.kind==='illustration')im.crop={left:0,top:140/1560,right:0,bottom:520/1560};
}
function notes(s,n,extra=''){
 const meta=story.slides[n-1],c=story.cases.find(c=>c.id===meta.case);
 const words=c?['Question: '+c.question,'Proposed rule: '+c.rule,'Expected behavior: '+c.expected,'Observed result: '+c.observed,'What this says about the proposal: '+c.implication,'Limit: '+c.boundary,'Proposal clause: '+c.clause_heading+' at proposal/proposal-source.txt:'+c.clause_line,'Requirements: '+c.requirement_ids.join(', ')].join('\n'):JSON.stringify({assessment:story.status_rows,placement:story.placement_choice_rows,data:story.data_choice_rows});
 s.speakerNotes.textFrame.setText(words+'\n'+extra+'\nProposal '+story.proposal_revision+' SHA-256 '+story.proposal_sha256+'\nREADME SHA-256 '+story.readme_sha256+'\nImmutable receipt SHA-256 '+story.receipt_sha256+'\nEiffel mesh: SDC PERFORMANCE, https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674, CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ . Informative positions and ground context do not establish surveyed placement.\nAccepted source and declaration rules are distinguished from detailed conventions and identities awaiting review. Python and C++ share PROJ and decoding. Omniverse reuses Python. Hydra consumes a resolved ordinary USD bake.');
}
{
 const s=slide(1);text(s,story.opening,64,153,1152,163,31);text(s,story.assessment,64,347,1152,181,31,false,C.teal);text(s,story.summary,64,575,1152,127,27,false,C.muted);notes(s,1);
}
{
 const s=slide(2),c=story.cases.find(c=>c.id==='inputs');text(s,c.question,64,150,1152,79,31);table(s,[['Source information','Plain meaning'],...story.input_rows],254,333,[330,822],25);text(s,c.expected,64,622,1152,84,27,false,C.teal);notes(s,2);
}
for(const n of [3,4,6,9,10]){
 const s=slide(n),c=story.cases.find(c=>c.id===story.slides[n-1].case);text(s,c.question,64,147,1152,81,31,true,C.teal);await image(s,c,64,250,762,429);
 text(s,'Observed',865,250,351,32,22,true,C.teal);text(s,c.observed,865,287,351,168,24);
 text(s,'What it establishes',865,465,351,33,22,true,C.teal);text(s,c.implication,865,503,351,189,24);
 text(s,c.image.role[0].toUpperCase()+c.image.role.slice(1)+'. Limits in the notes and README.',64,686,762,25,18,false,C.muted);notes(s,n);
}
{
 const s=slide(5),c=story.cases.find(c=>c.id==='readers');text(s,c.question,64,146,1152,80,31);let y=242;
 for(const e of story.examples){text(s,e.label+(e.unit==='m'?', metres':', US survey feet'),64,y,1152,37,25,true,C.teal);table(s,[['Resolved component','Python reader','C++ reader'],...['Map east coordinate','Map north coordinate','Height'].map((v,k)=>[v,...['python','cpp'].map(n=>e[n][k].toLocaleString('en-US',{minimumFractionDigits:6,maximumFractionDigits:6}))])],y+45,142,[352,400,400],24);y+=203;}
 text(s,c.boundary.split('. ')[0]+'.',64,654,1152,58,23,false,C.muted);notes(s,5,'Tables show one recorded point per dataset in declared units, rounded to six decimals. '+JSON.stringify(story.examples));
}
{
 const s=slide(7),c=story.cases.find(c=>c.id==='measurements');text(s,c.question,64,145,1152,95,30);await image(s,c,64,249,1152,332);text(s,c.observed,64,594,1152,63,25,false,C.teal);text(s,c.boundary,64,663,1152,48,21,false,C.muted);notes(s,7);
}
{
 const s=slide(8);text(s,'Selected demonstrations support the proposed behavior.',64,145,1152,68,30);table(s,[['Review dimension','Assessment'],...story.status_rows],231,370,[330,822],24);
 text(s,'No additional undefined model rule was confirmed in the inspected paths. That is a bounded finding.',64,635,1152,77,26,false,C.amber);notes(s,8,JSON.stringify(story.limits));
}
{
 const s=slide(11),c=story.cases.find(c=>c.id==='animation');text(s,c.rule.split('. ')[0]+'.',64,148,1152,81,30,true,C.teal);
 text(s,c.observed,64,211,1152,51,23,false,C.muted);
 const chart=s.charts.add('bar',{position:{left:45,top:265,width:756,height:408},categories:['0','5','10'],series:[{name:'Error from interpolating converted endpoints',values:[0,+story.chord_error_metres.toFixed(6),0],fill:C.amber}],barOptions:{direction:'column',grouping:'clustered',gapWidth:130},hasLegend:false,xAxis:{title:{text:'USD sample time code',textStyle:{typeface:'Arial',fontSize:21,fill:C.ink}},textStyle:{typeface:'Arial',fontSize:23,fill:C.ink},line:{fill:C.light,width:1}},yAxis:{min:0,max:1200,majorUnit:200,title:{text:'Distance from source-first result (m)',textStyle:{typeface:'Arial',fontSize:21,fill:C.ink}},numberFormatCode:'0',textStyle:{typeface:'Arial',fontSize:20,fill:C.muted},majorGridlines:{fill:'#E9EEF1',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0',textStyle:{typeface:'Arial',fontSize:25,fill:C.ink,bold:true}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});applyPresentationChartFont(chart,{fontFamily:'Arial'});
 text(s,'Why the order matters',850,271,366,55,30,true);text(s,c.implication,850,343,366,196,27);text(s,c.boundary,850,561,366,137,24,false,C.muted);notes(s,11,'Chart uses the recorded t=0, 5, 10 coordinates. Six-decimal workbook snapshot values, whole-metre display labels. The bar is a negative control, not a measured failure of the source-first reader. '+c.observed);
}
for(const n of [12,13]){
 const s=slide(n),rows=n===12?story.placement_choice_rows:story.data_choice_rows;table(s,[['Topic','Proposed meaning to review'],...rows],154,447,[355,797],25);
 const sentence=n===12?'These are proposed definitions in the full draft.':'Coordinate epochs and scene-authored transformation-resource controls are deferred while preserving a path to future support.';
 text(s,sentence,64,637,1152,70,26,false,C.amber);notes(s,n,JSON.stringify(rows));
}
{
 const s=slide(14);table(s,[['Path or check','Recorded evidence'],...story.evidence_rows],151,459,[340,812],23);text(s,'There are two placement readers. Omniverse reuses Python with a verified stage geometry sink. Hydra consumes a C++-resolved ordinary USD bake.',64,637,1152,75,25,false,C.muted);notes(s,14,JSON.stringify(story.evidence_rows));
}
const draft=path.join(build,'draft.pptx');await(await PresentationFile.exportPptx(p)).save(draft);
const final=path.join(output,'Geospatial-proposal-assessment-2026-10-12-v1.pptx');
const tables=story.required_native_table_slides;
const result=await finalizePresentation({workspaceDir:W,candidatePath:draft,finalPath:final,pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:14,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:[11],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'reference',families:['Arial'],referencePath:reference,referenceSha256:sha(await fs.readFile(reference))},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
await fs.writeFile(path.join(build,'content-evidence.json'),JSON.stringify({readme_sha256:story.readme_sha256,proposal_sha256:story.proposal_sha256,slides:evidence},null,2));
console.log(JSON.stringify({final,status:result.status,slides:14}));
