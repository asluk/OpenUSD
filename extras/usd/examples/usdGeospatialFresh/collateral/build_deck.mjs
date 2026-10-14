import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const BASE='C:/Users/aluk/Documents/Codex/2026-09-21/have';
const OUT=BASE+'/outputs/geospatial-fresh-build-20261014';
const ROOT=BASE+'/work/geospatial-fresh-20261014';
const TMP=BASE+'/work/geospatial-fresh-report-20261014/deck-build-v3';
const SKILL='C:/Users/aluk/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const ref=BASE+'/outputs/geospatial-deck-clarity-20261006/Geospatial-proposal-explained-2026-10-06-v3.pptx';
await fs.mkdir(TMP,{recursive:true});await fs.mkdir(OUT+'/slides',{recursive:true});
const quality=JSON.parse(await fs.readFile(OUT+'/proposal-quality.json','utf8'));
const controls=JSON.parse(await fs.readFile(ROOT+'/evidence/provider-controls.json','utf8')).filter(r=>r.kind==='provider-control');
const p=Presentation.create({slideSize:{width:1280,height:720}});
const ink='#203744',teal='#007f8b',muted='#526772';let tableOwners=[];
function text(s,value,x,y,w,h,size=26,bold=false,color=ink){const z=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});z.text=value;z.text.style={typeface:'Arial',fontSize:size,bold,color,wrap:'square',autoFit:'none',insets:0,verticalAlignment:'top'};return z;}
function slide(title,lead,notes=''){const s=p.slides.add();s.background.fill='#ffffff';text(s,title,64,44,1152,86,40,true);if(lead)text(s,lead,64,139,1152,84,27);s.speakerNotes.text='Source README: outputs/geospatial-fresh-build-20261014/README.md. Authority: proposal e519199; no source model changes made in this run. '+notes;return s;}
async function picture(s,name,x,y,w,h,alt){s.images.add({blob:new Uint8Array(await fs.readFile(OUT+'/'+name)),contentType:'image/png',alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function foot(s,value){text(s,value,64,642,1152,58,21,false,teal);}
function table(s,values,x,y,w,h,widths,font=23){const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});tableOwners.push(p.slides.items.length);t.borders.assign({style:'solid',fill:'#b2bec4',width:.75});for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){let cell=t.getCell(r,c);cell.fill=r===0?ink:'#ffffff';cell.text.style={typeface:'Arial',fontSize:font,bold:r===0,color:r===0?'#ffffff':ink,autoFit:'none',verticalAlignment:'middle',insets:8};}return t;}
let s=slide('Geospatial USD: proposal quality','');
text(s,'A proposal that can drive a fresh implementation',64,160,550,134,38,true);
text(s,'The tested scene semantics were derivable without adding source fields.\n\nImplementation errors were exposed and corrected against the proposal.',64,330,540,215,28);
await picture(s,'tower-storm-final.png',650,148,575,407,'Actual native Storm render of the C++-resolved Eiffel geometry, with illustrative site context');
text(s,'C++ placement, ordinary USD bake, native Storm',660,567,545,62,21,false,muted);
foot(s,'Bounded evidence of proposal quality. Profiles integration and broader conformance coverage remain explicit.');
s.speakerNotes.text+=' Fresh implementation source was authored without previous geospatial code or outputs before first freeze. One agent; common libraries; not a blinded independent-author study. Native rendered geometry is real output; ground/sky/material are illustrative. Eiffel original asset credit and embedded CC BY 4.0 attribution retained.';

s=slide('Inputs describe meaning; readers compute results','Local points retain their ordinary USD length interpretation. Geospatial inputs tell a reader where and how that model is placed.');
table(s,[['USD input','Meaning'],['crs:wkt','Complete CRS description: datum, axes, units, projection and height reference.'],['crs:position','Absolute origin in its CRS. Geographic 3D uses longitude, latitude and height.'],['crs:orientation','Physical heading, pitch and roll against local geodetic east, north and up.'],['Ordinary xformOps','Intentional scale, pivots and adjustments under the specified ordering.'],['Native dataset association','Asset, format, field and coordinate domain; native values stay paired with locations.']],64,242,1152,359,[350,802],22);
foot(s,'No computed geospatial results become source USD properties. There is no crs:scale or coordinate-epoch field.');

s=slide('Placement and ordinary USD adjustment order','The distinction is between local detail transforms and the anchor’s adjustment after intrinsic geospatial placement.');
table(s,[['Phase','What happens','Driven by'],['1. Source evaluation','Evaluate composed origin and physical attitude at the requested time.','position, orientation, Core time rules'],['2. Local detail','Apply descendant detail transforms, stage units and up-axis mapping.','ordinary local transforms'],['3. Geospatial placement','Place and orient the detail; honor the full CRS and height operation.','WKT + source position + attitude'],['4. Working adjustment','Apply the anchor’s ordinary transforms in its fixed working chart.','anchor xformOps, including pivots'],['5. Requested result','Express coordinates in the requested CRS or ordinary scene chart.','output request + numeric origin']],64,245,1152,355,[245,617,290],22);
foot(s,'A direct child binding is another absolute anchor. Ancestor ordinary transforms do not add its placement again.');
s.speakerNotes.text+=' Normative evaluation and query sections. Tested: nested direct bindings, descendant reset, Y/Z up, source units, reference time offsets, value clips and transported independent instances. Orientation endpoint poses use shortest-arc interpolation; ambiguous half-turn interiors fail.';

s=slide('WKT string normalization and CRS equivalence','A consistent stored spelling enables exact token comparison. It does not turn every equivalent CRS description into identical text.');
table(s,[['Question','Proposed behavior and executed control'],['Does spelling match?','Normalize spaces, preferred keywords and exact decimal spelling. Preserve quoted content.'],['Does meaning survive?','Retain axes, units and authored operations. An analytic static-shift control preserves the WKT transformation.'],['Are different CRSs equivalent?','Resolve semantic equivalence separately. A different normalized token alone does not establish a different Earth reference.']],64,251,1152,325,[355,797],25);
foot(s,'Writers store normalized tokens. Supported non-normal reader input warns and leaves the source layer unchanged.');
s.speakerNotes.text+=' README: WKT string identity and shared placement. Evidence: test_contract WKT controls and focused-native-checks.json analytic BOUNDCRS shift. Preferred productions from https://docs.ogc.org/is/18-010r11/18-010r11.pdf . Full ISO grammar validation is not certified.';

s=slide('Composition and repeated georeferenced assets','Sharing a CRS definition and positioning an occurrence have distinct meanings. The controls distinguish those meanings explicitly.');
table(s,[['Case','Observed behavior'],['Shared CRS library','Reference and inherit composition give the same placement in both readers.'],['Directly bound child','Its absolute placement ignores a parent’s 1,000 m ordinary adjustment.'],['Repeated georeferenced prototype','A 10 m east instance offset applies once. Storage ancestors do not move the occurrence.'],['Missing occurrence frame','An identity occurrence keeps placement. A nonidentity adjustment without its required frame fails.']],64,250,1152,334,[370,782],24);
foot(s,'Instance results retain ID/index and prototype context. General inverse and instance-normal coverage remain explicit limits.');
s.speakerNotes.text+=' README: WKT string identity and shared placement. Evidence: sharing.json, native-controls.json, focused-native-checks.json and test_assembly.py. Equatorial analytic expectations, not previous prototype output. Source ID 1234 is ordinary USD instance identity, not a new geospatial property.';

s=slide('USD Profiles: dependency before payload loading','Profiles uses ClaimsAPI metadata on the entrypoint to declare required processing before a consumer loads content.');
table(s,[['Author','Publisher','Consumer'],['Bind a model or native measurement.','Maintain a conservative summary for all retained content and variants.','Read the qualified usage declaration; load no payload to discover it.'],['Schemas imply the proposed capability.','Publish the summary on the entrypoint, outside payloads.','Treat missing completeness as unknown and retain the dependency.']],64,258,1152,273,[384,384,384],25);
text(s,'Proposed identities',64,560,310,34,25,true);text(s,'usd.geospatial.crsResolution.v1   /   usd.geospatial.publication.v1',64,603,1152,37,25,false,teal);
foot(s,'Publisher coverage is a checkable claim. Discovery does not prove the claim true.');
s.speakerNotes.text+=' https://openusd.org/release/user_guides/schemas/UsdProfiles/overview.html . ClaimsAPI customData.profilesInfo.capabilityUsages and an unqualified profileCompatibility publication claim. Names and graph registration remain proposed; schema-implied capability is not a traversal-generated summary.';

s=slide('Profiles declarations: executed controls','Both freshly written readers discover the same declaration states with zero loaded payloads.');
table(s,[['Published state','Python / C++ discovery','Publisher audit'],['Retained bound content','required / required','Valid hard dependency'],['Qualified empty usage','known-none / known-none','Valid when no retained use needs resolution'],['Unqualified absence','unknown / unknown','Conservative dependency retained'],['Stale empty summary','known-none claim / same claim','Rejected: a retained variant is CRS-bound']],64,249,1152,332,[355,358,439],24);
foot(s,'Clarify integration: generic compatibility-query status is not dependency discovery. Supply the final registration graph.');
s.speakerNotes.text+=' Evidence: profiles.json, profiles-generic-query.json and native guards. A coverage-only local profile graph and a coverage-plus-resolution graph change generic IsCompatibleWith results. Empty usage gives NoPath in this SDK despite the composed completeness claim. This is a registration/integration clarification, not a new placement rule. No fake hard usage was added to force an API result.';

s=slide('Provider coordinates supply independent expectations','The expected answers come from matched provider point IDs. Reader agreement is reported separately from provider error and operation accuracy.');
const rows=[['Provider source','Points','Largest provider error','Python–C++ difference'],...controls.map(c=>[c.region+' '+c.source,String(c.points),(c.max_provider_error_m*1000).toFixed(3)+' mm','0 m in recorded output'])];
table(s,rows,64,247,1152,336,[320,125,350,357],23);
foot(s,'187 comparisons; all within a stated 2 mm tolerance. Rounded controls do not certify survey accuracy.');
s.speakerNotes.text+=' Evidence: provider-controls.json and provider-reader-comparison.json. Local RAF20/GEOID18 resources, network off. Attributed operation accuracy: France tested height paths 0.01 m; Colorado 0.015 m; geographic/geocentric path unknown. Common PROJ is not independent geodetic truth.';

s=slide('A site survey keeps absolute-coordinate meaning','Projection and site calibration stay in the complete WKT. Survey vertices are not reinterpreted as local model offsets.');
await picture(s,'colorado-survey.png',64,245,752,366,'Colorado LandXML absolute survey points after resolution, shown in a local view');
text(s,'14,359 vertices\n710 line parts',864,275,335,92,31,true);text(s,'Explicit north/east/height and US survey feet.\n\nThe two readers agree on every recorded point.',864,400,335,190,27);
foot(s,'LandXML is a producer import demonstration, not a fourth schema data format. The view is a plotting convention.');
s.speakerNotes.text+=' Evidence: survey.json and survey-resolved.npz. Original Trimble LandXML and site-calibration WKT retained. No synthetic elevation or hidden local-anchor reinterpretation. Plot centre/basis is presentation-only.';

s=slide('The railway has a useful horizontal result','An unconfirmed height reference does not justify inventing an altitude. The horizontal workflow can still resolve its location.');
await picture(s,'railway-map.png',64,239,754,378,'Original railway horizontal derivative resolved to Lambert-93');
text(s,'15,822 coordinates',867,280,330,64,32,true);text(s,'Explicit 2D derivative.\n\nOriginal third components and file bytes are preserved.\n\n3D meaning remains unclaimed.',867,378,330,218,27);
foot(s,'The readers agree on the returned horizontal coordinates. No zero-height substitute is used.');
s.speakerNotes.text+=' Evidence: measurements.json, railway-resolved.npz, writer-facts.json. GeoJSON native association is geometry-only. RFC7946 https://www.rfc-editor.org/rfc/rfc7946 . Legacy CRS identifiers are checked as complete recognized spellings, not substring guesses.';

s=slide('CF measurements preserve pairing across space and time','Named dimensions, explicit coordinate roles and observation times determine which value belongs at each location.');
await picture(s,'climate-samples.png',64,247,1152,349,'Synthetic CF observations with permuted coordinate dimensions, retained values and one masked sample');
foot(s,'154 samples; one masked. The original climate file lacks required metadata and is rejected. This CF example is synthetic.');
s.speakerNotes.text+=' Evidence: measurements.json and climate-resolved.npz. 153 valid locations match between readers; values, masks and two observation times preserved. Observation times are not coordinate epochs. Analytics plot, not Hydra/Omniverse render. CF1.12 https://cfconventions.org/Data/cf-conventions/cf-conventions-1.12/cf-conventions.html .';

s=slide('GeoTIFF analytics retain the native sample domain','USD names the asset, band and IFD. Location resolution preserves the cell’s value and mask.');
await picture(s,'city-heatmap.png',64,243,757,374,'Synthetic GeoTIFF city heat field with masked cells');
text(s,'3,072 cells\n24 masked',864,275,335,92,31,true);text(s,'3,048 valid sample locations agree.\n\nPixel-centre mapping and missing-height failure have separate controls.',864,405,335,192,27);
foot(s,'Synthetic 2D heat field; no terrain height assumed. Analytics presentation, not a scene-render claim.');
s.speakerNotes.text+=' Evidence: measurements.json, city-resolved.npz and GeoTIFF Area/Point controls. Native format decoder is shared; placement evaluation is independently written. https://docs.ogc.org/is/19-008r4/19-008r4.html .';

s=slide('Two placement readers; explicit integration paths','The integrations demonstrate how resolved data can be consumed. They do not add a third placement implementation.');
table(s,[['Path','What actually ran'],['Python placement','Fresh composed-USD reader with PROJ.'],['Native C++ placement','Fresh native USD reader; independently written placement math and PROJ calls.'],['Omniverse writeback','Fresh Python results bridged into a stage and read back: 163,416 Eiffel vertices.'],['Native Hydra / Storm','Actual rendering of ordinary USD geometry baked from the C++ placement results.']],64,247,1152,337,[350,802],24);
foot(s,'Dense reader difference ≤ 8 nm; float32 write error ≤ 0.011 mm. These are different from geodetic accuracy.');
s.speakerNotes.text+=' Evidence: tower.json, ov-writeback.json, storm-render-final.log and fresh-export-checks.json. Shared PROJ and format decoder disclosed. No Fabric/ovstage resolver or geospatial Hydra filter. Omniverse output uses an external Python bridge, not an in-process third resolver. Fresh ordinary readers recover the selected bake with one double origin.';

s=slide('The audit tests the implementation against the proposal','Passing images were not enough. The reverse audit checked authored fields, omitted inputs, sampling, native metadata and deferred scope.');
table(s,[['Obligation','Distinguishing control'],['WKT preserves source meaning','OGC-preferred keywords, exact decimals, quoted content and non-normal warnings.'],['No invented height or date','Short 3D tuples fail; time-dependent operations without coordinate epoch are deferred.'],['Correct placement roles and order','Invalid binding roles fail; nested anchors, resets, clips and independent instances execute.'],['A bake represents only what it claims','Unrequested source samples are removed; selected samples and double origin reread correctly.']],64,249,1152,337,[365,787],24);
foot(s,`${quality.evidence.python_contract_controls} Python controls and ${quality.evidence.native_controls} native controls, plus provider, sharing and fresh-export evidence.`);
s.speakerNotes.text+=' Evidence: control-tests-final.xml, native controls/guards, sharing.json and generation receipts. Implementation defects were corrected using existing clauses, including resource-loader collision, stale engine errors and compound geographic chart classification. No new model properties were inserted as fixes. https://docs.ogc.org/is/18-010r11/18-010r11.pdf .';

s=slide('Proposal readiness and proof limits','The tested semantics can be reviewed on their own merits. A successful bounded demonstration is not complete implementation conformance.');
table(s,[['Disposition','Assessment'],['Scene meaning exercised','No new data-model or placement-rule gap found in the tested paths.'],['Profiles integration','Make discovery versus generic compatibility explicit; supply and review the registration graph.'],['Prototype coverage','Nonlinear derivatives, continuous bounds, general instance normals and full format/variant coverage remain unproven.'],['Deferred scope','Coordinate epochs remain deferred; no implicit epoch is supplied and the model keeps a future path.']],64,245,1152,337,[350,802],24);
foot(s,'Unsupported requests remain visible failures. Evidence does not authorize silently approximating an untested domain.');
s.speakerNotes.text+=' Full ISO grammar validation, arbitrary material-graph closure and nested conditional-variant publisher enumeration are not certified. The occurrence exporter rejects authored instance normals. Finite vertices do not prove the nonlinear image of continuous faces/time. This is coverage/implementation limitation, not evidence of missing normative scene meaning.';

s=slide('Fresh derivation and reproducibility','The proposal was the authority. Original data and neutral libraries were reused; previous geospatial source and results were excluded until the first freeze.');
text(s,'New source',64,256,330,45,31,true);text(s,'Schemas, placement evaluation, adapters and fixture writers were authored anew.',64,319,550,125,28);
text(s,'Preserved inputs',688,256,450,45,31,true);text(s,'Proposal and original dataset hashes are unchanged. Corrective candidate generations retain provenance.',688,319,510,140,28);
text(s,'Shared dependencies and scope',64,479,620,45,31,true);text(s,'USD supplies composition; PROJ supplies geodetic operations. One agent’s fresh derivation is not a blinded independent-author study.',64,541,1128,82,28);
foot(s,'Pinned proposal: e519199. README, deck, source-to-clause trace and executable receipts describe the same bounded evidence.');
s.speakerNotes.text+=' generation-record.json, authority/derivation.md, immutability.json and source hashes. Earlier incremental runs are not retroactively labeled fresh. Artifact style follows the clear Arial, white, dark-blue and teal reference deck; its implementation was not generation input.';

const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const candidate=TMP+'/candidate.pptx';await(await PresentationFile.exportPptx(p)).save(candidate);
const fontPolicy={basis:'reference',families:['Arial'],referencePath:ref,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(ref)).digest('hex')};
const result=await finalizePresentation({workspaceDir:BASE,candidatePath:candidate,finalPath:OUT+'/Geospatial-proposal-quality-2026-10-14-v3.pptx',pythonExecutable:PY,integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:tableOwners,fontPolicy,verifyArtifactToolImport:true,receiptPath:TMP+'/validation.json'});
for(const [i,s] of p.slides.items.entries()){const blob=await p.export({slide:s,format:'png',scale:1.35});await fs.writeFile(OUT+'/slides/slide-'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await blob.arrayBuffer()));}
await fs.writeFile(TMP+'/deck-source.json',JSON.stringify({slides:p.slides.items.length,tableOwners,readme:OUT+'/README.md',readmeSha256:crypto.createHash('sha256').update(await fs.readFile(OUT+'/README.md')).digest('hex'),assessment:quality.evidence},null,2));
console.log(JSON.stringify({slides:p.slides.items.length,final:OUT+'/Geospatial-proposal-quality-2026-10-14-v3.pptx',result}));
