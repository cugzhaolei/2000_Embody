# DeepSeek Harness 底层原理图解（时序图 + 流程图）

> 基于 `deepseek-harness-master` 源码精读。所有图均为 Mermaid 语法，可直接在 GitHub / Typora / 支持 Mermaid 的编辑器渲染。
> 图例：参与者即真实模块；消息即真实方法/事件名（与源码一致）。

---

## 图 1（时序图）：一次对话 turn 的完整旅程 —— 从输入到落盘

这是全系统最核心的一条链路：`ReactLoopAgent.turn()/step()` 驱动一轮对话。

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户/UI
    participant A as Agent<br/>(ReactLoopAgent)
    participant I as Inbox<br/>(持久化收件箱)
    participant S as Session Log<br/>(事件溯源账本)
    participant P as SystemPrompt<br/>(点菜员)
    participant L as LlmRuntime<br/>(ctx.llm)
    participant AD as LlmAdapter<br/>(DeepSeek 等)
    participant T as ToolRuntime<br/>(ctx.tools)
    participant TB as 工具实现
    participant PERS as Persistence<br/>(write-behind)

    U->>A: followup(message)
    A->>I: splice('next-turn', …, [message])
    I->>S: append('agent/inbox/spliced')  // 收件箱变更也入账
    A->>I: wakeDriver() → 开驱动循环

    Note over A,S: —— turn()：开一轮 ——
    A->>S: append('turn/start', {turn})
    A->>I: claim('next-turn', turn)   // 取出待处理消息

    Note over A,P: —— preStep()：组装提示词 ——
    A->>P: assemble({agent, signal})
    P-->>A: PromptAssembly{sections, tools, variables}
    A->>S: append('user/message', {…}, surfaceOp:'append')

    Note over A,L: —— step()：构造并发出模型请求 ——
    A->>S: deriveMessages()   // 从账本“算出”历史
    S-->>A: Message[]
    A->>L: prepareCall(config, signal)
    L-->>A: PreparedLlmCall{config, retryPolicy, stream()}
    A->>S: append('request/header', {header, reason})

    A->>L: stream(request)   // 经 llm/stream waterfall
    L->>AD: adapter.stream(options)
    loop 流式响应
        AD-->>A: chunk
        A->>S: append('assistant/chunk', {chunk})  // 逐字入账，回放保真
    end
    A->>S: append('assistant/message', {message, usage})

    alt 模型请求了工具调用
        A->>T: executeToolCalls(toolCalls, turn, step, signal)
        loop 每个 tool-call
            T->>S: append('tool/call', {callId, name, arguments})
            Note over T,TB: —— 五段式执行管线 ——
            T->>T: tools/pre-execute waterfall (allow/deny/ask)
            T->>T: guard 检查（单调守卫）
            T->>T: tools/execute waterfall (timeout 包装等)
            T->>TB: execute(args, exec)   // 工具本体
            TB-->>T: canonical value
            T->>T: tools/post-execute waterfall (接受/替换/block)
            T->>S: append('tool/result', {message, error?, meta?})
        end
        A->>A: 工具还欠请求 → 下一 step；否则收尾
    end

    A->>S: append('turn/end', {turn, reason})
    Note over A,PERS: 每次模型请求前 / 工具副作用前强制冲刷
    PERS->>PERS: session/flush → write-behind 立即落盘
```

**关键点**：
- 编号 3、5、10、15、19、24 都是**写账本**——"模型可见 ⟺ 已记录"铁律的体现；
- `request/header` 是"请求快照"（provider/model/工具列表），模型历史完全由 `deriveMessages()` 从账本折叠出来；
- `assistant/chunk` 逐字入账，保证 UI 重放与真实输出一字不差；
- 工具结果按模型顺序提交（结果保序、执行可重叠），取消时为未启动的调用补写合成结果。

---

## 图 2（时序图）：子代理委派 —— 一个 Agent 生出一个 Agent

前台一次性委派（`subagent` 工具 → `spawn` provider 的完整时序）。

```mermaid
sequenceDiagram
    autonumber
    participant P as 父 Agent
    participant TS as subagent 工具
    participant SR as SubagentRuntime<br/>(ctx.subagents)
    participant PR as Provider (spawn)
    participant CR as ctx.agents<br/>(AgentRegistry)
    participant CA as 子 Agent<br/>(同一 agent-loop)
    participant CS as 子 Session Log

    P->>TS: execute(args)   // 模型调用 subagent 工具
    TS->>SR: start('spawn', {prompt, parent, signal})
    SR->>PR: provider.start(request)
    PR->>CR: create({meta:{parentSession, delegationDepth+1}, setup})
    CR->>CS: append('session/end-seed')  // 全新会话，无父历史
    CR-->>PR: AgentHandle
    PR->>CA: followup(prompt)
    CA->>CS: append('turn/start' → … 正常循环 …)
    CA-->>PR: whenIdle()  → 子代理跑完
    PR-->>SR: SubagentResult{output, stopReason}
    SR-->>TS: run.result
    TS-->>P: tool/result（子代理的最终答复）
    P->>P: dispose()  // 必须释放子代理
```

**关键点**：
- 子代理**复用同一条 agent-loop**——`create()` 的 setup 钩子里装配 persona/工具过滤/结构化输出，发布时序与主 agent 完全一致；
- `parentSession` + `delegationDepth`（父深度+1）写入 SessionHeader，形成可持久化的血缘树；`fork` provider 则用父会话已完成前缀做 seed；
- 可续子代理（continuable）走 `startContinuable`：父用 `send_message` 续发、`interrupt_agent` 只停当前轮，冷恢复直接从持久化 Session + 折叠描述符重建，**不经过 Provider**。

---

## 图 3（流程图）：dsh 启动 —— 五层 patch 组合成插件树

从命令到运行中的 Web UI。

```mermaid
flowchart TD
    CLI["dsh --profile web --port 8080"] --> ARGS["apps/cli/src/args.ts<br/>commander 切分<br/>launcher flag | app 参数"]
    ARGS --> PB["profile-boot.ts → runProfile()"]
    PB --> ENV["loadLayeredEnv<br/>继承环境 > 项目 .env > $DSH_HOME/.env"]
    ENV --> COMP["composeProfile：五层 patch 叠加"]
    COMP --> L1["① bundle 层<br/>(dsh.profile.bundles 顺序：base → web-app)"]
    COMP --> L2["② profile 层<br/>profiles/web/cordis.patch.yml"]
    COMP --> L3["③ home 层<br/>$DSH_HOME/cordis.patch.yml"]
    COMP --> L4["④ --patch overlays"]
    COMP --> L5["⑤ launcher 派生层<br/>agent-presets / telemetry 开关"]
    L1 & L2 & L3 & L4 & L5 --> FLAT["flatten 成一次<br/>applyEntryPatches([], layers)<br/>打空根"]
    FLAT --> BOOT["boot('dsh', cordis.yml, patches)"]
    BOOT --> ROOT["new Context + provide('dshHomePath')"]
    ROOT --> LOADER["ctx.plugin(Loader) + prepare 钩子<br/>provideCmdline / launch-environment"]
    LOADER --> INCLUDE["mountRootInclude<br/>cordis:include 根 entry (id='include')"]
    INCLUDE --> AWAIT["loader.await() → assertEntriesActivated"]
    AWAIT --> TREE["插件树激活：llm/session/tools/agent-loop/…<br/>≈100 行 base 插件"]
    TREE --> WS["web-startup 解析 --port (!!js 延迟求值)"]
    WS --> WEB["webserver 127.0.0.1:3080"]
    WEB --> FSS["frontend-static 服务 dist<br/>+ tapIndex 注入 __DSH_BOOT__"]
    WEB --> UI["浏览器加载 AppWebEntry → Web UI"]

    style FLAT fill:#fff3cd,stroke:#d4a017
    style INCLUDE fill:#d4edda,stroke:#28a745
    style WEB fill:#cce5ff,stroke:#0d6efd
```

**关键点**：
- **一次 `applyEntryPatches`** 保证 `--dump-config`、flag 推导与真实 boot **同源不漂移**；
- patch 按 id **整段替换 config**（非深合并）、同 id 后写胜出；`insert` 行按引用推入结果树，故每代应用前必须 `structuredClone`；
- `!!js` YAML 方言在**该行声明的 injections 激活后**才求值——所以 `webserver` 行能直接读 `ctx.webStartup.port`，flag 永远压过写死的默认值。

---

## 图 4（流程图）：工具执行五段式管线

一次 `tool/call` 从模型到结果的全部阶段与可插入点。

```mermaid
flowchart TD
    TC["模型发出 tool/call<br/>(name + 原始 arguments JSON)"] --> S["写账本 tool/call"]
    S --> P1["tools/pre-execute waterfall<br/>(可插入：审批/策略)"]
    P1 --> DEC{决策}
    DEC -->|allow| G["guard 单调守卫<br/>(任一返回 reason 即拒绝)"]
    DEC -->|ask| ASK["ctx.approval.request()<br/>→ UI 人工审批"]
    ASK -->|allowed-once| G
    ASK -->|rejected/cancelled| DENY
    DEC -->|deny| DENY["materialize 结构化错误结果"]
    G -->|通过| P2["tools/execute waterfall<br/>(可插入：timeout-policy / retry)"]
    P2 --> BODY["工具本体 execute(args, exec)<br/>观察 exec.signal（协作取消）"]
    BODY -->|value| P3["tools/post-execute waterfall<br/>(接受/替换内容/附加上下文/block)"]
    P3 --> OUT["output.schema 校验 canonical 值"]
    OUT --> R["写账本 tool/result"]
    R --> N["tools/result emit<br/>(冻结结果通知 UI/遥测)"]
    N --> NEXT["结果进入模型历史 → 下一 step 或收尾"]

    style P1 fill:#fff3cd,stroke:#d4a017
    style P2 fill:#fff3cd,stroke:#d4a017
    style P3 fill:#fff3cd,stroke:#d4a017
```

**关键点**：
- `tools/pre-execute`（决策）、`tools/execute`（around 包装）、`tools/post-execute`（结果改写）是**三个 waterfall**——监听者必须 `next()` 委托，否则短路；
- 所有失败都归一化为结构化结果（`message + code`），模型可读可自纠（如 `UNKNOWN_TOOL`/`TOOL_TIMEOUT`/`FS_STALE_VERSION`）；
- `timeout-policy` 通过临时替换 `exec.signal` 实现协作式超时；审批 `ask` 只在工具调用挂起期间等真人。

---

## 图 5（流程图）：会话日志 —— 一本账，四家读

事件溯源生态：所有下游都从同一本账派生，彼此不共享可变状态。

```mermaid
flowchart LR
    APP["Session.append(event)<br/>冻结 → 入 log → 派发 session/event"] --> FAN["session/event 广播"]
    FAN --> DERIVE["deriveMessages()<br/>surface 折叠 → LLM 历史"]
    FAN --> PERS["Persistence write-behind<br/>200ms 批窗口 + flush 屏障<br/>→ JSONL/SQLite"]
    FAN --> PROJ["Projection 投影单元<br/>eager 折叠 → stats/title/权限"]
    FAN --> TELE["Telemetry 采样<br/>深拷贝 → 脱敏 → OTLP"]
    FAN --> UI["前端渲染<br/>Session 事件窗口 → UI 组件"]

    DERIVE --> REQ["模型请求（只读账本）"]
    PERS --> RESTORE["崩溃恢复 load()<br/>截断 torn 尾 + 合成闭包"]
    PROJ --> CACHE["投影缓存<br/>storage-domain 落盘"]
    TELE --> EXPORT["OTLP/HTTP logs"]
    UI --> VIEW["会话树/轨迹/工具卡片"]

    style APP fill:#d4edda,stroke:#28a745
    style DERIVE fill:#cce5ff,stroke:#0d6efd
    style PERS fill:#cce5ff,stroke:#0d6efd
```

**关键点**：
- 持久化、UI、遥测、投影**互不阻塞**——append 是同步入 log + fire-and-forget 通知；
- 压缩（compaction）通过 `surfaceOp:{op:'replace',start,end}` **盖纸条**遮蔽旧节点而非删除，`sourceEventSeqs` 保留可恢复性；
- SQLite 后端：每事件一行（`data` 为 JSON 原文），`SCHEMA_VERSION=15` + `application_id=0x44534850`，崩溃后 `load()` 找最后 `turn/end` 判撕裂点，自动补齐中断回合。

---

## 图 6（流程图）：能力接缝 —— 三脚插座的实例

以文件系统为例，展示 Definition / Provider / Consumer 如何让"换实现 = 换行为"。

```mermaid
flowchart TB
    DEF["Service Definition<br/>fs/fs：抽象 FileSystem<br/>12 原语 + fs/* 事件词表<br/>ctx.fs"]
    DEF --> P1["Provider：fs-local<br/>本地 realpath + 原子写"]
    DEF --> P2["Provider：fs-sandbox<br/>继承 local + 策略围栏"]
    DEF --> P3["Provider：e2b/fs-e2b<br/>云端沙箱 Filesystem API"]
    DEF --> CON1["Consumer：tool-fs<br/>read/write/edit/read_image"]
    DEF --> CON2["Consumer：str_replace_editor"]
    DEF --> POL["纯事件策略<br/>fs-observation-policy<br/>(不注入服务，只听 fs/* 事件)"]

    P1 -.互斥替换.-> DEF
    P2 -.互斥替换.-> DEF
    P3 -.互斥替换.-> DEF
    POL -. read-before-write 门.-> CON1

    style DEF fill:#fff3cd,stroke:#d4a017
    style P1 fill:#d4edda,stroke:#28a745
    style P2 fill:#d4edda,stroke:#28a745
    style P3 fill:#d4edda,stroke:#28a745
```

**关键点**：
- 一个 context 只允许一个 Provider 实现（装载第二个报重复服务）；
- `fs-observation-policy` 不注册服务、只通过 `fs/write-intent`/`fs/edit-intent`/`fs/observed` 事件参与——卸载它只丢策略，工具仍可用裸 Provider（策略与能力正交组合）；
- 换 Provider（本地→沙箱→E2B）时，`tool-fs`、`bash-local`、`terminal-bash`、`lsp-stdio` 全部零改动——这就是"一套执行世界"。

---

*图源：`packages/core/{agent-loop,agent,session,tools}`、`packages/fs/*`、`packages/boot/app-boot`、`packages/subagent/*` 源码精读。*
