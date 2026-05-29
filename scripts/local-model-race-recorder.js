#!/usr/bin/env node
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const RECORDING_DIR = join(ROOT, "var", "recordings");
const TMP_DIR = join(ROOT, "var", "tmp");
mkdirSync(RECORDING_DIR, { recursive: true });
mkdirSync(TMP_DIR, { recursive: true });

const HOST = process.env.MERCURY_RACE_HOST || "0.0.0.0";
const PORT = Number(process.env.MERCURY_RACE_PORT || 18888);
const REMOTE = process.env.MERCURY_RACE_REMOTE || "norik@192.168.1.101";
const REMOTE_ROOT = process.env.MERCURY_RACE_REMOTE_ROOT || "/home/norika/Neuron-Mercury";
const RESIDENT_URL = process.env.MERCURY_RACE_RESIDENT_URL || "http://127.0.0.1:17345";
const DEFAULT_MODEL = process.env.MERCURY_RACE_MODEL || "qwen2.5:7b";
const DEFAULT_NUM_PREDICT = Number(process.env.MERCURY_RACE_NUM_PREDICT || 900);
const ACCESS_KEY_PATH = join(TMP_DIR, "local-model-race-recorder.key");
const ACCESS_KEY = process.env.MERCURY_RACE_ACCESS_KEY || (() => {
  if (existsSync(ACCESS_KEY_PATH)) return readFileSync(ACCESS_KEY_PATH, "utf8").trim();
  const key = randomBytes(12).toString("hex");
  writeFileSync(ACCESS_KEY_PATH, `${key}\n`, "utf8");
  return key;
})();
const DEFAULT_PROMPT = [
  "請用繁體中文回答一個高難度產品工程問題：",
  "你是一台 RTX 3060 Windows 筆電上的本地 AI 加速器，不能呼叫雲端模型。",
  "請設計一套能讓大型本地語言模型第一次提問就有感變快的架構，必須同時處理：",
  "1. 冷啟動第一包答案；2. 背景完整補完；3. 第二次毫秒級 replay；4. UMA/RAG 專案記憶；",
  "5. 3000 個實體神經元與 10000 個虛擬神經元如何調度；6. 低衝擊模式不能拖慢遊戲；",
  "7. 如何用 benchmark 證明不是假加速；8. 如何避免舊記憶污染不同專案。",
  "請給出架構、資料流、風險、驗證指標與一個具體使用者情境。"
].join("\n");

function requestUrl(req) {
  return new URL(req.url || "/", `http://${req.headers.host || `${HOST}:${PORT}`}`);
}

function isLocalRequest(req) {
  const remote = req.socket.remoteAddress || "";
  return remote === "127.0.0.1" || remote === "::1" || remote === "::ffff:127.0.0.1";
}

function authorized(req) {
  if (isLocalRequest(req)) return true;
  const url = requestUrl(req);
  return url.searchParams.get("key") === ACCESS_KEY || req.headers["x-mercury-access-key"] === ACCESS_KEY;
}

function json(res, status, payload) {
  const text = JSON.stringify(payload);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(text)
  });
  res.end(text);
}

function readBody(req, limit = 20 * 1024 * 1024) {
  return new Promise((resolvePromise, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error("request body too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolvePromise(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function run(command, args, options = {}) {
  const started = Date.now();
  return new Promise((resolvePromise) => {
    const child = spawn(command, args, { ...options, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      try { child.kill("SIGTERM"); } catch {}
      setTimeout(() => {
        try { child.kill("SIGKILL"); } catch {}
      }, 1500).unref?.();
    }, options.timeoutMs || 240000);
    child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolvePromise({ code, stdout, stderr, elapsed_ms: Date.now() - started });
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      resolvePromise({ code: 1, stdout, stderr: `${stderr}\n${error.message}`, elapsed_ms: Date.now() - started });
    });
  });
}

async function runRemoteNode(source, payload, timeoutMs = 240000) {
  const b64 = Buffer.from(JSON.stringify(payload)).toString("base64");
  const script = [
    `cd ${JSON.stringify(REMOTE_ROOT)} || exit 1`,
    `export MERCURY_RACE_PAYLOAD='${b64}'`,
    "node --input-type=module <<'NODE'",
    source,
    "NODE"
  ].join("\n");
  const scriptB64 = Buffer.from(script).toString("base64");
  const remoteCommand = `wsl.exe -e bash -lc "printf '%s' '${scriptB64}' | base64 -d | bash"`;
  const result = await run("ssh", [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    REMOTE,
    remoteCommand
  ], { timeoutMs });
  const lastJson = result.stdout.trim().split(/\n/).reverse().find((line) => line.trim().startsWith("{"));
  if (!lastJson) return { ok: false, mode: "remote_no_json", ...result };
  try {
    return { ok: result.code === 0, ...JSON.parse(lastJson), ssh_elapsed_ms: result.elapsed_ms, stderr: result.stderr.trim() };
  } catch (error) {
    return { ok: false, mode: "remote_bad_json", error: error.message, ...result };
  }
}

async function runRemoteShell(source, timeoutMs = 240000) {
  const scriptB64 = Buffer.from(source).toString("base64");
  const remoteCommand = `wsl.exe -e bash -lc "printf '%s' '${scriptB64}' | base64 -d | bash"`;
  const result = await run("ssh", [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    REMOTE,
    remoteCommand
  ], { timeoutMs });
  const lastJson = result.stdout.trim().split(/\n/).reverse().find((line) => line.trim().startsWith("{"));
  if (!lastJson) return { ok: false, mode: "remote_shell_no_json", ...result };
  try {
    return { ok: result.code === 0, ...JSON.parse(lastJson), ssh_elapsed_ms: result.elapsed_ms, stderr: result.stderr.trim() };
  } catch (error) {
    return { ok: false, mode: "remote_shell_bad_json", error: error.message, ...result };
  }
}

const activateShell = `
set -e
cd ${JSON.stringify(REMOTE_ROOT)}
started="$(date +%s%3N)"
node src/mercury.js resident restart --port=17345 --low-impact >/tmp/mercury-race-activate-resident.log 2>&1
node src/mercury.js bench-resident-llm-fast-endpoint --url=${JSON.stringify(RESIDENT_URL)} >/tmp/mercury-race-activate-fast.log 2>&1
node src/mercury.js bench-resident-llm-fast-final-merge-endpoint --url=${JSON.stringify(RESIDENT_URL)} >/tmp/mercury-race-activate-merge.log 2>&1
status="$(node src/mercury.js product status --skip-heavy)"
ready="$(printf '%s\\n' "$status" | grep -m1 '^ready:' || true)"
fast="$(printf '%s\\n' "$status" | grep -m1 'Resident LLM first-answer API' || true)"
merge="$(printf '%s\\n' "$status" | grep -m1 'Resident LLM final-merge API' || true)"
now="$(date +%s%3N)"
READY="$ready" FAST="$fast" MERGE="$merge" STARTED="$started" NOW="$now" node -e 'const ready=process.env.READY||""; const payload={ok: ready.includes("ready: yes"), mode:"mercury_acceleration_activated", elapsed_ms:Number(process.env.NOW)-Number(process.env.STARTED), ready, first_answer:process.env.FAST||"", final_merge:process.env.MERGE||""}; console.log(JSON.stringify(payload));'
`;

const modelsSource = `
const started = Date.now();
try {
  const response = await fetch("http://127.0.0.1:11434/api/tags");
  const json = await response.json().catch(() => ({}));
  const models = (json.models || []).map((item) => item.name).filter(Boolean);
  console.log(JSON.stringify({ ok: response.ok, mode: "ollama_models", elapsed_ms: Date.now() - started, models }));
} catch (error) {
  console.log(JSON.stringify({ ok: false, mode: "ollama_models", elapsed_ms: Date.now() - started, models: [], error: error.name + ": " + error.message }));
}
`;

const baselineSource = `
const payload = JSON.parse(Buffer.from(process.env.MERCURY_RACE_PAYLOAD, "base64").toString("utf8"));
const started = Date.now();
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), payload.timeout_ms || 210000);
try {
  const response = await fetch("http://127.0.0.1:11434/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model: payload.model,
      prompt: payload.prompt,
      stream: false,
      options: { num_predict: payload.num_predict, temperature: 0 }
    }),
    signal: controller.signal
  });
  const json = await response.json().catch(() => ({}));
  console.log(JSON.stringify({
    ok: response.ok,
    mode: "ollama_direct_baseline",
    status: response.status,
    elapsed_ms: Date.now() - started,
    model: payload.model,
    response: String(json.response || "").trim(),
    response_chars: String(json.response || "").trim().length,
    total_duration_ns: json.total_duration || 0,
    eval_count: json.eval_count || 0,
    eval_duration_ns: json.eval_duration || 0
  }));
} catch (error) {
  console.log(JSON.stringify({ ok: false, mode: "ollama_direct_baseline", elapsed_ms: Date.now() - started, error: error.name + ": " + error.message }));
} finally {
  clearTimeout(timer);
}
`;

const mercurySource = `
const payload = JSON.parse(Buffer.from(process.env.MERCURY_RACE_PAYLOAD, "base64").toString("utf8"));
const started = Date.now();
const response = await fetch(payload.resident_url + "/llm-fast", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({
    model: payload.model,
    prompt: payload.prompt,
    intent: payload.intent,
    enqueue_miss: true,
    force_first_packet: true,
    num_predict: payload.num_predict
  })
});
const json = await response.json().catch(() => ({}));
console.log(JSON.stringify({
  ok: response.ok && json.ok !== false,
  mode: json.mode || "mercury_llm_fast",
  status: response.status,
  elapsed_ms: Date.now() - started,
  model: json.model || payload.model,
  response: String(json.response || "").trim(),
  response_chars: Number(json.response_chars || String(json.response || "").trim().length),
  packet_ms: json.packet?.elapsed_ms ?? null,
  background_completion: json.background_completion || null
}));
`;

function pageHtml() {
  return `<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Neuron Mercury Local Model Race</title>
<style>
  :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #080a0f; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #080a0f; color: #eef3ff; overflow-x: auto; }
  main { width: min(1680px, 100%); min-width: 980px; margin: 0 auto; padding: 14px; display: grid; gap: 12px; }
  header { display: flex; justify-content: space-between; align-items: end; gap: 14px; padding-bottom: 8px; border-bottom: 1px solid #223149; }
  h1 { margin: 0; font-size: clamp(24px, 3vw, 42px); line-height: 1.02; letter-spacing: 0; }
  .sub { color: #9fb0c8; font-size: 14px; margin-top: 6px; }
  .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
  label { color: #9fb0c8; font-size: 13px; font-weight: 800; display: grid; gap: 5px; }
  select, input, textarea { border: 1px solid #2a3850; border-radius: 8px; background: #0d1423; color: #eef3ff; outline: none; }
  select, input { min-height: 42px; padding: 9px 11px; font: 800 14px/1.2 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  textarea { width: 100%; min-height: 132px; max-height: 220px; resize: vertical; padding: 14px; font: 700 17px/1.58 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  button { border: 0; border-radius: 8px; min-height: 66px; padding: 14px 18px; font-weight: 950; font-size: clamp(18px, 2vw, 30px); cursor: pointer; }
  button:disabled { opacity: .55; cursor: wait; }
  .prompt-panel { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 12px; padding: 14px; border: 1px solid #223149; border-radius: 8px; background: #0a1020; }
  .dropzone { border: 1px dashed #46617f; border-radius: 8px; padding: 14px; color: #cfe0fb; background: #0d1423; display: grid; gap: 12px; align-content: center; }
  .dropzone.drag { border-color: #2ef2a8; background: #11231e; }
  .hint { color: #9fb0c8; font-size: 13px; line-height: 1.45; }
  .status-line { grid-column: 1 / -1; }
  .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  #runBaseline { background: #ffbd77; color: #160b02; }
  #runMercury { background: linear-gradient(135deg, #fff06a 0%, #2ef2a8 58%, #75d7ff 100%); color: #03110d; box-shadow: 0 0 34px rgba(46,242,168,.2); }
  .bolt { display: inline-block; margin-right: 8px; font-size: 1.15em; text-shadow: 0 0 18px rgba(255,240,106,.9); }
  .results { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .card { min-height: 390px; border: 1px solid #263a57; border-radius: 8px; background: #0d1423; display: grid; grid-template-rows: auto auto auto minmax(0, 1fr); overflow: hidden; }
  .card-head { padding: 16px 18px 10px; border-bottom: 1px solid #1d2a40; display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
  .title { font-size: clamp(22px, 2.2vw, 34px); line-height: 1.05; font-weight: 950; }
  .left .title { color: #ffbd77; }
  .right .title { color: #63f4b5; }
  .time { font: 950 clamp(24px, 3vw, 46px)/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; color: #eef3ff; white-space: nowrap; }
  .bar-wrap { height: 10px; margin: 0 18px 12px; background: #182338; border-radius: 999px; overflow: hidden; }
  .bar { height: 100%; width: 0%; background: #ffbd77; transition: width .2s linear; }
  .right .bar { background: #2ef2a8; }
  .text { min-height: 0; padding: 14px 18px 18px; overflow: auto; white-space: pre-wrap; color: #eaf1ff; font-size: 17px; line-height: 1.58; }
  .status { color: #9fb0c8; font-size: 14px; padding: 0 18px 10px; }
  .comparison { min-height: 54px; display: flex; align-items: center; justify-content: center; border: 1px solid #263a57; border-radius: 8px; background: #0a1020; color: #dbe8ff; font-weight: 950; font-size: clamp(18px, 2vw, 30px); text-align: center; padding: 12px; }
  @media (max-width: 1100px) {
    main { min-width: 920px; }
    .prompt-panel { grid-template-columns: minmax(0, 1fr) 300px; }
  }
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Neuron Mercury Local Model Race</h1>
      <div class="sub">同一個模型、同一個困難題目：左邊是完整原生生成，右邊目前只驗證 Mercury 第一包提示，不能冒充完整回答加速。</div>
    </div>
    <div class="toolbar">
      <label>模型
        <select id="model"><option value="${DEFAULT_MODEL}">${DEFAULT_MODEL}</option></select>
      </label>
      <label>輸出 token
        <input id="numPredict" value="${DEFAULT_NUM_PREDICT}" type="number" min="128" max="1600" step="64" />
      </label>
    </div>
  </header>

  <section class="prompt-panel">
    <textarea id="prompt" aria-label="測試題目"></textarea>
    <div id="dropzone" class="dropzone">
      <div>
        <b>拖拉文件到這裡</b>
        <div class="hint">會自動改成「約 1500 字文件摘要」測試題，左右兩邊都用同一份內容比較。</div>
      </div>
      <button id="pickFile" type="button" style="min-height:42px;font-size:15px;background:#22304a;color:#dfeaff">選擇文件</button>
      <input id="fileInput" type="file" hidden />
    </div>
    <div id="status" class="hint status-line">Ready. Remote: ${REMOTE}</div>
  </section>

  <section class="actions">
    <button id="runBaseline" type="button">一般生成</button>
    <button id="runMercury" type="button"><span class="bolt">⚡</span>Mercury 第一包提示</button>
  </section>

  <section class="results">
    <article class="card left">
      <div class="card-head">
        <div>
          <div class="title">一般生成</div>
          <div class="hint">Ollama direct / 原生本地模型</div>
        </div>
        <div id="baselineTime" class="time">-- ms</div>
      </div>
      <div id="baselineStatus" class="status">尚未開始</div>
      <div class="bar-wrap"><div id="baselineBar" class="bar"></div></div>
      <div id="baselineText" class="text">點擊「一般生成」後，這裡顯示完整回覆。</div>
    </article>

    <article class="card right">
      <div class="card-head">
        <div>
          <div class="title">⚡ Mercury 第一包提示</div>
          <div class="hint">First packet only / 不是完整回答加速</div>
        </div>
        <div id="mercuryTime" class="time">-- ms</div>
      </div>
      <div id="mercuryStatus" class="status">尚未啟動</div>
      <div class="bar-wrap"><div id="mercuryBar" class="bar"></div></div>
      <div id="mercuryText" class="text">點擊「Mercury 第一包提示」後，這裡只顯示第一包提示。若字數不足，不算完整回答加速。</div>
    </article>
  </section>

  <section id="comparison" class="comparison">目前不宣稱完整回答加速。只有右邊達到左邊 80% 字數以上，才允許比較。</section>
</main>
<script>
const defaultPrompt = ${JSON.stringify(DEFAULT_PROMPT)};
const promptBox = document.getElementById("prompt");
promptBox.value = defaultPrompt;
const modelSelect = document.getElementById("model");
const numPredictInput = document.getElementById("numPredict");
const runBaselineBtn = document.getElementById("runBaseline");
const runMercuryBtn = document.getElementById("runMercury");
const statusEl = document.getElementById("status");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const pickFileBtn = document.getElementById("pickFile");
const comparisonEl = document.getElementById("comparison");
const accessKey = new URL(location.href).searchParams.get("key") || "";
const state = {
  baseline: { elapsed: null, timer: null, started: null, chars: 0 },
  mercury: { elapsed: null, timer: null, started: null, chars: 0, comparable: false },
  accelerationActive: false
};

async function postJson(url, body) {
  const fullUrl = accessKey ? url + (url.includes("?") ? "&" : "?") + "key=" + encodeURIComponent(accessKey) : url;
  const response = await fetch(fullUrl, { method: "POST", headers: { "content-type": "application/json", "x-mercury-access-key": accessKey }, body: JSON.stringify(body) });
  const json = await response.json();
  if (!response.ok || json.ok === false) throw new Error(json.error || json.mode || "request failed");
  return json;
}

async function loadModels() {
  try {
    const fullUrl = accessKey ? "/api/models?key=" + encodeURIComponent(accessKey) : "/api/models";
    const response = await fetch(fullUrl, { headers: { "x-mercury-access-key": accessKey } });
    const json = await response.json();
    const models = Array.from(new Set([...(json.models || []), "${DEFAULT_MODEL}"].filter(Boolean)));
    modelSelect.innerHTML = "";
    for (const model of models) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      if (model === "${DEFAULT_MODEL}") option.selected = true;
      modelSelect.appendChild(option);
    }
    statusEl.textContent = "Ready. Models loaded: " + models.join(", ");
  } catch (error) {
    statusEl.textContent = "Ready. Model list fallback: ${DEFAULT_MODEL}";
  }
}

function readOptions() {
  return {
    model: modelSelect.value || "${DEFAULT_MODEL}",
    num_predict: Math.max(128, Math.min(1600, Number(numPredictInput.value) || ${DEFAULT_NUM_PREDICT})),
    prompt: promptBox.value
  };
}

function setLane(kind, patch) {
  if (patch.time !== undefined) document.getElementById(kind + "Time").textContent = patch.time;
  if (patch.status !== undefined) document.getElementById(kind + "Status").textContent = patch.status;
  if (patch.text !== undefined) {
    const textEl = document.getElementById(kind + "Text");
    textEl.textContent = patch.text;
    textEl.scrollTop = 0;
  }
  if (patch.bar !== undefined) document.getElementById(kind + "Bar").style.width = patch.bar + "%";
}

function startTimer(kind, label) {
  clearInterval(state[kind].timer);
  state[kind].started = performance.now();
  state[kind].elapsed = null;
  state[kind].chars = 0;
  if (kind === "mercury") state[kind].comparable = false;
  setLane(kind, { time: "0 ms", status: label, text: "生成中...", bar: 8 });
  state[kind].timer = setInterval(() => {
    const elapsed = Math.round(performance.now() - state[kind].started);
    setLane(kind, { time: elapsed + " ms", bar: Math.min(92, 8 + elapsed / 220) });
  }, 90);
}

function finishTimer(kind, elapsed, status, text) {
  clearInterval(state[kind].timer);
  state[kind].elapsed = elapsed;
  state[kind].chars = String(text || "").trim().length;
  setLane(kind, { time: elapsed + " ms", status, text: text || "", bar: 100 });
  const written = document.getElementById(kind + "Text").textContent.trim();
  if (!written) setLane(kind, { status: "失敗 / 畫面沒有顯示答案", text: "沒有答案顯示，這次不算加速成功。" });
  updateComparison();
}

function visibleElapsed(kind) {
  return Math.max(1, Math.round(performance.now() - state[kind].started));
}

function updateComparison() {
  if (!state.baseline.elapsed || !state.mercury.elapsed) return;
  const baselineChars = state.baseline.chars || 0;
  const mercuryChars = state.mercury.chars || 0;
  const comparable = baselineChars > 0 && mercuryChars >= Math.ceil(baselineChars * 0.8);
  state.mercury.comparable = comparable;
  if (!comparable) {
    comparisonEl.textContent = "不公平比較：Mercury 只有 " + mercuryChars + " 字，原生有 " + baselineChars + " 字；少於 80%，不算加速勝利。";
    return;
  }
  const ratio = state.baseline.elapsed / Math.max(1, state.mercury.elapsed);
  const delta = state.baseline.elapsed - state.mercury.elapsed;
  const baselineRate = Math.round(baselineChars / Math.max(1, state.baseline.elapsed) * 1000);
  const mercuryRate = Math.round(mercuryChars / Math.max(1, state.mercury.elapsed) * 1000);
  comparisonEl.textContent = "公平字數比較：" + ratio.toFixed(2) + "x，節省 " + Math.max(0, delta) + " ms；原生 " + baselineChars + " 字/" + baselineRate + "字秒，Mercury " + mercuryChars + " 字/" + mercuryRate + "字秒。";
}

async function runBaseline() {
  const options = readOptions();
  runBaselineBtn.disabled = true;
  statusEl.textContent = "一般生成：正在呼叫 " + options.model + " 原生本地模型...";
  startTimer("baseline", "Ollama direct running");
  try {
    const out = await postJson("/api/baseline", options);
    const text = out.response || "";
    if (text.trim().length < 20) throw new Error(out.error || "原生模型沒有回傳有效文字");
    finishTimer("baseline", visibleElapsed("baseline"), "完成 / " + text.length + " 字 / browser-visible / model " + options.model + " / server " + out.elapsed_ms + " ms", text);
    statusEl.textContent = "一般生成完成。";
  } catch (error) {
    finishTimer("baseline", visibleElapsed("baseline"), "失敗", error.message);
    statusEl.textContent = "一般生成失敗：" + error.message;
  } finally {
    runBaselineBtn.disabled = false;
  }
}

async function runMercury() {
  const options = readOptions();
  runMercuryBtn.disabled = true;
  statusEl.textContent = "Neuron Mecury：啟動加速並生成...";
  startTimer("mercury", "啟動 Mercury 加速中");
  try {
    if (!state.accelerationActive) {
      try {
        const activated = await postJson("/api/activate", {});
        state.accelerationActive = true;
        setLane("mercury", { status: "加速已啟動 / " + (activated.elapsed_ms || 0) + " ms" });
      } catch (activationError) {
        state.accelerationActive = false;
        setLane("mercury", { status: "warmup 失敗，改直接測 Mercury API / " + activationError.message });
      }
    }
    const out = await postJson("/api/mercury", options);
    const text = out.response || "";
    if (text.trim().length < 20) throw new Error(out.error || "Mercury 沒有回傳有效文字，這次不算加速成功");
    const minChars = state.baseline.chars ? Math.ceil(state.baseline.chars * 0.8) : 0;
    const fair = !state.baseline.chars || text.trim().length >= minChars;
    const verdict = fair ? "完成" : "字數不足，不算加速勝利";
    const status = verdict + " / " + text.trim().length + " 字" + (state.baseline.chars ? " vs 原生 " + state.baseline.chars + " 字" : "") + " / browser-visible / packet " + (out.packet_ms ?? "--") + " ms / server " + out.elapsed_ms + " ms / " + options.model;
    finishTimer("mercury", visibleElapsed("mercury"), status, text);
    statusEl.textContent = fair ? "Neuron Mecury 生成完成。" : "Neuron Mecury 字數不足：這次不算公平加速。";
  } catch (error) {
    finishTimer("mercury", visibleElapsed("mercury"), "失敗", error.message);
    statusEl.textContent = "Neuron Mecury 生成失敗：" + error.message;
  } finally {
    runMercuryBtn.disabled = false;
  }
}

async function loadFile(file) {
  if (!file) return;
  statusEl.textContent = "讀取文件：" + file.name;
  const text = await file.text();
  const body = text.slice(0, 60000);
  promptBox.value = "請針對以下文件做約1500字繁體中文摘要，包含：\\n1. 核心主旨\\n2. 重要細節\\n3. 風險與限制\\n4. 可執行下一步\\n5. 一句話結論\\n\\n檔名：" + file.name + "\\n文件內容：\\n" + body;
  statusEl.textContent = "文件已載入：" + file.name + " / " + text.length + " chars";
}

dropzone.addEventListener("dragover", event => {
  event.preventDefault();
  dropzone.classList.add("drag");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", event => {
  event.preventDefault();
  dropzone.classList.remove("drag");
  loadFile(event.dataTransfer.files[0]);
});
pickFileBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => loadFile(fileInput.files[0]));
runBaselineBtn.addEventListener("click", runBaseline);
runMercuryBtn.addEventListener("click", runMercury);
loadModels();
</script>
</body>
</html>`;
}

async function handleApi(req, res) {
  if (!authorized(req)) {
    json(res, 401, { ok: false, error: "access key required" });
    return;
  }
  const url = requestUrl(req);
  const raw = await readBody(req, 512 * 1024);
  let payload = {};
  try { payload = raw.length ? JSON.parse(raw.toString("utf8")) : {}; } catch {}
  const prompt = String(payload.prompt || DEFAULT_PROMPT).slice(0, 5000);
  const common = {
    model: String(payload.model || DEFAULT_MODEL).slice(0, 80),
    prompt,
    num_predict: Math.max(32, Math.min(512, Number(payload.num_predict || DEFAULT_NUM_PREDICT))),
    timeout_ms: 240000,
    resident_url: RESIDENT_URL,
    intent: `race.${Date.now()}.${Math.random().toString(16).slice(2)}`
  };
  if (url.pathname === "/api/baseline") {
    const out = await runRemoteNode(baselineSource, common, 260000);
    json(res, out.ok ? 200 : 500, out);
    return;
  }
  if (url.pathname === "/api/mercury") {
    const out = await runRemoteNode(mercurySource, common, 60000);
    json(res, out.ok ? 200 : 500, out);
    return;
  }
  json(res, 404, { ok: false, error: "not found" });
}

const server = createServer(async (req, res) => {
  try {
    const url = requestUrl(req);
    if (req.method === "GET" && url.pathname === "/") {
      const html = pageHtml();
      res.writeHead(200, { "content-type": "text/html; charset=utf-8", "content-length": Buffer.byteLength(html) });
      res.end(html);
      return;
    }
    if (req.method === "GET" && url.pathname === "/api/config") {
      json(res, 200, {
        ok: true,
        model: DEFAULT_MODEL,
        num_predict: DEFAULT_NUM_PREDICT,
        key_required_for_remote: true,
        local_request: isLocalRequest(req)
      });
      return;
    }
    if (req.method === "GET" && url.pathname === "/api/models") {
      if (!authorized(req)) {
        json(res, 401, { ok: false, error: "access key required" });
        return;
      }
      const out = await runRemoteNode(modelsSource, { model: DEFAULT_MODEL }, 15000);
      const models = Array.from(new Set([...(out.models || []), DEFAULT_MODEL].filter(Boolean)));
      json(res, out.ok ? 200 : 500, { ...out, models });
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/activate") {
      if (!authorized(req)) {
        json(res, 401, { ok: false, error: "access key required" });
        return;
      }
      const out = await runRemoteShell(activateShell, 180000);
      json(res, out.ok ? 200 : 500, out);
      return;
    }
    if (req.method === "POST" && (url.pathname === "/api/baseline" || url.pathname === "/api/mercury")) {
      await handleApi(req, res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/recording") {
      if (!authorized(req)) {
        json(res, 401, { ok: false, error: "access key required" });
        return;
      }
      const body = await readBody(req, 80 * 1024 * 1024);
      const name = `local-model-race-${new Date().toISOString().replace(/[-:]/g, "").replace(/\\.\\d+Z$/, "Z")}.webm`;
      const path = join(RECORDING_DIR, name);
      writeFileSync(path, body);
      json(res, 200, { ok: true, path, url: `/recordings/${name}`, bytes: body.length });
      return;
    }
    if (req.method === "GET" && url.pathname.startsWith("/recordings/")) {
      if (!authorized(req)) {
        json(res, 401, { ok: false, error: "access key required" });
        return;
      }
      const name = decodeURIComponent(url.pathname.replace(/^\/recordings\//, ""));
      const path = join(RECORDING_DIR, name.replace(/[\/\\]/g, ""));
      const { readFileSync, existsSync } = await import("node:fs");
      if (!existsSync(path)) {
        json(res, 404, { ok: false, error: "recording not found" });
        return;
      }
      const data = readFileSync(path);
      res.writeHead(200, { "content-type": "video/webm", "content-length": data.length });
      res.end(data);
      return;
    }
    json(res, 404, { ok: false, error: "not found" });
  } catch (error) {
    json(res, 500, { ok: false, error: error.message });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Neuron Mercury local model race recorder`);
  console.log(`url: http://${HOST}:${PORT}/`);
  console.log(`access_key: ${ACCESS_KEY}`);
  console.log(`remote: ${REMOTE}`);
  console.log(`model: ${DEFAULT_MODEL}`);
});
