import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {Presentation,PresentationFile,registerPdfFontFace} from '@oai/artifact-tool';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.dirname(here);
const workspaceDir=path.resolve(root,'../..');
const outDir=path.join(workspaceDir,'outputs/geospatial-fresh-build-20261015');
const build=path.join(here,'deck-build');
const skill='C:/Users/aluk/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const python='C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES ??= 'C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
await fs.mkdir(outDir,{recursive:true});await fs.mkdir(path.join(build,'pages'),{recursive:true});
for(const [family,file,weight,style] of [['Calibri','calibri.ttf',400,'normal'],['Calibri','calibrib.ttf',700,'normal'],['Calibri','calibrii.ttf',400,'italic'],['Consolas','consola.ttf',400,'normal']]){
 registerPdfFontFace({family,weight,style,source:new Uint8Array(await fs.readFile('C:/Windows/Fonts/'+file))});
}
const md=await fs.readFile(path.join(root,'README.md'),'utf8');
const sections=md.split(/^## /m).slice(1).map(s=>({title:s.slice(0,s.indexOf('\n')).trim(),body:s.slice(s.indexOf('\n')+1).trim()}));
const clean=s=>s.replace(/`/g,'').replace(/\*\*/g,'').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').trim();
const paras=s=>s.body.split(/\n\s*\n/).filter(p=>!p.startsWith('|')&&!p.startsWith('![')&&!p.startsWith('```')).map(clean);
function tableRows(s){return s.body.split('\n').filter(l=>l.startsWith('|')&&!/^\|[- :|]+\|$/.test(l)).map(l=>l.split('|').slice(1,-1).map(clean));}
const p=Presentation.create({slideSize:{width:1280,height:720}});
const navy='#203945',teal='#137e91',ink='#233f4c',muted='#49626e',white='#ffffff';
function txt(slide,name,text,x,y,w,h,size=26,color=ink,bold=false,font='Calibri'){
 const s=slide.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=[{run:clean(text),style:{typeface:font,fontSize:`${size}px`,color,bold}}];s.text.style={fontSize:size,color,bold};s.text.insets=0;return s;
}
function base(title,source,lead=true){
 const s=p.slides.add();s.background.fill=white;txt(s,'title',title,64,42,1152,80,43,navy,true);
 if(lead)txt(s,'lead',paras(source)[0],64,132,1152,103,27,ink);
 s.speakerNotes.text=`Source: the canonical README section "${source.title}".\n\n${source.body}\n\nAuthority SHA-256: 7b7784019d125bf27523929501b72d134810f996a87e764ea0e82db3da120256. Evidence files in this run record executed scope. No complete-conformance or adoption claim.`;
 return s;
}
function table(slide,rows,y=258,height=348,widths=null){
 const t=slide.tables.add({rows:rows.length,columns:rows[0].length,left:64,top:y,width:1152,height,values:rows,...(widths?{columnWidths:widths}:{})});
 t.borders.assign({fill:'#aebec6',width:.65,style:'solid'});
 for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?navy:(r%2?'#ffffff':'#f1f6f8');
  cell.text.set([{run:clean(rows[r][c]),style:{typeface:'Calibri',fontSize:'23px',color:r===0?'#ffffff':ink,bold:r===0}}]);
  cell.text.style={fontSize:23,color:r===0?'#ffffff':ink,bold:r===0};
 }
 return t;
}
async function image(slide,file,x,y,w,h,alt){const b=await fs.readFile(path.join(here,'assets',file));slide.images.add({blob:new Uint8Array(b),contentType:'image/png',alt,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function note(slide,text){return txt(slide,'scope-note',text,64,646,1152,56,21,muted);}

// 1. The quality judgment is explicit and bounded before implementation totals.
{
 const s=base('Geospatial in USD',sections[0],false);
 txt(s,'subhead','Proposal quality and working evidence',64,136,1120,70,38,teal,true);
 txt(s,'assessment',paras(sections[0])[0],64,236,1115,151,32,ink);
 txt(s,'review-state',paras(sections[0])[1],64,420,1115,164,27,muted);
 note(s,'Fresh source generation from the complete proposed contract. 15 October 2026.');
}
// 2. Same table and explanation as the human source.
{
 const s=base(sections[1].title,sections[1]);table(s,tableRows(sections[1]),255,367,[330,822]);
 note(s,'Computed projection effects stay out of the source schema.');
}
// 3. Actual outputs, with a shared camera and an explicit ordinary adjustment.
{
 const s=base(sections[2].title,sections[2]);
 await image(s,'tower-placed.png',40,235,595,338,'Placed original Eiffel geometry before project adjustments');
 await image(s,'tower-final.png',645,235,595,338,'Actual Hydra render of the C++ ordinary bake after project adjustments');
 txt(s,'before','30° true-north heading, nominal 300 m',64,580,550,50,24,teal,true);
 txt(s,'after','Scale 1.15, grid rotation 20°, east 120 m, south 60 m',655,580,558,60,24,teal,true);
 note(s,'Same camera and 100 m display grid. Source position and physical attitude stay unchanged.');
 s.speakerNotes.text+='\nEiffel asset: SDC PERFORMANCE, (FREE) La tour Eiffel, https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674, CC BY 4.0, https://creativecommons.org/licenses/by/4.0/. Illustrative placement, scale, neutral materials and ground change the display. Actual geometry comes from the current bake.';
}
// 4. Independent provider expectations, in physical units.
{
 const s=base(sections[3].title,sections[3]);table(s,tableRows(sections[3]),264,300,[610,90,226,226]);
 txt(s,'distinction','Provider coordinates are the expected answers. Both readers use PROJ, so their agreement is not an independent geodetic algorithm check.',64,590,1152,90,26,muted);
}
// 5. Profiles is a named main-story topic, with concrete authored entries.
{
 const s=base(sections[4].title,sections[4]);
 const code=sections[4].body.match(/```usda\n([\s\S]*?)\n```/)[1];
 txt(s,'authored-profiles',code,72,256,1140,351,22,navy,false,'Consolas');
 note(s,'Existing ClaimsAPI and customData carrier. Versioned identities remain proposed.');
}
// 6. Separate publishing responsibility from the consumer's cheap read.
{
 const s=base('Profiles before payload loading',sections[4],false);
 txt(s,'lead','The publisher maintains conservative coverage. The consumer reads the interface without traversing or loading content.',64,132,1152,98,29,ink);
 table(s,tableRows(sections[4]),260,266,[550,602]);
 txt(s,'publisher','A stronger omission cannot conceal retained dependency. The publisher must refresh or withdraw a stale completeness claim.',64,556,1152,80,27,muted);
 note(s,'Technical registration and schema implication are tested. Namespace stewardship and approval ownership remain review items.');
}
// 7. Global analytics stays visible beside local construction examples.
{
 const s=base(sections[5].title,sections[5]);
 await image(s,'global-climate.png',513,235,710,421,'Scientific plot of the global climate samples at resolved geocentric locations');
 txt(s,'dataset','2,664 climate demonstration values\n\n5,328 illustrative samples across two declared times\n\nDeclared CF metadata, units and synthetic height. Observational provenance is unverified.',64,258,430,356,28,ink);
 note(s,'Both readers preserve sample identities, values, masks and observation times.');
}
// 8. Real original rail and construction data, with explicit conversion provenance.
{
 const s=base(sections[6].title,sections[6]);
 await image(s,'railway.png',48,246,575,336,'Original railway with resolved local display locations and source height colours');
 await image(s,'westminster.png',655,246,575,336,'Original Westminster site-grid design breaklines, no invented triangulation');
 txt(s,'railway-caption','15,822 railway positions\nGeoJSON geometry and height semantics',64,580,540,62,25,teal,true);
 txt(s,'site-caption','13,899 design-breakline positions\nExplicit derived CF copy of LandXML',665,580,540,62,25,teal,true);
 note(s,'Original files remain unchanged. The complete site-calibration WKT retains horizontal and vertical conversions.');
}
// 9. Exact integration roles prevent claims of a third reader or native OV engine.
{
 const s=base(sections[7].title,sections[7]);table(s,tableRows(sections[7]),267,321,[375,777]);
 note(s,'Eiffel bake difference: at most 0.00763 mm. Omniverse stage write/readback: 0 m.');
}
// 10. An independently derived counterexample makes a runtime rule concrete.
{
 const s=base('Source interpolation before projection',sections[8],false);
 txt(s,'lead','The equatorial control places the source-interpolated midpoint on the surface. Interpolating only projected endpoints would miss by 971.4 m.',64,132,1152,105,29,ink);
 await image(s,'interpolation.png',82,235,1116,376,'Analytic equatorial source interpolation compared with the ECEF endpoint chord');
 note(s,'A bake records actual sample keys and time-code scale. Those keys alone do not certify the original between-sample trajectory.');
}
// 11. Coverage limits are visible rather than hidden behind passing point tests.
{
 const s=base('Meaningful failures and coverage limits',sections[8]);
 table(s,[['Requested behavior','Prototype disposition'],
 ['Continuous nonlinear face, curve or subdivision bounds','Unsupported without a domain certificate. Vertex tests provide finite-point evidence.'],
 ['Geometric point/vector/normal primvar export','Explicitly rejected. Ordinary mesh normals have derivative-based transport.'],
 ['Native format coverage','GeoTIFF IFD 0 and the declared CF unit/role subset. Other combinations need separate verification.'],
 ['General inverse and composition coverage','The tested controls pass. Global inverse uniqueness and all value-clip combinations remain unverified.']],252,370,[470,682]);
 note(s,'These are implementation or verification limits against an explicit contract. Complete conformance is not established.');
}
// 12. Review conclusion, with scope deferral kept distinct from foreclosure.
{
 const s=base(sections[9].title,sections[9],false);
 txt(s,'conclusion',paras(sections[9])[0],64,158,1130,163,34,ink);
 txt(s,'scope',paras(sections[9])[1],64,352,1130,148,29,muted);
 txt(s,'proof-boundary','The assessment supports review of the concrete data model and runtime conventions. Profiles ownership and prototype coverage remain explicit.',64,535,1130,87,27,teal,true);
 const credit=note(s,'Eiffel attribution');
 const cs={typeface:'Calibri',fontSize:'21px',color:muted};
 credit.text.set([{run:'Eiffel: ',style:cs},{run:'SDC PERFORMANCE',style:cs,link:{uri:'https://sketchfab.com/3d-models/free-la-tour-eiffel-8553f94d06e24cb4b0fde1080f281674',isExternal:true}},{run:', ',style:cs},{run:'CC BY 4.0',style:cs,link:{uri:'https://creativecommons.org/licenses/by/4.0/',isExternal:true}},{run:'. Illustrative placement, scale and display-material changes.',style:cs}]);
}
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];txt(s,'page',String(i+1),1216,686,32,22,17,muted);
 const png=await p.export({slide:s,format:'png',scale:1.25});await fs.writeFile(path.join(build,'pages',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 const pdf=await p.export({slide:s,format:'pdf'});await fs.writeFile(path.join(build,'pages',`slide-${String(i+1).padStart(2,'0')}.pdf`),new Uint8Array(await pdf.arrayBuffer()));
 await fs.writeFile(path.join(build,'progress.json'),JSON.stringify({rendered_slides:i+1,total:p.slides.items.length}));
 console.log(`Rendered ${i+1}/${p.slides.items.length}`);
}
const candidate=path.join(build,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const finalPath=path.join(outDir,'Geospatial-proposal-quality-2026-10-15-v3.pptx');
await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath,pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[2,4,6,9,11].flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[2,4,6,9,11],
 fontPolicy:{basis:'design',families:['Calibri','Consolas']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation-v3.json')});
await fs.writeFile(path.join(build,'readme-deck-source.json'),JSON.stringify({readme_sha256:(await import('node:crypto')).createHash('sha256').update(md).digest('hex'),sections:sections.map(s=>s.title),slides:12,output:finalPath},null,2));
console.log(finalPath);
