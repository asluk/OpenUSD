// README-derived, editable evidence. Charts use immutable reader returns.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [skill,runtimePython,workspaceDir,outputName='geospatial-build-visual-evidence.pptx']=process.argv.slice(2);
const staging=path.join(workspaceDir,'work/geospatial-visual-deck-20261005');
const finalPath=path.join(workspaceDir,'outputs/geospatial-visual-deck-20261005',outputName);
await fs.mkdir(staging,{recursive:true});await fs.mkdir(path.dirname(finalPath),{recursive:true});
const sha=b=>createHash('sha256').update(b).digest('hex');
const story=JSON.parse(await fs.readFile(path.join(root,'delivery/story.json'),'utf8'));
if(sha(await fs.readFile(path.join(root,'README.md')))!==story.readme_sha256)throw Error('README changed; derive again');
const integrationBytes=await fs.readFile(path.join(root,'delivery/integration-evidence.json'));
if(sha(integrationBytes)!==story.integration_evidence_sha256)throw Error('Integration audit changed; derive again');
const integration=JSON.parse(integrationBytes);
if(integration.capabilities.ov_geospatial_backend||integration.capabilities.rendering)throw Error('Query-only deck cannot advertise backend or rendering integration');
const resultsBytes=await fs.readFile(path.join(root,'delivery/scope-results.json'));
const results=JSON.parse(resultsBytes),report=JSON.parse(await fs.readFile(path.join(root,'delivery/run-report.json'),'utf8'));
const controls=JSON.parse(await fs.readFile(path.join(root,'data/partner-controls.json'),'utf8'));
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({fontFamily:'Arial'});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#233542',teal:'#117E89',blue:'#37659A',amber:'#BE7424',muted:'#526773',light:'#D6DEE3'};
const labels=Object.fromEntries(integration.paths.map(r=>[r.result_key,r.short_label]));
const readers=[['headless',labels.headless,C.teal,'circle',13],['native_usd',labels.native_usd,C.blue,'square',9],['live_ov',labels.live_ov,C.amber,'diamond',5]];
const clean=s=>String(s).replace(/\*\*|`/g,'');
// Editable Excel chart snapshots have a 15-digit decimal limit. Plot offsets
// are rounded to six decimal places; raw returns and coincidence checks stay exact.
const plot=v=>Number(v.toFixed(6));
function text(s,value,x,y,w,h,size=28,bold=false,color=C.ink){
 const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=clean(value);sh.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};return sh;
}
function line(s,x,y,w,h,color=C.light,width=1){return s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:color,width}});}
function arrow(s,x,y,w=60){return s.shapes.add({geometry:'rightArrow',position:{left:x,top:y,width:w,height:24},fill:C.teal,line:{fill:'none',width:0}});}
function table(s,values,top,height,widths,size=24,left=64,width=1152){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left,top,width,height,values,columnWidths:widths});
 t.borders.assign({width:1,fill:C.light,style:'solid'});
 for(let r=0;r<values.length;r++){
  t.rows[r].height=height/values.length;
  for(let c=0;c<values[0].length;c++){
   const cell=t.getCell(r,c);cell.fill=r?'#FFFFFF':C.ink;
   cell.text.style={typeface:font,fontSize:size,color:r?C.ink:'#FFFFFF',bold:!r,autoFit:'none'};
  }
 }return t;
}
function axis(title,min,max,format='0',grid=true){return {title:{text:title,textStyle:{typeface:font,fontSize:19,fill:C.ink}},min,max,numberFormatCode:format,tickLabelPosition:'low',textStyle:{typeface:font,fontSize:18,fill:C.muted},line:{fill:C.light,width:1},majorGridlines:grid?{fill:'#E8EEF1',width:1}:null};}
function query(key,name){const row=results[key].find(r=>r.name===name);if(!row)throw Error('Missing evidence '+name);return row.queries;}
function coordinateChart(s,name,title,units,position){
 const first=query('headless',name)[0].coordinates;
 const qs=readers.map(([key])=>query(key,name));
 for(let r=1;r<qs.length;r++)for(let i=0;i<qs[0].length;i++)if(qs[r][i].coordinates.some((v,j)=>v!==qs[0][i].coordinates[j]))throw Error('Reader coincidence claim changed');
 const chart=s.charts.add('scatter',{
  position,title,titleTextStyle:{typeface:font,fontSize:23,fill:C.ink,bold:true},
  series:readers.map(([key,label,color,symbol,size])=>({name:label,xValues:query(key,name).map(q=>plot(q.coordinates[0]-first[0])),values:query(key,name).map(q=>plot(q.coordinates[1]-first[1])),marker:{symbol,size},fill:color,line:{fill:'none',width:0}})),
  scatterOptions:{style:'marker'},hasLegend:true,legend:{position:'bottom',overlay:false,textStyle:{typeface:font,fontSize:18,fill:C.ink}},
  xAxis:axis('Easting offset ('+units+')',undefined,undefined,'0',false),yAxis:axis('Northing offset ('+units+')',undefined,undefined,'0',true),
  chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:C.light,width:1}
 });applyPresentationChartFont(chart,{fontFamily:font});return first;
}
function valueFlow(s,source,output,sourceName,outputName){
 text(s,'Source USD: '+sourceName,823,210,389,48,25,true);
 text(s,source.map((v,i)=>['E','N','H'][i]+'  '+v.toFixed(4)).join('\n'),823,260,389,112,25);
 arrow(s,830,380,58);text(s,'WKT-defined conversion',906,373,309,66,22,false,C.teal);
 text(s,'Resolved: '+outputName,823,466,389,48,25,true);
 text(s,output.map((v,i)=>['E','N','H'][i]+'  '+v.toFixed(4)).join('\n'),823,521,389,112,25);
}
const layoutEvidence=[];
for(let i=0;i<story.slides.length;i++){
 const d=story.slides[i],s=p.slides.add();s.background.fill='#FFFFFF';
 const titles=['Geospatial proposal readiness','Concrete candidate answers','Four contracts still required','WKT string normalization preserves meaning','USD composition retains CRS bindings','France: matching coordinate queries','Colorado: matching site-calibration queries','Source interpolation before conversion','Authority audit and integration evidence'];
 text(s,titles[i],64,40,1152,104,42,true);
 let notes='';
 if(i===0){
  text(s,d.paragraphs[0],64,176,1152,168,38,true);
  text(s,d.paragraphs[1],64,380,1152,116,31,false,C.teal);
  text(s,d.paragraphs[2],64,540,1152,118,28);
 }else if(i===1){table(s,d.values,150,500,[278,874],23);
 }else if(i===2){
  table(s,d.values,150,442,[345,807],23);
  text(s,'Q9 separately concerns geographic geometry and bounds. Geographic coordinate queries are already in initial scope.',64,612,1152,57,22);
  text(s,'Q12 review clarification: Profiles is the planned route to evaluate; this run did not test its integration.',64,680,1152,25,18,false,C.muted);
 }else if(i===3){
  text(s,'Different spellings converge to one normalized token',64,152,1152,44,29,true,C.teal);
  text(s,'Tested input variants (fragments)',64,214,560,44,24,true);
  text(s,'geodcrs ( … )\nGEODETICCRS[ … ]\n6.37813712345678912345E6',64,278,548,155,26);
  arrow(s,617,330,64);
  text(s,'Preserved normalized text (fragments)',715,214,498,44,24,true);
  text(s,'GEODCRS[ … ]\n6378137.12345678912345',715,292,498,108,26,true);
  line(s,64,454,1152,0);
  text(s,'Quoted content survives',64,480,364,43,24,true);
  text(s,'REMARK["Keep  spaces …"]',64,535,364,65,23);
  text(s,'Frame epoch survives',456,480,347,43,24,true);
  text(s,'FRAMEEPOCH[2015.0]',456,535,347,65,23);
  text(s,'24 lexical tests',850,480,364,43,26,true,C.teal);
  text(s,'Fixed-point validation rejects\nnon-normalized authored text.',850,535,364,72,22);
  text(s,'Token identity is distinct from CRS equivalence. Names are preserved; unknown syntax fails explicitly.\nCoverage is bounded to the tested WKT profile.',64,641,1152,65,21,false,C.muted);
  notes='Fragments abridge the full EXACT test fixture. Case, preferred alias, delimiter, exponent and whitespace variants are separate tested complete strings, not claims that these fragments alone form valid CRS definitions. Coordinate epochs remain unsupported; frame epochs remain CRS metadata.';
 }else if(i===4){
  text(s,'A referenced asset keeps its CRS bindings when composed under /Assembly.',64,145,1152,67,28);
  text(s,'Authored asset',64,240,310,42,26,true);
  text(s,'/World\n    /Data\n    /Independent\n        /Data',64,306,310,143,25);
  arrow(s,375,334,54);
  text(s,'Composed CRS discovery',462,240,405,42,26,true);
  text(s,'/Assembly/Data\n    → binding at /Assembly\n/Assembly/Independent/Data\n    → binding at /Assembly/Independent',462,306,412,162,22);
  arrow(s,877,334,54);
  text(s,'Same results',966,240,246,42,26,true);
  text(s,readers.map(r=>r[1]).join('\n'),966,306,246,143,26,true,C.teal);
  table(s,d.values,484,167,[495,219,219,219],20);
  text(s,'USD in OV means OpenUSD queries hosted in Omniverse. Results stay in JSON.\nBinding discovery is demonstrated; independent model-placement reconciliation remains open.',64,663,1152,48,18,false,C.muted);
  notes='Diagram depicts actual referenced-assembly discovery queries and returned binding_prim paths. Inherited definition: ITRF2020; independent definition: NAD83 / California zone 5 plus NAVD88 height. This does not imply nested model-placement reconciliation.';
 }else if(i===5){
  text(s,'CC49 → Lambert-93 • 59 directly bound origins • same NGF-IGN69 height',64,146,1152,55,26);
  const first=coordinateChart(s,'origins-France_01-to-France_02','Actual Lambert-93 query returns','m',{left:57,top:215,width:735,height:416});
  valueFlow(s,controls.France_01.points[0],first,'CC49','Lambert-93');
  text(s,'All components in metres; chart offsets from output point 0 only. Source values stay unchanged.\n59 origins in both directions; reader difference 0; CSV discrepancy 0.0608 mm. Shared PROJ; no survey-accuracy claim.',64,640,1152,66,20,false,C.muted);
  notes='Chart reads every actual returned coordinate from scope-results.json. Output-only subtraction of point 0 is for readability, adds no scene field and does not relabel source values. Scatter axes have their own scales. All three series coincide exactly, using distinct nested marker shapes. Unchanged NGF-IGN69 height does not exercise a vertical-datum change.';
 }else if(i===6){
  text(s,'Colorado State Plane → Westminster calibrated site • 5 directly bound origins',64,146,1152,55,26);
  const first=coordinateChart(s,'origins-Colorado_02-to-Colorado_03','Actual calibrated-site query returns','ftUS',{left:57,top:215,width:735,height:416});
  valueFlow(s,controls.Colorado_02.points[0],first,'State Plane','calibrated site');
  text(s,'All components in US survey feet. WKT-carried site calibration changes horizontal values and height.\n5 origins in both directions; reader difference 0; CSV discrepancy 0.0342 mm. Source unchanged; shared PROJ.',64,640,1152,66,20,false,C.muted);
  notes='Same actual-reader-return chart convention as France. Input Colorado_02 uses State Plane and NAVD88; output Colorado_03 embeds supplied horizontal and vertical site calibration. This tests the WKT-carried operation, not different datum grids or coordinate epochs. Provider CSVs are PROJ-generated intake/rounding controls. Plot axes have their own scales.';
 }else if(i===7){
  text(s,'WGS84 equator: longitude −1° at t=0 → +1° at t=10; height = 0 m',64,147,1152,55,26);
  const first=query('headless','origin-source-interpolation-0')[0].coordinates;
  const midpoint=query('headless','origin-source-interpolation-5')[0].coordinates;
  const end=query('headless','origin-source-interpolation-10')[0].coordinates;
  const R=6378137; // Semi-major axis authored in the WGS84 fixture, not fitted to reader output.
  for(const [key] of readers)for(const t of [0,5,10]){
   const lon=(-1+t/5)*Math.PI/180,expected=[R*Math.cos(lon),R*Math.sin(lon),0];
   if(query(key,'origin-source-interpolation-'+t)[0].coordinates.some((v,j)=>Math.abs(v-expected[j])>2e-8))throw Error('Recorded interpolation result differs from independent WGS84 control');
  }
  const base=first[0];const curve=Array.from({length:81},(_,j)=>{const lon=(-1+j/40)*Math.PI/180;return {x:R*Math.sin(lon)/1000,y:R*Math.cos(lon)-base};});
  const chart=s.charts.add('scatter',{
   position:{left:57,top:220,width:735,height:396},title:'Equatorial ECEF path — radial scale expanded',titleTextStyle:{typeface:font,fontSize:23,fill:C.ink,bold:true},
   series:[{name:'Analytic source-first path',xValues:curve.map(q=>plot(q.x)),values:curve.map(q=>plot(q.y)),marker:{symbol:'none'},line:{fill:C.teal,width:3}},
     {name:'Converted-endpoint chord',xValues:[plot(first[1]/1000),plot(end[1]/1000)],values:[0,0],marker:{symbol:'none'},line:{fill:C.amber,width:3}},
     ...readers.map(([key,label,color,symbol,size])=>({name:label+' (recorded)',xValues:[0,5,10].map(t=>plot(query(key,'origin-source-interpolation-'+t)[0].coordinates[1]/1000)),values:[0,5,10].map(t=>plot(query(key,'origin-source-interpolation-'+t)[0].coordinates[0]-base)),marker:{symbol,size},fill:color,line:{fill:'none',width:0}}))],
   scatterOptions:{style:'lineWithMarkers'},hasLegend:true,legend:{position:'bottom',overlay:false,textStyle:{typeface:font,fontSize:16,fill:C.ink}},
   xAxis:axis('ECEF Y (km)',-120,120,'0',false),yAxis:axis('ECEF X above endpoint plane (m)',-100,1100,'0',true),
   chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:C.light,width:1}
  });applyPresentationChartFont(chart,{fontFamily:font});
  text(s,'At t=5, source interpolation\nfirst gives longitude 0°.',830,234,382,80,27,true);
  text(s,'All three query paths return\nX = 6,378,137 m\nY = 0 m • Z = 0 m',830,341,382,116,27);
  text(s,report.sampling_record_control.endpoint_chord_midpoint_discrepancy_metres.toFixed(3)+' m',830,480,382,65,40,true,C.teal);
  text(s,'Midpoint error from interpolating\nonly the converted endpoints.',830,551,382,76,24);
  text(s,'Dots are recorded queries at t=0, 5, 10; the curve is an analytic guide. Radial and tangential scales differ.',64,638,1152,31,21,false,C.muted);
  text(s,'Fresh USD sampling record verified: keys 0, 5, 10 and timeCodesPerSecond = 48. This is not a resolved-scene export.',64,682,1152,27,19,false,C.muted);
  notes='81-point analytic WGS84 equatorial guide computed only for visualization. Only the three marked time-code queries were executed by each reader. Endpoint chord is the negative mathematical control. Endpoint X is subtracted solely for display. Tangential axis in kilometres and radial axis in metres intentionally expand radial scale. Core animation time is not a coordinate epoch. Sampling schedule does not guarantee behavior between export samples.';
 }else{
  text(s,'Proposal authority and the executed integration both need audits.',64,154,1152,75,32,true);
  text(s,'Consumer repairs reject unsupported frames and compare geographic identity in declared component units. Source layers stay unchanged.',64,256,1152,91,28);
  text(s,'Integration claims now trace the source input, USD reader, conversion library and actual output. The OV-hosted path returns JSON query results.',64,387,1152,91,28);
  text(s,'All paths share PROJ. Full model geometry, OV geometry writeback, rendering and resolved-scene export have no passing evidence in this run.',64,537,1152,109,28,false,C.teal);
 }
 s.speakerNotes.textFrame.setText(`README section: ${d.readme_section}\nREADME SHA-256: ${story.readme_sha256}\nExecution receipt SHA-256: ${story.run_receipt_sha256}\nExecuted source: ${story.executed_source_commit}\nReader results SHA-256: ${sha(resultsBytes)}\nIntegration evidence SHA-256: ${story.integration_evidence_sha256}\n\nUSD Python and USD C++ are OpenUSD query paths. USD in OV means OpenUSD Python queries hosted in Omniverse, using omni.usd context.get_stage() and pyproj. Their output is JSON. No OV geometry backend receives these computed results and no rendering runs. All three share PROJ.\n\n${d.paragraphs.join('\n\n')}\n\n${notes}\n\nCharts round plotted offsets to six decimal places in the labeled units for editable Excel snapshots. Raw returned coordinates are unchanged; reader coincidence is checked before rounding. Collateral revision uses the same immutable execution. Candidate choices remain under review; partial controls do not certify full placement or geodetic accuracy.`);
 layoutEvidence.push({slide:i+1,readme_section:d.readme_section,native_charts:s.charts.items.length});
}
const candidatePath=path.join(staging,'candidate-'+outputName);await(await PresentationFile.exportPptx(p)).save(candidatePath);
const tables=[2,3,5],charts=[6,7,8];
const result=await finalizePresentation({workspaceDir,candidatePath,finalPath,pythonExecutable:runtimePython,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:story.slides.length,requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:charts,
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(staging,outputName+'.validation.json')});
await fs.writeFile(path.join(staging,outputName+'.evidence.json'),JSON.stringify({readme_sha256:story.readme_sha256,run_receipt_sha256:story.run_receipt_sha256,reader_results_sha256:sha(resultsBytes),executed_source:report.source_commit,slides:layoutEvidence,chart_claim:'Actual coordinate returns; analytic guide separated from executed interpolation samples.',new_runtime_execution:false},null,2));
console.log(JSON.stringify({finalPath,validation:result.status,slides:p.slides.items.length}));
