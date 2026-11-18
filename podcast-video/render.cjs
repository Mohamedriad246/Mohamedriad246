// Renders top-notch-promo.html frame-by-frame with Playwright and encodes an MP4.
// usage: node render.cjs <landscape|portrait> <out.mp4> [fps=30] [workers=4]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const [,, fmt = 'landscape', out = `out/video-${fmt}.mp4`, fpsArg = '30', workersArg = '4'] = process.argv;
const FPS = Number(fpsArg), WORKERS = Number(workersArg);
const W = fmt === 'portrait' ? 1080 : 1920, H = fmt === 'portrait' ? 1920 : 1080;
const PAGE = 'file://' + path.resolve(__dirname, 'podcast-clip.html') + `?render=1&fmt=${fmt}`;

function ffmpeg(args) {
  const p = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', ...args], { stdio: ['pipe', 'inherit', 'inherit'] });
  p.done = new Promise((res, rej) => p.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  return p;
}

(async () => {
  const browser = await chromium.launch();
  const probe = await browser.newPage({ viewport: { width: W, height: H } });
  await probe.goto(PAGE);
  await probe.waitForFunction(() => window.__ready === true);
  const duration = await probe.evaluate(() => window.__duration);
  await probe.close();

  const total = Math.round(duration * FPS);
  const per = Math.ceil(total / WORKERS);
  const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'tn-'));
  const started = Date.now();
  let doneFrames = 0;

  const chunks = await Promise.all([...Array(WORKERS)].map(async (_, w) => {
    const from = w * per, to = Math.min(total, from + per);
    if (from >= to) return null;
    const file = path.join(tmp, `chunk-${w}.mp4`);
    const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    await page.goto(PAGE);
    await page.waitForFunction(() => window.__ready === true);
    const enc = ffmpeg(['-y', '-f', 'image2pipe', '-c:v', 'png', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS), file]);
    for (let f = from; f < to; f++) {
      await page.evaluate(t => window.__seek(t), f / FPS);
      const buf = await page.screenshot({ type: 'png' });
      if (!enc.stdin.write(buf)) await new Promise(r => enc.stdin.once('drain', r));
      if (++doneFrames % 60 === 0) process.stdout.write(`  ${fmt}: ${doneFrames}/${total} frames (${((Date.now() - started) / 1000).toFixed(0)}s)\n`);
    }
    enc.stdin.end();
    await enc.done;
    await page.close();
    return file;
  }));
  await browser.close();

  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, chunks.filter(Boolean).map(f => `file '${f}'`).join('\n'));
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  await ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out]).done;
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(`done: ${out} (${total} frames, ${((Date.now() - started) / 1000).toFixed(0)}s)`);
})().catch(e => { console.error(e); process.exit(1); });
