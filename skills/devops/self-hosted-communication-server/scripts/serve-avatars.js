/**
 * Standalone avatar server for Spacebar.
 * Serves avatar files from /opt/spacebar/files/avatars/<userId>/<hash>
 *
 * Handles both:
 *   /avatars/<userId>/<hash>   — via Caddy reverse proxy
 *   /<userId>/<hash>           — direct
 *
 * Strips the leading "avatars" segment when present.
 * Falls back to bare filename (no extension) if no extension matches.
 *
 * Run: node serve-avatars.js
 * Port: 3456
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const AVATAR_DIR = '/opt/spacebar/files/avatars';
const PORT = 3456;

const MIME_TYPES = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
};

http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0].replace(/\/+$/, '');
  const ext = path.extname(urlPath);
  const lookupPath = ext ? urlPath.slice(0, -ext.length) : urlPath;

  let segments = lookupPath.split('/').filter(Boolean);
  // Strip leading 'avatars' prefix from Caddy proxy
  if (segments.length > 2 && segments[0] === 'avatars') {
    segments = segments.slice(1);
  }

  if (segments.length < 2) {
    res.writeHead(400);
    res.end('Bad request');
    return;
  }

  const userId = segments[0];
  const hash = segments[1];
  const userDir = path.join(AVATAR_DIR, userId);

  // Try with known extensions first
  let found = false;
  const exts = Object.keys(MIME_TYPES);
  exts.some((e) => {
    const fp = path.join(userDir, hash + e);
    if (fs.existsSync(fp)) {
      res.writeHead(200, {
        'Content-Type': MIME_TYPES[e],
        'Cache-Control': 'public, max-age=86400',
      });
      fs.createReadStream(fp).pipe(res);
      found = true;
      return true;
    }
  });

  // Fallback: bare filename (Spacebar stores avatars without extension)
  if (!found) {
    const barePath = path.join(userDir, hash);
    if (fs.existsSync(barePath)) {
      res.writeHead(200, {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=86400',
      });
      fs.createReadStream(barePath).pipe(res);
      found = true;
    }
  }

  if (!found) {
    res.writeHead(404);
    res.end('Not found');
  }
}).listen(PORT, () => {
  console.log(`Avatar server running on port ${PORT}, serving from ${AVATAR_DIR}`);
});