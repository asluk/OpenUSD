// Workspace-only adapter for missing #standard-fonts aliases in the bundled
// artifact-tool PDF renderer. Uses the same standard-font metrics already
// shipped in the runtime. No installed package or final typeface is modified.
import {registerHooks,createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {Font}=require('@pdf-lib/standard-fonts');
const names={Courier:'Courier',CourierBold:'Courier-Bold',CourierBoldOblique:'Courier-BoldOblique',CourierOblique:'Courier-Oblique',Helvetica:'Helvetica',HelveticaBold:'Helvetica-Bold',HelveticaBoldOblique:'Helvetica-BoldOblique',HelveticaOblique:'Helvetica-Oblique',Symbol:'Symbol',TimesBold:'Times-Bold',TimesBoldItalic:'Times-BoldItalic',TimesItalic:'Times-Italic',TimesRoman:'Times-Roman',ZapfDingbats:'ZapfDingbats'};
const data={};
for(const [alias,name]of Object.entries(names)){
 const f=Font.load(name);const glyphs=f.CharMetrics.map(x=>x.N);const indexes=new Map(glyphs.map((g,i)=>[g,i]));const groups=new Map();
 for(const [a,b,k]of f.KernPairs){if(!indexes.has(a)||!indexes.has(b))continue;const list=groups.get(k)??[];list.push(indexes.get(a)*glyphs.length+indexes.get(b));groups.set(k,list);}
 const kern=[];for(const [k,positions]of groups){positions.sort((a,b)=>a-b);let prior=0;kern.push(k,positions.map(x=>{const delta=x-prior;prior=x;return delta;}));}
 data[alias]={name,bbox:f.FontBBox,ascender:f.Ascender??f.FontBBox[3],descender:f.Descender??f.FontBBox[1],xHeight:f.XHeight??0,capHeight:f.CapHeight??0,glyphNames:glyphs.join(' '),glyphWidths:f.CharMetrics.map(x=>x.WX),kernPairs:kern};
}
registerHooks({resolve(specifier,context,next){if(specifier.startsWith('#standard-fonts/')){const name=specifier.split('/')[1];if(!data[name])throw Error('Unknown bundled standard-font alias '+name);return {url:'geospatial-font:'+name,shortCircuit:true};}return next(specifier,context);},load(url,context,next){if(url.startsWith('geospatial-font:'))return {format:'commonjs',source:'module.exports='+JSON.stringify(data[url.split(':')[1]])+';',shortCircuit:true};return next(url,context);}});
