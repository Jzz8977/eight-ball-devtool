import http from 'node:http';
import { readFile } from 'node:fs/promises';
const root = new URL('./', import.meta.url);
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };
const files = new Set(['index.html', 'styles.css', 'app.js']);
http.createServer(async (req, res) => {
  const path = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
  if (!files.has(path)) { res.writeHead(404); res.end('Not found'); return; }
  try {
    const content = await readFile(new URL(path, root));
    res.writeHead(200, { 'Content-Type': types[path.slice(path.lastIndexOf('.'))] }); res.end(content);
  } catch { res.writeHead(500); res.end('Unable to read file'); }
}).listen(5188, '127.0.0.1', () => console.log('Local: http://127.0.0.1:5188'));
