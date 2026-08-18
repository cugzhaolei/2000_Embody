const socket = io();
const terminal = document.getElementById("terminal");
const cardsDiv = document.getElementById("cards");
const termTitle = document.getElementById("termTitle");
let runningId = null;

function clearTerminal() {
  terminal.innerHTML = "";
}

function classify(line) {
  if (/整体结果:\s*PASS/.test(line))          return "line-pass";
  if (/整体结果:\s*FAIL/.test(line))          return "line-fail";
  if (/模块状态/.test(line))                  return "line-header";
  if (/已清理|已停止|已启动/.test(line))        return "line-info";
  if (/断言|场景/.test(line))                  return "line-info";
  if (/话题.*正常/.test(line))                 return "line-result";
  if (/服务.*已就绪/.test(line))               return "line-result";
  if (/action.*已注册/.test(line))             return "line-result";
  if (/参数节点.*my_parameter/.test(line))     return "line-result";
  if (/停录完成/.test(line))                   return "line-result";
  if (/录制中/.test(line))                     return "line-info";
  if (/正在运行|命令:/.test(line))             return "line-launch";
  if (/❌|FAIL|异常/.test(line))              return "line-fail";
  if (/=====/.test(line))                      return "line-header";
  if (/^\s*•/.test(line))                      return "line-info";
  if (/\[INFO\]/.test(line))                   return "line-dim";
  return "line";
}

function appendLine(text) {
  const cls = classify(text);
  const div = document.createElement("div");
  div.className = cls;
  div.textContent = text;
  terminal.appendChild(div);
  terminal.scrollTop = terminal.scrollHeight;
}

function setStatus(id, status) {
  const card = document.getElementById("card-" + id);
  if (!card) return;
  card.className = "card " + status;
  const badge = card.querySelector(".badge");
  const btn = card.querySelector(".btn-run");
  const labels = { idle: "就绪", running: "运行中...", success: "PASS", fail: "FAIL" };
  const classes = { idle: "idle", running: "running", success: "success", fail: "fail" };
  badge.textContent = labels[status];
  badge.className = "badge " + classes[status];
  btn.disabled = status === "running";
}

function runScenario(id, file, name) {
  if (runningId) return;
  runningId = id;
  setStatus(id, "running");
  termTitle.textContent = name + " — 终端输出";
  clearTerminal();
  socket.emit("run", { file });
}

socket.on("output", (data) => appendLine(data.line));

socket.on("done", (data) => {
  if (runningId) setStatus(runningId, data.rc === 0 ? "success" : "fail");
  appendLine("");
  appendLine(data.rc === 0 ? "✅ 执行完毕" : "❌ 执行失败 (rc=" + data.rc + ")");
  runningId = null;
});

async function init() {
  const resp = await fetch("/api/scenarios");
  const scenarios = await resp.json();
  scenarios.forEach((s) => {
    const card = document.createElement("div");
    card.className = "card";
    card.id = "card-" + s.id;
    card.innerHTML = `
      <div class="top">
        <span class="icon">${s.icon}</span>
        <span class="name">${s.name}</span>
        <span class="badge idle">就绪</span>
      </div>
      <div class="desc">${s.desc}</div>
      <button class="btn-run" onclick="runScenario('${s.id}','${s.file}','${s.name}')">
        ▶ 运行
      </button>`;
    cardsDiv.appendChild(card);
  });
}

init();
