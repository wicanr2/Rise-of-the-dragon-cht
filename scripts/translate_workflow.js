// ROTD CHT — multi-agent translation workflow (ScummVM AVG localization).
// Ran 18 parallel translator agents over build/batches/batch_NN.json (English
// dialogue, gitignored as copyrighted source) -> zh_NN.json, applying the 孟波/阿香
// glossary + 1990s cyberpunk-noir register, Big5-safe. Merged into translations/zh.json.
// Reusable for future ScummVM AVG CHT projects. See PLAN.md Phase 4.

export const meta = {
  name: 'rotd-translate',
  description: 'Translate Rise of the Dragon dialogue (2386 lines) to Traditional Chinese with the 孟波/City Hunter homage glossary',
  phases: [{ title: 'Translate', detail: '18 batches translated in parallel' }],
}

const GLOSSARY = [
  'Blade / William "Blade" Hunter → 孟波（致敬《城市獵人》盜版主角，1990s 軟體世界時代梗）',
  'Karyn → 阿香（延伸城市獵人槙村香梗，孟波女友）',
  'Jake → 傑克；Chen / Chen Lu → 陳路；Chandra → 錢德拉（反派）；Chandi → 錢迪',
  'Qwong/Quong → 阿廣；Hwang → 黃；Mayor Vincenzi → 文森奇市長',
  'MTZ → 保留英文 MTZ（毒品代號）；NaPent → 神經素 NaPent（麻醉噴劑）；Pleasure Dome → 歡愉穹頂',
  '說話人標籤 "NAME:" → "中文名："（全形冒號），例如 "BLADE:" → "孟波："',
].join('\n');

const GUIDE = [
  '你是資深繁體中文遊戲在地化譯者。把《Rise of the Dragon》(Dynamix 1990, 賽博龐克黑色偵探 AVG) 的英文對話翻成繁體中文。',
  '規則：',
  '1. 繁體中文，且必須能用 Big5 編碼 —— 只用常見繁體字，避免簡體字、罕用異體字、emoji。',
  '2. 語氣：1990 年代賽博龐克黑色電影、硬漢偵探、街頭味、帶玩世不恭與黑色幽默。第一人稱旁白是主角孟波的內心獨白。',
  '3. 嚴格保留原文的 \\r 換行符（分隔對話框內的行），位置對應原文。',
  '4. 對話要精簡，能塞進小對話框；寧可俐落不要冗長。',
  '5. 數字選單（如 "1. CANCEL  2. Exit"）保留編號，只翻文字（"1. 取消  2. 離開"）。',
  '6. 髒話/粗話用台味口語自然處理（不要直翻）。',
  '7. 一律套用譯名表，全批一致。',
].join('\n');

const a = (typeof args === 'string') ? JSON.parse(args) : (args || {});
const batchDir = a.batchDir || '/home/anr2/rise-of-the-dragon/build/batches';
const count = a.count || 18;
const pad = (i) => String(i).padStart(2, '0');

const jobs = [];
for (let i = 0; i < count; i++) {
  const file = `${batchDir}/batch_${pad(i)}.json`;
  const out = `${batchDir}/zh_${pad(i)}.json`;
  jobs.push({ i, file, out });
}

log(`translating ${count} batches`);

const results = await parallel(jobs.map((j) => () =>
  agent(
    `${GUIDE}\n\n=== 譯名表 ===\n${GLOSSARY}\n\n` +
    `用 Read 工具讀取這個 JSON 陣列檔：${j.file}\n` +
    `每個元素是 {"key","en"}。把每一條 "en" 翻成繁體中文。\n` +
    `然後用 Write 工具把結果（一個 JSON 物件，key→中文翻譯）寫到：${j.out}\n` +
    `最後也回傳同一個 JSON 物件。務必涵蓋這個 batch 的每一個 key。`,
    {
      label: `batch ${pad(j.i)} (${jobs[j.i] ? '' : ''}…)`,
      phase: 'Translate',
      schema: { type: 'object', additionalProperties: { type: 'string' } },
    }
  ).then((r) => ({ i: j.i, n: r ? Object.keys(r).length : 0, ok: !!r }))
));

const okCount = results.filter((r) => r && r.ok).length;
const total = results.reduce((s, r) => s + (r ? r.n : 0), 0);
log(`done: ${okCount}/${count} batches ok, ${total} lines translated (written to ${batchDir}/zh_*.json)`);
return { batches: okCount, lines: total };
