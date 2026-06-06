#!/usr/bin/env node
/**
 * helper-server.js
 * Pieni paikallinen palvelin joka vastaanottaa komentoja selaimelta.
 * Aja: node helper-server.js
 * Pidä auki taustalla kun käytät korjaustyökalua.
 */

const http     = require('http');
const { exec } = require('child_process');
const path     = require('path');

const PORT    = 3001;
const WORKDIR = __dirname; // jazz-portfolio kansio

const server = http.createServer((req, res) => {
  // CORS — salli pyynnöt localhost:8080:lta
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    res.writeHead(200); res.end(); return;
  }

  if (req.method === 'POST' && req.url === '/scan') {
    console.log('📷 Skannaus käynnistetty...');
    exec('node generate-manifest.js', { cwd: WORKDIR }, (err, stdout, stderr) => {
      if (err) {
        console.error('Virhe:', err.message);
        res.writeHead(500);
        res.end(JSON.stringify({ ok: false, message: err.message }));
      } else {
        const lines = stdout.trim().split('\n');
        const last  = lines[lines.length - 1];
        console.log('✅', last);
        res.writeHead(200);
        res.end(JSON.stringify({ ok: true, message: last }));
      }
    });
    return;
  }

  res.writeHead(404);
  res.end(JSON.stringify({ ok: false, message: 'Not found' }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`\n✅  Helper-server käynnissä portissa ${PORT}`);
  console.log('   Pidä tämä ikkuna auki kun käytät korjaustyökalua.\n');
});
