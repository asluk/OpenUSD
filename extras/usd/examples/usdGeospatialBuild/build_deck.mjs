// The README-derived slide document is the only source of presentation claims.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root = path.resolve(process.argv[2] ?? '.');
const output = path.resolve(process.argv[3] ?? 'deck-build');
const modulePath = process.env.ARTIFACT_TOOL_MODULE;
const { Presentation, PresentationFile } = await import(modulePath ? pathToFileURL(modulePath).href : '@oai/artifact-tool');
const document = JSON.parse(await fs.readFile(path.join(root, 'docs/slides.json'), 'utf8'));
await fs.mkdir(output, { recursive: true });
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const created = [];
const font = 'Arial';
const ink = '#152A36';
const green = '#548B00';
function text(slide, value, x, y, w, h, size, color = ink, bold = false) {
  const box = slide.shapes.add({geometry:'textbox', position:{left:x,top:y,width:w,height:h}, fill:'none',line:{fill:'none',width:0}});
  box.text = value;
  box.text.style = {typeface:font,fontSize:size,color,bold,autoFit:'none'};
  return box;
}
for (const [index, data] of document.slides.entries()) {
  const slide = deck.slides.add();
  created.push(slide);
  slide.background.fill = index === 0 ? '#102B38' : '#FFFFFF';
  if (index === 0) {
    text(slide, data.title, 76, 160, 1120, 115, 68, '#FFFFFF', true);
    text(slide, data.lines[0], 80, 314, 1000, 120, 34, '#DBE8EC');
    text(slide, data.lines[1], 80, 516, 1000, 55, 26, '#A3D744');
  } else {
    text(slide, data.title, 72, 48, 1136, 75, 44, ink, true);
    if (data.chart) {
      const chartStyle = {typeface:font,fontSize:23,fill:ink};
      slide.charts.add('bar', {
        position:{left:70,top:162,width:745,height:410},
        categories:data.chart.categories,
        series:[{name:'Midpoint displacement',values:data.chart.values,fill:green}],
        barOptions:{direction:'column',grouping:'clustered',gapWidth:170},
        hasLegend:false,
        xAxis:{textStyle:chartStyle},
        yAxis:{min:0,max:1100,majorUnit:250,title:{text:'Displacement (m)',textStyle:chartStyle},textStyle:chartStyle},
        dataLabels:{showValue:true,position:'outEnd',textStyle:{...chartStyle,bold:true}},
      });
      text(slide, data.lines[2], 858, 198, 340, 145, 27, ink, true);
      text(slide, data.lines[3], 858, 387, 340, 175, 25);
    } else {
      const gap = data.lines.length >= 6 ? 66 : data.lines.length === 5 ? 92 : 110;
      const size = data.lines.length >= 6 ? 27 : 30;
      data.lines.forEach((line, n) => text(slide, line, 80, 159 + n * gap, 1110, gap - 10, size));
    }
    text(slide, `${index + 1} / ${document.slides.length}`, 1106, 664, 100, 28, 18, '#6B7C84');
  }
  slide.speakerNotes.textFrame.setText(`Source: README.md, section '${data.title}'. README SHA-256: ${document.readme_sha256}.\n${data.lines.join('\n')}`);
}
await (await PresentationFile.exportPptx(deck)).save(path.join(output, 'candidate.pptx'));
for (let n=0; n<created.length; n++) {
  const slide = created[n];
  const png = await deck.export({slide,format:'png',scale:1});
  await fs.writeFile(path.join(output,`slide-${n+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({slides:document.slides.length,readme_sha256:document.readme_sha256,candidate:path.join(output,'candidate.pptx')}));
