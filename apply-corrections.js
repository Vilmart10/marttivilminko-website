#!/usr/bin/env node
/**
 * apply-corrections.js
 * Soveltaa corrections.json-tiedoston korjaukset manifest.json:iin.
 *
 * Käyttö: node apply-corrections.js
 */

const fs   = require('fs');
const path = require('path');

const MANIFEST    = path.join(__dirname, 'manifest.json');
const CORRECTIONS = path.join(__dirname, 'corrections.json');

if (!fs.existsSync(CORRECTIONS)) {
  console.error('❌  corrections.json ei löydy!');
  console.log('   Luo se ensin korjaustyökalulla (C-näppäin slideshowssa)');
  process.exit(1);
}

const manifest    = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
const corrections = JSON.parse(fs.readFileSync(CORRECTIONS, 'utf8'));

let count = 0;
manifest.images.forEach(img => {
  if (corrections.hasOwnProperty(img.filename)) {
    const yVal = corrections[img.filename];
    const oldPos = img.facePosition || 'ei asetettu';
    img.facePosition = `center ${yVal}%`;
    console.log(`  ✓ ${img.filename}: ${oldPos} → center ${yVal}%`);
    count++;
  }
});

fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2), 'utf8');
console.log(`\n✅  ${count} korjausta sovellettu manifest.json:iin`);
console.log('   Muista ajaa: git add manifest.json && git commit -m "Asemoinnin korjaukset" && git push');
