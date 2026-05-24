#!/usr/bin/env node
const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const IMAGES_DIR = path.join(__dirname, 'images');
const MANIFEST   = path.join(__dirname, 'manifest.json');
const SUPPORTED  = ['.jpg', '.jpeg', '.JPG', '.JPEG'];
const PY_SCRIPT  = path.join(__dirname, 'read_meta.py');

function readMeta(filepath) {
  try {
    const raw = execSync(`python3 "${PY_SCRIPT}" "${filepath}"`, { encoding:'utf8' });
    return JSON.parse(raw.trim());
  } catch(e) {
    console.warn('  ⚠ virhe:', e.message.split('\n')[0]);
    return { date:null, artist:null, keywords:[], orientation:'landscape', width:0, height:0 };
  }
}

console.log('📷  Luetaan kuvakansio:', IMAGES_DIR);
if (!fs.existsSync(IMAGES_DIR)) { console.error('❌  images/-kansiota ei löydy!'); process.exit(1); }

const files = fs.readdirSync(IMAGES_DIR).filter(f => SUPPORTED.includes(path.extname(f))).sort();
console.log(`   Löytyi ${files.length} kuvaa\n`);

const images = [];
for (const filename of files) {
  const filepath = path.join(IMAGES_DIR, filename);
  process.stdout.write(`  ↳ ${filename} … `);
  const meta = readMeta(filepath);
  console.log(meta.date || '(ei pvm)', '|', meta.artist || '(ei artistia)');
  images.push({ filename, src:`images/${filename}`, ...meta });
}

images.sort((a,b) => {
  if (!a.date && !b.date) return 0;
  if (!a.date) return 1;
  if (!b.date) return -1;
  return b.date.localeCompare(a.date);
});

fs.writeFileSync(MANIFEST, JSON.stringify({ generated: new Date().toISOString(), count: images.length, images }, null, 2));
console.log(`\n✅  manifest.json kirjoitettu (${images.length} kuvaa)`);
