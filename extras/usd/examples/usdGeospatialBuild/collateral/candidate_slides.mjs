// Editable presentation derives its evidence and prose from the receipt-bound README story.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [skill,runtimePython,workspaceDir,outputName='geospatial-build-v3.pptx']=process.argv.slice(2);
const staging=path.join(workspaceDir,'work/geospatial-candidate-loop-slides-20261004');
const finalPath=path.join(workspaceDir,'outputs/geospatial-candidate-loop-20261004',outputName);
await fs.mkdir(staging,{recursive:true});await fs.mkdir(path.dirname(finalPath),{recursive:true});
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
if(createHash('sha256').update(await fs.readFile(path.join(root,'README.md'))).digest('hex')!==story.readme_sha256)throw Error('README changed; derive again');
const {resolvePresentationFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({fontFamily:'Arial'});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const clean=s=>s.replace(/\*\*|`/g,'');
function text(s,value,top,height,size=28,bold=false,color='#233542'){
 const sh=s.shapes.add({geometry:'textbox',position:{left:64,top,width:1152,height},fill:'none',line:{fill:'none',width:0}});
 sh.text=clean(value);sh.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};
}
function table(s,values,top,height,widths,size=24){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top,width:1152,height,values,columnWidths:widths});
 t.borders.assign({width:1,fill:'#D6DEE3',style:'solid'});
 for(let r=0;r<values.length;r++){
  t.rows[r].height=height/values.length;
  for(let c=0;c<values[0].length;c++){
   const cell=t.getCell(r,c);cell.fill=r?'#FFFFFF':'#233542';
   cell.text.style={typeface:font,fontSize:size,color:r?'#233542':'#FFFFFF',bold:!r,autoFit:'none'};
  }
 }
}
const titles=['Geospatial proposal readiness','Concrete candidate answers','Four contracts still required','WKT string normalization',
              'Executed reader coverage','Same France origin in each runtime','Source interpolation and export samples','Postimplementation audit'];
for(let i=0;i<story.slides.length;i++){
 const d=story.slides[i],s=p.slides.add();s.background.fill='#FFFFFF';text(s,titles[i],40,100,42,true);
 if(i===0){
  text(s,d.paragraphs[0],176,168,38,true);
  text(s,d.paragraphs[1],380,116,31,false,'#117E89');
  text(s,d.paragraphs[2],550,104,28);
 }else if(i===1){
  table(s,d.values,150,500,[278,874],23);
 }else if(i===2){
  table(s,d.values,150,468,[345,807],24);
  text(s,d.paragraphs[0].split(' The candidate')[0],644,54,22);
 }else if(i===3){
  text(s,d.paragraphs[0].match(/The (\d+) WKT tests/)[1]+' tests check lexical identity while preserving represented information.',154,68,28);
  table(s,[['WKT fragment','Before','Normalized'],
           ['Numeric spelling','LENGTHUNIT["metre",1E0]','LENGTHUNIT["metre",1.0]'],
           ['Exact decimal','6378137.12345678912345','6378137.12345678912345'],
           ['Quoted content','REMARK["Keep  spaces"]','REMARK["Keep  spaces"]']],252,280,[235,458,459],23);
  text(s,'Different display names retain different tokens. CRS equivalence requires a separate engine comparison.',565,70,27);
  text(s,'Illustrative fragments from the tested lexical rules. Context-sensitive legacy UNIT aliases are unsupported.',658,42,20);
 }else if(i===4){
  table(s,d.values,160,280,[495,219,219,219],25);
  text(s,'Every reader checks the same authored scenes. Direct origins include France projections, Colorado site calibration and analytic ECEF conversions.',483,92,27);
  text(s,'Expected failures include unsupported frame requests. Source data stays unchanged. PROJ is shared across readers.',609,67,23);
 }else if(i===5){
  text(s,d.paragraphs[0],152,134,27);
  table(s,d.values,327,216,[182,245,245,240,240],25);
  text(s,'All 59 France origins pass in both directions. Coordinates only, with no geometry or measurement-domain claim.',590,80,26);
 }else if(i===6){
  text(s,d.paragraphs[0],154,128,27);
  table(s,d.values,313,205,[230,480,442],26);
  text(s,'Interpolating only the converted endpoints misses the midpoint by '+d.paragraphs[1].match(/\*\*([0-9.]+) m\*\*/)[1]+' m.',549,75,29,true,'#117E89');
  text(s,'Fresh USD sampling record: keys 0, 5, 10 and explicit timeCodesPerSecond 48. This is not a resolved-scene export.',644,53,22);
 }else{
  text(s,d.paragraphs[0],162,242,29);
  text(s,d.paragraphs[1],447,222,27);
 }
 s.speakerNotes.textFrame.setText(`README section: ${d.readme_section}\nREADME SHA-256: ${story.readme_sha256}\nExecution receipt SHA-256: ${story.run_receipt_sha256}\nExecuted source: ${story.executed_source_commit}\n\n${d.paragraphs.join('\n\n')}\n\nCandidate choices are under review. Partial controls do not certify full placement or geodetic accuracy.`);
}
const candidatePath=path.join(staging,'candidate-'+outputName);await(await PresentationFile.exportPptx(p)).save(candidatePath);
const owners=[2,3,4,5,6,7];
const result=await finalizePresentation({workspaceDir,candidatePath,finalPath,pythonExecutable:runtimePython,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:8,requiredNativeTableOwnerSlides:owners,requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(staging,outputName+'.validation.json')});
console.log(JSON.stringify({finalPath,validation:result.status}));
