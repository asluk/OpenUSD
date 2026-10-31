//
// Copyright 2026 NVIDIA CORPORATION & AFFILIATES
//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//
// All slide claims, tables and images come from README.md; no parallel narrative.
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skill =
  process.env.PRESENTATIONS_SKILL_DIR ??
  "C:/Users/aluk/.codex/plugins/cache/openai-primary-runtime/presentations/26.1020.11618/skills/presentations";
const { finalizePresentation, resolvePresentationFont } = await import(
  pathToFileURL(path.join(skill, "container_tools/artifact_tool_utils.mjs"))
);
const font = resolvePresentationFont({ fontFamily: "Arial" });
const build = path.join(root, "delivery/deck-build");
await fs.mkdir(build, { recursive: true });
const text = await fs.readFile(path.join(root, "README.md"), "utf8");
const clean = (s) =>
  s
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
const sections = [
  ...text.matchAll(/^## ([^\n]+)\n([\s\S]*?)(?=^## |$(?![\s\S]))/gm),
].map((x) => ({ title: x[1], raw: x[2] }));
if (sections.length !== 12)
  throw Error("Expected 12 standalone README sections");
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const navy = "#213f4c",
  ink = "#284653",
  muted = "#526c75",
  accent = "#8b582b";
function box(slide, s, x, y, w, h, size = 25, bold = false, color = ink) {
  const t = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  t.text = s;
  t.text.style = {
    typeface: font,
    fontSize: size,
    bold,
    color,
    wrap: "square",
    autoFit: "none",
    insets: 0,
    verticalAlignment: "top",
  };
  return t;
}
const tableOwners = [];
const receipt = [];
for (let i = 0; i < sections.length; i++) {
  const section = sections[i],
    slide = p.slides.add();
  slide.background.fill = "#ffffff";
  const blocks = section.raw.trim().split(/\n\s*\n/);
  const lead = clean(
    blocks.find((x) => !x.startsWith("!") && !x.startsWith("|")) ?? "",
  );
  const imageMatch = section.raw.match(/!\[([^\]]*)\]\(([^)]+)\)/);
  const rows = section.raw
    .split("\n")
    .filter((x) => x.startsWith("|") && !/^\|[\s:|-]+\|$/.test(x))
    .map((x) => x.split("|").slice(1, -1).map(clean));
  const evidence = clean(
    blocks.find((x) => x.startsWith("**Evidence.**")) ?? "",
  );
  const caption = blocks.find((x) => x.startsWith("*Caption:"));
  const foot = caption
    ? clean(caption).replace(/^Caption:\s*/, "")
    : evidence.replace(/^Evidence\.\s*/, "").split(/(?<=[.!?])\s+/)[0];
  if (i === 0) {
    box(
      slide,
      clean(text.match(/^# (.+)$/m)[1]),
      64,
      64,
      1136,
      148,
      48,
      true,
      navy,
    );
    const sentences = lead.split(/(?<=[.!?])\s+/);
    box(slide, sentences[0], 64, 263, 1136, 138, 34, true, navy);
    box(
      slide,
      sentences.slice(1).join(" "),
      64,
      432,
      1110,
      168,
      28,
      false,
      muted,
    );
    box(
      slide,
      "Frozen proposal 4120379 · Fresh derivation · 23 October 2026",
      64,
      653,
      1080,
      28,
      18,
      false,
      muted,
    );
  } else {
    box(slide, section.title, 64, 42, 1152, 92, 38, true, navy);
    if (imageMatch && i === 4) {
      slide.images.add({
        blob: await fs.readFile(path.join(root, imageMatch[2])),
        contentType: "image/png",
        alt: imageMatch[1],
        fit: "contain",
        position: { left: 64, top: 150, width: 1152, height: 485 },
      });
    } else if (imageMatch && i === 6) {
      const imageLeft = i === 6;
      const frame = imageLeft
        ? { left: 64, top: 160, width: 540, height: 465 }
        : { left: 584, top: 158, width: 632, height: 465 };
      slide.images.add({
        blob: await fs.readFile(path.join(root, imageMatch[2])),
        contentType: "image/png",
        alt: imageMatch[1],
        fit: "contain",
        position: frame,
      });
      box(
        slide,
        lead,
        imageLeft ? 660 : 64,
        182,
        imageLeft ? 556 : 470,
        416,
        28,
        false,
        ink,
      );
    } else {
      box(slide, lead, 64, 142, 1152, 122, 25, false, ink);
      if (imageMatch)
        slide.images.add({
          blob: await fs.readFile(path.join(root, imageMatch[2])),
          contentType: "image/png",
          alt: imageMatch[1],
          fit: "contain",
          position: { left: 64, top: 270, width: 1152, height: 358 },
        });
      else if (rows.length) {
        tableOwners.push(i + 1);
        const cols = rows[0].length;
        const widths = cols === 3 ? [740, 110, 302] : [390, 762];
        const table = slide.tables.add({
          rows: rows.length,
          columns: cols,
          left: 64,
          top: 282,
          width: 1152,
          height: 338,
          columnWidths: widths,
          values: rows,
        });
        table.borders.assign({ style: "solid", fill: "#bcc9cc", width: 0.75 });
        for (let r = 0; r < rows.length; r++)
          for (let c = 0; c < cols; c++) {
            const cell = table.getCell(r, c);
            cell.fill = r === 0 ? navy : r % 2 ? "#ffffff" : "#f3f6f5";
            cell.text.style = {
              typeface: font,
              fontSize: r === 0 ? 24 : 23,
              color: r === 0 ? "#ffffff" : ink,
              bold: r === 0,
              insets: 10,
              verticalAlignment: "middle",
              wrap: "square",
              autoFit: "none",
            };
          }
      }
    }
    if (foot) box(slide, foot, 64, 654, 1110, 44, 17, false, muted);
    box(slide, String(i + 1), 1192, 664, 24, 24, 16, false, muted);
  }
  slide.speakerNotes.text =
    'Narrative and evidence: README.md, section "' +
    section.title +
    '". Authority: proposal commit 4120379fa12473b54a8f8e11999a1cefa5443614.\n\n' +
    clean(section.raw);
  receipt.push({
    slide: i + 1,
    section: section.title,
    lead,
    image: imageMatch?.[2] ?? null,
    tableRows: rows.length,
  });
}
const candidate = path.join(build, "candidate.pptx");
await (await PresentationFile.exportPptx(p)).save(candidate);
await fs.mkdir(path.join(root, "delivery/output"), { recursive: true });
const final =
  process.env.GEOSPATIAL_DECK_OUTPUT ??
  path.join(root, "delivery/output/Geospatial-USD-proposal-assessment.pptx");
await finalizePresentation({
  workspaceDir: root,
  candidatePath: candidate,
  finalPath: final,
  pythonExecutable:
    "C:/Users/aluk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
  integrityValidatorPath: path.join(
    skill,
    "container_tools/inspect_presentation_package_integrity.py",
  ),
  layoutValidatorPath: path.join(
    skill,
    "container_tools/inspect_presentation_layout_geometry.py",
  ),
  layoutArgs: [
    "--expected-slide-size-emu",
    "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    ...tableOwners.flatMap((n) => ["--require-native-table-slide", String(n)]),
  ],
  explicitTotalSlideCount: 12,
  requiredNativeTableOwnerSlides: tableOwners,
  requiredNativeChartOwnerSlides: [],
  fontPolicy: { basis: "design", families: ["Arial"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(build, path.basename(final) + ".validation.json"),
});
await fs.writeFile(
  path.join(build, "readme-deck-source.json"),
  JSON.stringify(
    {
      readme_sha256: createHash("sha256").update(text).digest("hex"),
      sections: receipt,
    },
    null,
    2,
  ),
);
for (let i = 0; i < p.slides.items.length; i++) {
  const png = await p.export({
    slide: p.slides.items[i],
    format: "png",
    scale: 1.5,
  });
  await fs.writeFile(
    path.join(build, `slide-${i + 1}.png`),
    new Uint8Array(await png.arrayBuffer()),
  );
}
console.log(
  JSON.stringify({
    final,
    slides: 12,
    readme_sha256: createHash("sha256").update(text).digest("hex"),
  }),
);
