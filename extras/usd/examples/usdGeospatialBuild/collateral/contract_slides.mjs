import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {Presentation,PresentationFile} from '@oai/artifact-tool';

const root=path.resolve(process.argv[2]||path.join(path.dirname(fileURLToPath(import.meta.url)),'..'));
const workspace=path.resolve(process.argv[3]||process.cwd());
const output=path.resolve(process.argv[4]||path.join(workspace,'outputs/geospatial-human-delivery-20261006'));
const build=path.join(workspace,'work/geospatial-human-delivery-render-20261006');
const skill='C:/Users/aluk/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const python='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
await fs.mkdir(build,{recursive:true});await fs.mkdir(output,{recursive:true});
const sha=b=>createHash('sha256').update(b).digest('hex');
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
if(story.readme_sha256!==sha(await fs.readFile(path.join(root,'README.md'))))throw Error('Stale README story');
if(story.narrative_version!==1||story.slides.length!==14)throw Error('Reassess narrative structure');
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#213744',teal:'#157C87',muted:'#526B79',light:'#D7E1E6',amber:'#A25D20'};
const slides=Array.from({length:14},()=>p.slides.add());
function text(s,value,x,y,w,h,size=28,bold=false,color=C.ink){
 const shape=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'#FFFFFF',line:{fill:'#FFFFFF',width:0}});
 shape.text=value;shape.text.style={typeface:'Arial',fontSize:size,bold,color,autoFit:'none',verticalAlignment:'top'};return shape;
}
function slide(n){const s=slides[n-1];s.background.fill='#FFFFFF';text(s,story.slides[n-1].title,64,34,1152,104,42,true);return s;}
function table(s,rows,y,h,widths,size=25){
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:64,top:y,width:1152,height:h,values:rows,columnWidths:widths});
 t.borders.assign({width:1,fill:C.light,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:rows.length,columnCount:rows[0].length}).assign({margins:{left:10,right:10,top:2,bottom:2}});
 for(let r=0;r<rows.length;r++){t.rows[r].height=h/rows.length;for(let c=0;c<rows[0].length;c++){const cell=t.getCell(r,c);cell.fill=r?'#FFFFFF':C.ink;cell.text.style={typeface:'Arial',fontSize:size,color:r?C.ink:'#FFFFFF',bold:!r,autoFit:'none'};}}return t;
}
async function image(s,case_,x,y,w,h){const asset=case_.image;const im=s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'delivery',asset.path))),contentType:'image/png',alt:asset.alt,fit:case_.kind==='illustration'?'cover':'contain',position:{left:x,top:y,width:w,height:h}});if(case_.kind==='illustration')im.crop={left:0,top:140/1560,right:0,bottom:520/1560};}
function notes(s,n,extra=''){
 const meta=story.slides[n-1],case_=story.cases.find(c=>c.id===meta.case);
 const assessment=case_?['Question: '+case_.question,'Proposed rule: '+case_.rule,'Expected: '+case_.expected,'Observed: '+case_.observed,'Implication for proposal quality: '+case_.implication,'Limit: '+case_.boundary,'Proposal: '+case_.clause_heading+' at proposal/proposal-source.txt:'+case_.clause_line,'Functional requirements: '+JSON.stringify(case_.requirements),'Image role: '+(case_.image?.role||'Recorded numerical evidence')].join('\n'):JSON.stringify({section:meta.section,status:story.status_rows,issues:n===8?story.issue_rows:undefined});
 s.speakerNotes.textFrame.setText(assessment+'\n'+extra+'\nREADME SHA-256 '+story.readme_sha256+'\nProposal SHA-256 '+story.proposal_sha256+'\nImmutable execution receipt SHA-256 '+story.immutable_receipt_sha256+'\nLater audit SHA-256 '+story.audit_sha256+'\n'+story.provenance_disposition+'\nEiffel mesh credit: SDC PERFORMANCE, https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674 ; CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ . Illustrative context is not surveyed ground truth.');
}
{
 const s=slide(1);text(s,story.opening,64,153,1152,163,31);text(s,story.assessment,64,347,1152,181,31,false,C.teal);text(s,story.summary,64,575,1152,127,27,false,C.muted);notes(s,1,'Main explanation: 1–8. Supporting evidence and review choices: 9–14.');
}
{
 const s=slide(2),c=story.cases.find(c=>c.id==='inputs');text(s,c.question,64,150,1152,79,31);table(s,[['Source information','Plain meaning'],...story.input_rows],254,333,[330,822],25);text(s,c.expected,64,622,1152,84,27,false,C.teal);notes(s,2);
}
for(const n of [3,4,6,9,10]){
 const s=slide(n),c=story.cases.find(c=>c.id===story.slides[n-1].case);text(s,c.question,64,147,1152,81,31,true,C.teal);
 await image(s,c,64,250,762,429);
 text(s,'Observed',865,250,351,32,22,true,C.teal);text(s,c.observed,865,287,351,168,24);
 text(s,'What it establishes',865,465,351,33,22,true,C.teal);text(s,c.implication,865,503,351,189,24);
 text(s,c.image.role[0].toUpperCase()+c.image.role.slice(1)+'. Limits in the notes and README.',64,686,762,25,18,false,C.muted);notes(s,n);
}
// Reader tables come directly from the recorded evidence also displayed in the README.
{
 const s=slide(5),c=story.cases.find(c=>c.id==='readers');text(s,c.question,64,146,1152,80,31);let y=242;
 for(const [key,label] of [['France_01','France: CC49 to Lambert-93, metres'],['Colorado_02','Colorado: State Plane to site grid, US survey feet']]){const e=story.examples[key];text(s,label,64,y,1152,37,25,true,C.teal);table(s,[['Resolved component','Python reader','C++ reader'],...['Map east coordinate','Map north coordinate','Height'].map((label,k)=>[label,...['python','native'].map(reader=>e[reader][k].toLocaleString('en-US',{minimumFractionDigits:6,maximumFractionDigits:6}))])],y+45,142,[352,400,400],24);y+=203;}
 text(s,c.boundary.split('. ')[0]+'.',64,654,1152,58,23,false,C.muted);notes(s,5,'The tables round one point per dataset to six decimals in their declared units. Shared PROJ and decoding limit independence. Required component/angular reports remain incomplete (audit A6). '+JSON.stringify(story.examples));
}
{
 const s=slide(7),c=story.cases.find(c=>c.id==='measurements');text(s,c.question,64,145,1152,95,30);await image(s,c,64,249,1152,332);text(s,c.observed,64,594,1152,63,25,false,C.teal);text(s,c.boundary,64,663,1152,48,21,false,C.muted);notes(s,7);
}
{
 const s=slide(8);text(s,'The recorded suite passed, then the audit exercised cases it had missed.',64,145,1152,68,30);table(s,[['Affected behavior','Confirmed issue'],...story.issue_rows],229,370,[330,822],22);text(s,'Repair these against the existing proposed rules. If repair reveals truly unspecified meaning, flag that separately.',64,654,1152,57,24,false,C.amber);notes(s,8,'No additional model blocker was established by this audit; this is not an exhaustive finding. R1 remains unreproduced.');
}
{
 const s=slide(11),c=story.cases.find(c=>c.id==='animation');text(s,c.rule,64,148,1152,81,30,true,C.teal);
 const chart=s.charts.add('bar',{position:{left:45,top:265,width:756,height:408},categories:['0','5','10'],series:[{name:'Error from interpolating converted endpoints',values:[0,+story.chord_error_metres.toFixed(6),0],fill:C.amber}],barOptions:{direction:'column',grouping:'clustered',gapWidth:130},hasLegend:false,xAxis:{title:{text:'USD sample time code',textStyle:{typeface:'Arial',fontSize:21,fill:C.ink}},textStyle:{typeface:'Arial',fontSize:23,fill:C.ink},line:{fill:C.light,width:1}},yAxis:{title:{text:'Distance from source-first result (m)',textStyle:{typeface:'Arial',fontSize:21,fill:C.ink}},numberFormatCode:'0',textStyle:{typeface:'Arial',fontSize:20,fill:C.muted},majorGridlines:{fill:'#E9EEF1',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0',textStyle:{typeface:'Arial',fontSize:25,fill:C.ink,bold:true}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});applyPresentationChartFont(chart,{fontFamily:'Arial'});
 text(s,'Why the order matters',850,271,366,55,30,true);text(s,c.implication,850,343,366,196,27);text(s,c.boundary,850,561,366,137,24,false,C.muted);notes(s,11,'The chart uses literal values from frozen source samples '+JSON.stringify(story.source_time_coordinates)+'; midpoint difference '+story.chord_error_metres+' m. Whole-metre chart labels; six-decimal workbook values. No continuous error curve is claimed.');
}
for(const n of [12,13]){
 const s=slide(n),rows=n===12?story.placement_choice_rows:story.data_choice_rows;table(s,[['Topic','Proposed meaning to review'],...rows],154,447,[355,797],25);
 text(s,n===12?'These are definitions in the candidate, not new inferred behavior supplied by the demonstrations.':'Coordinate epochs and scene-authored operation/resource controls remain deferred without foreclosing later support.',64,637,1152,70,26,false,C.amber);notes(s,n,JSON.stringify(rows));
}
{
 const s=slide(14);table(s,[['Path or check','Recorded evidence'],...story.evidence_rows],151,459,[340,812],23);text(s,'There are two placement readers. Omniverse reuses Python with a verified stage geometry sink. Hydra consumes a C++-resolved ordinary USD bake.',64,637,1152,75,25,false,C.muted);notes(s,14,JSON.stringify(story.evidence_rows));
}
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
execFileSync(python,[path.join(path.dirname(fileURLToPath(import.meta.url)),'repair_slide_viewports.py'),candidate],{stdio:'inherit'});
const final=path.join(output,'Geospatial-proposal-assessment-2026-10-06-v2.pptx');
const reference=path.join(root,'delivery/geospatial-build.pptx');
const result=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath:final,pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...story.required_native_table_slides.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:14,requiredNativeTableOwnerSlides:story.required_native_table_slides,requiredNativeChartOwnerSlides:story.required_native_chart_slides,materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'reference',families:['Arial'],referencePath:reference,referenceSha256:sha(await fs.readFile(reference))},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-v2.json')});
console.log(JSON.stringify({final,status:result.status,readme_sha256:story.readme_sha256}));
