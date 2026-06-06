#!/usr/bin/env node
/**
 * generate-profile-manifest.js
 * Lukee profile/-kansion kuvat ja luo profile/manifest.json
 * Ajo: node generate-profile-manifest.js
 */

const fs   = require('fs');
const path = require('path');

const PROFILE_DIR = path.join(__dirname, 'profile');
const MANIFEST    = path.join(PROFILE_DIR, 'manifest.json');
const SUPPORTED   = ['.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG', '.webp'];

if (!fs.existsSync(PROFILE_DIR)) {
  console.error('❌  profile/-kansiota ei löydy!');
  process.exit(1);
}

const files = fs.readdirSync(PROFILE_DIR)
  .filter(f => SUPPORTED.includes(path.extname(f)));

console.log(`📸  Löytyi ${files.length} profiilikuvaa`);

const images = files.map(filename => ({
  filename,
  src: `profile/${filename}`
}));

fs.writeFileSync(MANIFEST, JSON.stringify({ images }, null, 2));
console.log(`✅  profile/manifest.json kirjoitettu`);
