// Current candidate evidence, derived from README and frozen consumer returns.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [skill,python,workspace,outputName='Geospatial-contract-evidence-2026-10-06.pptx']=process.argv.slice(2);
const tmp=path.join(workspace,'work/geospatial-contract-deck-20261006');
const final=path.join(workspace,'outputs/geospatial-contract-deck-20261006',outputName);
await fs.mkdir(tmp,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});
const sha=b=>createHash('sha256').update(b).digest('hex');
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
if(sha(await fs.readFile(path.join(root,'README.md')))!==story.readme_sha256)throw Error('Re-derive changed README');
if(sha(await fs.readFile(path.join(root,'delivery/run-report.json')))!==story.run_receipt_sha256)throw Error('Changed receipt');
const report=JSON.parse(await fs.readFile(path.join(root,'delivery/run-report.json'),'utf8'));
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({fontFamily:'Arial'}),p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#213744',teal:'#157C87',muted:'#526B79',light:'#D7E1E6',amber:'#A25D20',blue:'#2A6199'};
function text(s,t,x,y,w,h,size=28,bold=false,color=C.ink){const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});sh.text=t;sh.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return sh;}
function table(s,values,y,h,widths,size=24,x=64,w=1152){const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});t.borders.assign({width:1,fill:C.light,style:'solid'});for(let r=0;r<values.length;r++){t.rows[r].height=h/values.length;for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.fill=r?'#FFFFFF':C.ink;cell.text.style={typeface:font,fontSize:size,color:r?C.ink:'#FFFFFF',bold:!r,autoFit:'none'};}}return t;}
async function pic(s,file,x,y,w,h,alt){s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,'delivery',file))),contentType:'image/png',alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function axis(title,format='0'){return {title:{text:title,textStyle:{typeface:font,fontSize:19,fill:C.ink}},numberFormatCode:format,textStyle:{typeface:font,fontSize:18,fill:C.muted},line:{fill:C.light,width:1},majorGridlines:{fill:'#E9EEF1',width:1}};}
for(let i=0;i<story.slides.length;i++){
 const d=story.slides[i],s=p.slides.add();s.background.fill='#FFFFFF';text(s,d.title,64,35,1152,110,42,true);let notes='';
 if(i===0){
  text(s,'Known contract gaps now have concrete proposed answers.',64,173,1152,112,39,true);
  text(s,'Position and model attitude are source inputs. Detailed transform, dataset, instance and scene-chart choices still need author review.',64,323,1152,130,32,false,C.amber);
  text(s,`${story.tests.regressions_passed} regressions and ${story.tests.distinguishing_controls_passed} distinguishing controls passed.\n${story.coordinate_count.toLocaleString()} coordinate results per Python/C++ path.`,64,500,1152,107,32,false,C.teal);
  text(s,'No new computed source properties. Group adoption and whole-proposal conformance are not claimed.',64,652,1152,45,23,false,C.muted);
 }else if(i===1){
  table(s,[['Authored inputs','Meaning in the proposed model'],
   ['crs:position','Absolute 3D model origin in source WKT components, units and height reference.'],
   ['crs:orientation','Physical geodetic ENU model attitude; identity fallback. Distinct from projected grid convergence.'],
   ['Ordinary xformOps','Intentional scale, pivots and project adjustment. Descendant stacks retain model-local meaning.'],
   ['Native data association','Asset, format, field and coordinate domain. Values, masks and observation times remain native.'],
   ['Computed results','Resolution, convergence, projection scale and bounds are results; no crs:scale source property.']],150,450,[300,852],24);
  text(s,'This is a complete review candidate. Tests do not establish author agreement to the detailed choices.',64,641,1152,66,25,false,C.amber);
 }else if(i===2){
  text(s,'A geographic asset sits inside a projected site. Its model orientation turns local X northward.',64,158,1152,80,30);
  const q=story.working_queries;
  const rows=[['Queried position','Easting (m)','Northing (m)','Height (m)'],['Anchor with +10 site adjustment',...q[0].coordinates[0].map(v=>v.toFixed(4))],['Child with +3 local X',...q[1].coordinates[0].map(v=>v.toFixed(4))],['Child with ordinary reset',...q[2].coordinates[0].map(v=>v.toFixed(4))]];
  table(s,rows,269,237,[474,226,226,226],25);
  text(s,'The +10 follows site easting. The child offset follows the oriented model.\nThe reset removes the ordinary adjustment and retains CRS placement.',64,539,1152,104,29,false,C.teal);
  text(s,`The raw working-axis child alternative differs by ${story.comparison.difference_metres.toFixed(3)} m. Descendant semantics are proposed for review.`,64,662,1152,46,22,false,C.muted);
 }else if(i===3){
  await pic(s,'renders/tower.png',30,142,805,474,'Native Hydra Storm rendering of resolved Eiffel geometry');
  text(s,'163,440 vertices',865,184,350,63,36,true,C.teal);
  text(s,'C++ pointwise results\n163,416 shading normals\nFresh USD export readers\nNative Storm color output',865,277,350,219,27);
  text(s,'Illustrative plane and markers.\nNo surveyed Paris context.',865,533,350,79,24,false,C.muted);
  text(s,'The renderer consumes an ordinary resolved export. This run does not install a live geospatial scene-index filter.',64,653,1152,51,24,false,C.muted);
  notes='Eiffel mesh: ( FREE ) La tour Eiffel by SDC PERFORMANCE, https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674 ; CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ . Reoriented, placed and rendered with illustrative context. Actual native Storm output from this frozen run.';
 }else if(i===4){
  await pic(s,'renders/terrain.png',25,143,814,477,'Native Storm rendering of resolved Colorado survey breaklines');
  text(s,'14,359 vertices',866,181,349,63,36,true,C.teal);
  text(s,'Original LandXML breaklines\nWKT-carried site calibration\nDeclared US survey feet\nSeparate stage conventions',866,276,349,229,27);
  text(s,'No terrain surface\nwas fabricated.',866,544,349,78,25,false,C.muted);
  text(s,'Fresh readers verify the resolved geometry. Polygonal bounds cover returned vertices and straight faces, with no continuous-surface certificate.',64,651,1152,61,23,false,C.muted);
 }else if(i===5){
  await pic(s,'plots/global-3d.png',39,154,1200,369,'Synthetic CF global temperature domain with explicit ellipsoidal height');
  text(s,'154 synthetic 3D samples retain values and two observation times.',64,547,1152,47,30,true,C.teal);
  text(s,'Explicit 100 m ellipsoidal height; illustrative temperature in kelvin. Both readers resolve geographic and ECEF outputs. Observation time is distinct from epoch.',64,615,1152,87,28);
 }else if(i===6){
  await pic(s,'plots/railway.png',29,148,682,513,'Original railway horizontal coordinates resolved to UTM 32');
  text(s,'15,822 vertices',756,188,460,57,36,true,C.teal);
  text(s,'2,386 railway parts\nExplicit horizontal source copy\nUTM 32 output coordinates\nOriginal data retained',756,282,460,201,29);
  text(s,'Original third components\nremain uninterpreted.',756,535,460,95,27,false,C.amber);
  text(s,'The larger-scale workflows keep useful 2D resolution without inventing height. Plot offsets serve display only.',64,670,1152,35,22,false,C.muted);
 }else if(i===7){
  let y=156;
  for(const [key,label] of [['France_01','France: CC49 to Lambert-93 (metres)'],['Colorado_02','Colorado: State Plane to calibrated site (US survey feet)']]){
   const e=story.examples[key];text(s,label,64,y,1152,44,27,true,C.teal);
   const rows=[['Component','Source','USD Python','USD C++','OV-hosted Python'],...['Easting','Northing','Height'].map((l,k)=>[l,...['source','python','native','ov'].map(n=>e[n][k].toFixed(4))])];
   table(s,rows,y+53,164,[190,233,233,233,263],22);y+=244;
  }
  text(s,'Both USD implementations agree. OV reuses Python placement. All paths share PROJ; these comparisons do not certify survey accuracy.',64,655,1152,55,22,false,C.muted);
 }else if(i===8){
  const xyz=story.source_time_coordinates,base=(xyz[0][0]+xyz[2][0])/2;
  const curve=Array.from({length:61},(_,n)=>{const a=(2*n/60)*Math.PI/180;return [6378137*Math.sin(a)/1000,6378137*Math.cos(a)-base]});
  const chart=s.charts.add('scatter',{position:{left:45,top:163,width:752,height:431},title:'Source-first ECEF path',titleTextStyle:{typeface:font,fontSize:25,fill:C.ink,bold:true},series:[
   {name:'Analytic guide',xValues:curve.map(v=>+v[0].toFixed(6)),values:curve.map(v=>+v[1].toFixed(6)),line:{fill:C.teal,width:3},marker:{symbol:'none'}},
   {name:'Converted endpoint chord',xValues:[xyz[0][1]/1000,xyz[2][1]/1000].map(v=>+v.toFixed(6)),values:[+(xyz[0][0]-base).toFixed(6),+(xyz[2][0]-base).toFixed(6)],line:{fill:C.amber,width:3},marker:{symbol:'none'}},
   {name:'Resolved export samples',xValues:xyz.map(v=>+(v[1]/1000).toFixed(6)),values:xyz.map(v=>+(v[0]-base).toFixed(6)),fill:C.blue,line:{fill:'none',width:0},marker:{symbol:'circle',size:10}}],scatterOptions:{style:'lineWithMarkers'},hasLegend:true,legend:{position:'bottom',textStyle:{typeface:font,fontSize:18,fill:C.ink}},xAxis:axis('ECEF Y (km)'),yAxis:axis('ECEF X relative to chord midpoint (m)'),chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});applyPresentationChartFont(chart,{fontFamily:font});
  text(s,`${story.chord_error_metres.toFixed(3)} m`,842,202,374,62,40,true,C.teal);
  text(s,'Midpoint difference from\ninterpolating only the\nconverted endpoints.',842,292,374,132,28);
  text(s,'Fresh geometry exports\nSample keys 0, 5, 10\ntimeCodesPerSecond = 48',842,473,374,115,27);
  text(s,'Both readers verify each exported sample. No original-trajectory guarantee is claimed between samples. Chart axes use different distance scales.',64,641,1152,70,24,false,C.muted);
  notes='The curve is a 61-point analytic visualization guide. Dots are the three actual resolved sample positions verified in fresh geometry exports. Source longitude goes from 0 to 2 degrees. Chart offset is for presentation only. Literal chart snapshots round plotted values to six decimals; underlying results remain unchanged.';
 }else{
  table(s,[['Consumer','Evidence reaching its output'],['USD Python and C++','Independent placement arithmetic; full point maps, Cartesian frame estimates and polygonal bounds. Shared PROJ and external decoding.'],['Omniverse live geometry',`${story.ov.geometry_vertices.toLocaleString()} vertices read back from runtime buffers/matrices. ${story.ov.edit_checks} edit, failure and recovery checks. Reuses Python placement.`],['Hydra / Storm','Two ordinary resolved exports reach points/transform data sources and the native renderer. No live CRS filter.']],155,335,[320,832],25);
  text(s,`All ${story.export_count} exports pass fresh-reader checks. Geographic scene charts and bound prototypes are covered.`,64,522,1152,59,30,true,C.teal);
  text(s,'Remaining evidence limits: continuous nonlinear certificates, general primvar coverage and physics integration. Detailed candidate choices still need author review.',64,608,1152,98,27,false,C.amber);
 }
 s.speakerNotes.textFrame.setText(`README section: ${d.section}\nREADME SHA-256: ${story.readme_sha256}\nReceipt SHA-256: ${story.run_receipt_sha256}\nImmutable execution receipt SHA-256: ${story.immutable_receipt_sha256}\nProposal SHA-256: ${story.proposal_sha256}\nIntegration evidence SHA-256: ${story.integration_evidence_sha256}\nExecuted source parent: ${story.executed_source_commit}; exact executed files frozen in receipt.\n\nLocal candidate, not group agreement or whole-requirement conformance. Two placement implementations; all use PROJ. OV reuses Python with a verified runtime geometry sink, without an OV render claim. Hydra uses a resolved ordinary-USD export from C++ results. Source data and measured limitations are documented in the README.\n\n${notes}`);
}
const candidate=path.join(tmp,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const tables=[2,3,8,10];const result=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath:final,pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:[9],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(tmp,outputName+'.validation.json')});
console.log(JSON.stringify({final,validation:result.status,slides:10}));
