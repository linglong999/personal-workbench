(function () {
  "use strict";

  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ───────── MOCK / LIVE 运行模式 ─────────
     MOCK：内置假数据（离线可演示，默认）
     LIVE：fetch 本地 Bridge（127.0.0.1:8213）真实调用 workbench 的 5 个 MCP 工具 */
  var API_BASE = "http://127.0.0.1:8213/api";
  var MODE_KEY = "wb-mode";
  var MODE = "mock";
  try { MODE = localStorage.getItem(MODE_KEY) || "mock"; } catch (e) { /* 隐私模式无 localStorage */ }
  var bridgeWarned = false;

  function api(path, body) {
    return fetch(API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  function bridgeDown() {
    if (bridgeWarned) return;
    bridgeWarned = true;
    toast("⚠ 连不上 Bridge —— 请在 workbench/ 目录启动：<span class='mono'>uvicorn workbench.bridge:app --port 8213</span>");
    setTimeout(function () { bridgeWarned = false; }, 8000);
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  /* classify_text 的真实标签（输入/决策/实践/复盘/创造）→ 归位建议 */
  function ruleFor(label) {
    var map = {
      "输入": "归入收件箱", "决策": "进入决策备忘", "实践": "放入项目 · 行动",
      "复盘": "生成今日复盘", "创造": "沉淀为知识卡片"
    };
    return map[label] || "归入收件箱";
  }
  /* 分类标签 → vault 白名单目录（写入用） */
  function folderFor(label) {
    return {
      "输入": "问题整理", "决策": "决策备忘", "实践": "行动记录",
      "复盘": "复盘沉淀", "创造": "知识卡片"
    }[label] || "问题整理";
  }

  var modeChip = $("#modeChip");
  function applyMode() {
    if (!modeChip) return;
    modeChip.textContent = MODE === "live" ? "LIVE" : "MOCK";
    modeChip.classList.toggle("is-live", MODE === "live");
    var liveSearch = $("#liveSearch"), searchEmpty = $("#searchEmpty");
    if (liveSearch && searchEmpty) {
      liveSearch.hidden = MODE !== "live";
      searchEmpty.hidden = MODE === "live";
    }
    /* 稍后再看是演示假数据：LIVE（自己真实使用）时整条隐藏，避免干扰 */
    var watchBand = document.querySelector(".watch-band");
    if (watchBand) { watchBand.hidden = (MODE === "live"); }
  }
  if (modeChip) {
    modeChip.addEventListener("click", function () {
      MODE = MODE === "live" ? "mock" : "live";
      try { localStorage.setItem(MODE_KEY, MODE); } catch (e) {}
      applyMode();
      toast(MODE === "live"
        ? "已切换到 LIVE · 真实调用本地 Bridge (:8213)"
        : "已切换到 MOCK · 使用内置演示数据");
      if (MODE === "live") {
        var active = $(".nav-item.is-active");
        if (active) {
          if (active.dataset.view === "today") liveToday();
          else if (active.dataset.view === "projects") liveProjects();
          else if (active.dataset.view === "tags") liveTags();
          else if (active.dataset.view === "usage") renderUsage();
        }
      }
    });
  }
  applyMode();

  /* ───────── 收件箱数据（假数据）───────── */
  var inboxData = [
    { kind: "想法", cls: "kind-idea", txt: "把「确认型 Agent」写成一篇对外讲的简洁说明", conf: "高置信度 · 已就位" },
    { kind: "任务", cls: "kind-task", txt: "给开源项目补一个 LICENSE", conf: "高置信度 · 已就位" },
    { kind: "问题", cls: "kind-q",    txt: "这条该归到「复盘」还是「知识」？", conf: "低置信度 · AI 请你定夺" }
  ];
  var inboxEl = $("#inboxList");
  if (inboxEl) {
    inboxData.forEach(function (it) {
      var li = document.createElement("li");
      li.className = "inbox-item";
      li.innerHTML =
        '<span class="inbox-kind ' + it.cls + '">' + it.kind + "</span>" +
        '<span class="inbox-txt">' + it.txt + "</span>" +
        '<span class="inbox-conf"><b>✦</b> ' + it.conf + "</span>";
      inboxEl.appendChild(li);
    });
  }

  /* ───────── 标签浏览（MOCK 演示 / LIVE 真实聚合）─────────
     统一数据形状：{tag: [{title, obsidian_uri}]}，uri 存在则点击直开 Obsidian。 */
  function C(t) { return { title: t }; }
  var mockTags = {
    "RAG": ["GraphRAG", "RAG六步流水线", "RAG检索与生成", "混合检索与重排序", "向量化", "Embedding"].map(C),
    "Prompt工程": ["Prompt六要素", "角色设定三层结构", "SystemPrompt与UserPrompt", "Few-shot", "CRISPE框架", "肯定指令与否定指令"].map(C),
    "AgentWorkflow": ["Agent框架全景", "Agent四种模式", "LangGraph图抽象", "链式调用Chain", "子智能体Subagent", "编排vsAgent"].map(C),
    "思维模型": ["第一性原理", "金字塔原理", "MECE原则", "逆向思维", "六顶思考帽", "二八法则", "STAR法则"].map(C)
  };
  var tagCloud = $("#tagCloud"), tagCardList = $("#tagCardList");

  function renderTags(tags) {
    if (!tagCloud) return;
    tagCloud.innerHTML = "";
    Object.keys(tags).sort().forEach(function (tag) {
      var cards = tags[tag];
      var c = document.createElement("button");
      c.className = "tag tag-blue";
      c.setAttribute("data-tag", tag);
      c.title = cards.map(function (x) { return x.title; }).join("、");
      c.innerHTML = "#" + esc(tag) + " <span class='tag-count'>" + cards.length + "</span>";
      c.addEventListener("click", function () {
        renderTagCards(tag, cards);
      });
      tagCloud.appendChild(c);
    });
  }
  /* ───────── 统一交互：点任何知识实体 ─────────
     有 obsidian_uri → 唤起 Obsidian 打开原笔记；无 uri（MOCK）→ 提示切 LIVE。
     嵌入式预览浏览器会静默拦截外部协议，toast 始终附带路径与出路。 */
  function openNote(item, absPath) {
    if (item && item.obsidian_uri) {
      var a = document.createElement("a");
      a.href = item.obsidian_uri;
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast("已请求 Obsidian 打开 · 若无反应，你在嵌入式预览里 ——" +
        "用 Chrome/Edge 打开 <b>http://127.0.0.1:8212</b> 可直连" +
        (absPath ? " · 文件 <span class='mono'>" + esc(absPath) + "</span>" : ""), 5200);
      return true;
    }
    if (MODE !== "live") {
      toast("真实打开需要 <b>LIVE</b> 模式 —— 点输入条右侧的 MOCK 切换");
      return false;
    }
    return false;
  }
  function searchFor(text) {
    if (MODE !== "live") {
      toast("真实检索需要 <b>LIVE</b> 模式 —— 点输入条右侧的 MOCK 切换");
      return false;
    }
    var navSearch = document.querySelector('.nav-item[data-view="search"]');
    if (navSearch) navSearch.click();
    if (srInput) { srInput.value = text; runSearch(); }
    return true;
  }

  function renderTagCards(tag, cards) {
    if (!tagCardList) return;
    tagCardList.hidden = false;
    tagCardList.innerHTML = "";
    cards.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "tag-card-item";
      li.innerHTML = "<b>" + esc(item.title) + "</b><span class='mono'>↗ Obsidian</span>";
      li.addEventListener("click", function () {
        if (!openNote(item, item.path)) searchFor(item.title);
      });
      tagCardList.appendChild(li);
    });
  }
  function liveTags() {
    api("/list_tags").then(function (d) {
      renderTags(d.tags || {});
    }).catch(function () {
      renderTags(mockTags);
      bridgeDown();
    });
  }

  /* ───────── 侧栏折叠（Trae 风格：点击显示/隐藏 + Ctrl+B）───────── */
  var appEl = $(".app");
  var sideRail = $("#sideRail");
  var sideToggle = $("#sideToggle");
  var railExpand = $("#railExpand");
  function setSide(show) {
    appEl.classList.toggle("side-hidden", !show);
    sideRail.hidden = show;
    sideToggle.setAttribute("aria-pressed", show ? "false" : "true");
    sideToggle.title = show ? "收起侧栏 (Ctrl/⌘+B)" : "展开侧栏 (Ctrl/⌘+B)";
  }
  function toggleSide() { setSide(appEl.classList.contains("side-hidden")); }
  sideToggle.addEventListener("click", toggleSide);
  railExpand.addEventListener("click", function () { setSide(true); });
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
      e.preventDefault(); toggleSide();
    }
  });

  /* ───────── 视图切换 ───────── */
  var navItems = $$(".nav-item");
  var views = $$(".view");
  function showView(name) {
    navItems.forEach(function (n) { n.classList.toggle("is-active", n.dataset.view === name); });
    views.forEach(function (v) { v.hidden = (v.id !== "view-" + name); });
    if (name === "tags") {
      if (MODE === "live") liveTags(); else renderTags(mockTags);
      return;
    }
    if (name === "usage") { renderUsage(); return; }
    if (MODE === "live") {
      if (name === "today") liveToday();
      else if (name === "projects") liveProjects();
    }
  }
  navItems.forEach(function (n) {
    n.addEventListener("click", function () { showView(n.dataset.view); });
  });

  /* ───────── LIVE 接线：经验回流（reopen_task）─────────
     切到「今天」视图时，用第一条任务真实召回历史经验，回填洞察卡。 */
  function liveToday() {
    var t = $("#view-today .task b");
    if (!t) return;
    api("/reopen_task", { task: t.textContent, top_k: 3 }).then(function (d) {
      var rs = d.results || [];
      var p = $("#view-today .ai-insight p");
      if (!p) return;
      if (!rs.length) {
        p.textContent = "知识库里还没有与该任务相关的历史经验 —— 做完这单，它会替你记下来。";
        return;
      }
      p.innerHTML = "与「" + esc(t.textContent) + "」最相关的过往经验（真实检索）：<b>" +
        rs.map(function (r) { return esc(r.title || r.id || ""); }).join(" · ") + "</b>";
    }).catch(bridgeDown);
  }

  /* ───────── LIVE 接线：决策闭环（scan_decision_closed_loop）─────────
     切到「项目」视图时，真实扫描决策备忘，回填闭环提示卡。 */
  function liveProjects() {
    api("/scan_decision_closed_loop").then(function (d) {
      var miss = d.missing || [];
      var p = $("#view-projects .ai-insight p");
      if (!p) return;
      if (!miss.length) {
        p.textContent = "真实扫描：决策闭环完整，所有决策均已关联问题 ✓";
        return;
      }
      p.innerHTML = "<b>真实扫描</b>：" + miss.map(esc).join("；") + " —— 建议补关联形成闭环。";
    }).catch(bridgeDown);
  }

  /* ───────── 全局输入：AI 识别提示（隐形式 AI 的关键演示）───────── */
  var capture = $("#capture");
  var captureHint = $("#captureHint");
  var debounceTimer;
  var lastLabel = "";      /* 最近一次分类结果，Enter 写入时用 */
  function mockRule(v) {
    if (/(复盘|总结|回顾)/.test(v)) { return { type: "复盘", rule: "生成今日复盘" }; }
    if (/(任务|做完|搞定|安排)/.test(v)) { return { type: "任务", rule: "放入项目 · 行动" }; }
    if (/(决策|决定|要不要|该不该)/.test(v)) { return { type: "决策", rule: "进入决策备忘" }; }
    return { type: "想法", rule: "归入收件箱" };
  }
  function showHint(type, rule, live) {
    lastLabel = type;
    captureHint.hidden = false;
    captureHint.innerHTML =
      '<b>✦ AI 识别为「' + type + '」' + (live ? ' <span class="mono" style="font-size:.75em;opacity:.75">· 真实 LLM</span>' : "") + '</b> · 建议' + rule +
      ' <button class="btn btn-mini" style="margin-left:8px">确认归位</button> <span style="opacity:.7">· 可改</span>';
  }
  capture.addEventListener("input", function () {
    var v = capture.value.trim();
    lastLabel = "";   /* 换了输入内容，旧分类作废，提交时重新分类 */
    if (!v) { captureHint.hidden = true; return; }
    if (MODE !== "live") {
      var m = mockRule(v);
      showHint(m.type, m.rule, false);
      return;
    }
    /* LIVE：防抖后走 Bridge 真实分类（classify_text） */
    captureHint.hidden = false;
    captureHint.innerHTML = "<b>✦ AI 识别中…</b>";
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      api("/classify_text", { text: v }).then(function (d) {
        var label = (d.label || "").trim();
        var m = mockRule(v);
        if (label) { showHint(label, ruleFor(label), true); }
        else { showHint(m.type, m.rule, false); }
      }).catch(function () {
        var m = mockRule(v);
        showHint(m.type, m.rule, false);
        bridgeDown();
      });
    }, 600);
  });
  var committing = false;   /* 写入中防抖：双击/回车连按不重复落盘 */
  function commitCapture() {
    if (committing || !capture.value.trim()) return;
    var v = capture.value.trim();
    if (MODE !== "live") {
      toast("已接住，AI 自动归位为「想法」到收件箱 [撤销]");
      capture.value = ""; captureHint.hidden = true;
      return;
    }
    /* LIVE：真实写入 vault —— 未分类过则先分类再落盘 */
    captureHint.hidden = true;
    var done = function () { committing = false; };
    var write = function (label) {
      var folder = folderFor(label);
      var d0 = new Date();
      var today = d0.getFullYear() + "-" + String(d0.getMonth() + 1).padStart(2, "0") + "-" + String(d0.getDate()).padStart(2, "0");
      var title = v.replace(/[\\/:*?"<>|#\[\]]/g, "-").slice(0, 24);
      var content = "---\ntype: " + label + "\nsource: console-input\ndate: " + today + "\n---\n\n" + v;
      committing = true;
      api("/create_note", { folder: folder, title: title, content: content }).then(function (d) {
        var fn = (d.path || "").split(/[\\/]/).pop();
        toast("已存入 vault ·「" + folder + "」/ " + esc(fn) +
          (d.obsidian_uri ? ' · <a href="' + d.obsidian_uri + '">在 Obsidian 打开 ↗</a>' : ""));
        capture.value = "";
        done();
      }).catch(function () {
        toast("写入失败：Bridge 未启动，内容未保存（仍在输入框）");
        bridgeDown();
        done();
      });
    };
    if (lastLabel && lastLabel !== "任务" && lastLabel !== "想法") { write(lastLabel); }
    else {
      committing = true;
      api("/classify_text", { text: v }).then(function (d) {
        done();
        write((d.label || "").trim() || "输入");
      }).catch(function () { done(); write("输入"); bridgeDown(); });
    }
  }
  capture.addEventListener("keydown", function (e) {
    if (e.key === "Enter") commitCapture();
  });
  captureHint.addEventListener("click", function (e) {
    if (e.target.tagName === "BUTTON") commitCapture();
  });

  /* ───────── 稍后再看 · 流动卡片 ───────── */
  var watchList = [
    { url: "https://www.bilibili.com",   title: "B 站知识区 · AI 全栈导论",      site: "bilibili.com" },
    { url: "https://www.youtube.com",    title: "Y Combinator · How to Build an AI", site: "youtube.com" },
    { url: "https://sspai.com",          title: "少数派 · 个人知识库搭建复盘",    site: "sspai.com" },
    { url: "https://zhihu.com",          title: "知乎 · 如何建立第二大脑",        site: "zhihu.com" },
    { url: "https://github.com",         title: "GitHub · agent 开源项目盘点",    site: "github.com" },
    { url: "https://mp.weixin.qq.com",   title: "公众号 · Prompt 工程实践指南",   site: "mp.weixin.qq.com" },
    { url: "https://www.zhihu.com/column", title: "知乎专栏 · AI Native 产品思考", site: "zhihu.com" },
    { url: "https://arxiv.org",          title: "Arxiv · RAG 综述",              site: "arxiv.org" }
  ];
  var track = $("#marqueeTrack");
  function letterOf(url) { try { return (new URL(url).hostname || "•")[0].toUpperCase(); } catch (e) { return "•"; } }
  function cardHTML(it) {
    /* 站点图标用本地字母头像，不依赖 Google favicon 服务（国内不可达、离线亦可） */
    return '<div class="wcard">' +
      '<span class="wcard-fav"><span class="fallback">' + letterOf(it.url) + '</span></span>' +
      '<span class="wcard-info"><span class="wcard-title">' + it.title + "</span>" +
      '<span class="wcard-site">' + it.site + "</span></span></div>";
  }
  var halves = watchList.map(cardHTML).join("");
  // 无缝循环：一份内容渲染两组（A+A），动画精度平移 -50%，首尾相接
  track.innerHTML = halves + halves;

  /* ───────── 右侧上下文面板：相关笔记 & AI 助手可交互 ───────── */
  $$(".ctx-links li").forEach(function (li) {
    var t = li.textContent.replace("↳", "").trim();
    li.addEventListener("click", function () { searchFor(t); });
  });
  var ctxAsk = $(".ctx-ask");
  if (ctxAsk) {
    ctxAsk.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && ctxAsk.value.trim()) {
        e.preventDefault();
        var q = ctxAsk.value.trim();
        if (searchFor(q)) { ctxAsk.value = ""; }   /* MOCK 下保留输入不丢内容 */
      }
    });
  }

  /* ───────── 知识视图卡片：点击 = 检索该卡片 ───────── */
  $$("#view-knowledge .kb-card").forEach(function (card) {
    var h = card.querySelector("h2, h3");
    if (!h) return;
    card.addEventListener("click", function () { searchFor(h.textContent.trim()); });
  });

  /* ───────── Toast ───────── */
  var toastEl = $("#toast");
  var toastTimer;
  function toast(msg, dur) {
    toastEl.innerHTML = msg;
    toastEl.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, dur || 2600);
  }

  /* ───────── 命令面板 (Ctrl/⌘+K) ───────── */
  var cmdModal = $("#cmdModal"), cmdInput = $("#cmdInput"), cmdList = $("#cmdList");
  var cmds = $$("#cmdList li");
  function openCmd() { cmdModal.hidden = false; cmdInput.value = ""; cmdInput.focus(); selCmd(0); }
  function closeCmd() { cmdModal.hidden = true; }
  function selCmd(i) {
    cmds.forEach(function (c, k) { c.classList.toggle("sel", k === i); });
  }
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openCmd(); }
  });
  $("#cmdK").addEventListener("click", openCmd);
  cmdModal.addEventListener("click", function (e) { if (e.target === cmdModal) closeCmd(); });
  cmds.forEach(function (c) {
    c.addEventListener("click", function () {
      closeCmd();
      var cmd = c.dataset.cmd;
      /* LIVE：决策检查走真实扫描（scan_decision_closed_loop） */
      if (cmd === "decision" && MODE === "live") {
        toast("决策检查中…（真实扫描决策备忘）");
        api("/scan_decision_closed_loop").then(function (d) {
          var miss = d.missing || [];
          toast(miss.length
            ? "决策检查（真实）：发现 " + miss.length + " 条缺关联 —— 已列入待确认"
            : "决策检查（真实）：闭环完整 ✓");
        }).catch(bridgeDown);
        return;
      }
      var map = {
        review:        "已生成今日复盘草稿 [撤销]",
        archive:       "已归档 1 条输入 [撤销]",
        decision:      "决策检查：发现 1 条缺关联，已列入待确认",
        tag:           "已为你自动打标签 · 3 条 [撤销]",
        knowledge:     "已沉淀「环境隔离预案」为知识卡片 [撤销]"
      };
      toast(map[cmd] || "完成");
    });
  });
  cmdInput.addEventListener("input", function () { selCmd(0); });
  cmdInput.addEventListener("keydown", function (e) {
    var idx = cmds.indexOf($(".sel", cmdList));
    if (e.key === "ArrowDown") { e.preventDefault(); selCmd(Math.min(idx + 1, cmds.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); selCmd(Math.max(idx - 1, 0)); }
    else if (e.key === "Enter") { cmds[idx].click(); }
    else if (e.key === "Escape") { closeCmd(); }
  });

  /* ───────── AI 待确认弹层 ───────── */
  var confirmBox = $("#confirmBox");
  $("#aiQueue").addEventListener("click", function () { confirmBox.hidden = false; });
  $("#confirmClose").addEventListener("click", function () { confirmBox.hidden = true; });
  confirmBox.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-mini")) {
      e.target.closest("li").style.opacity = "0.4";
      toast("已确认 · AI 继续 [撤销]");
    }
  });

  /* ───────── 复盘 → 知识 ───────── */
  var toKnow = $("#reviewToKnowledge");
  if (toKnow) {
    toKnow.addEventListener("click", function () {
      showView("knowledge");
      toast("已沉淀为知识卡片「环境隔离预案」 [撤销]");
    });
  }

  /* ───────── 添加稍后再看 ───────── */
  var watchAdd = $("#watchAdd");
  if (watchAdd) {
    watchAdd.addEventListener("click", function () {
      toast("粘贴链接，AI 会把它归入「稍后再看」 [撤销]");
    });
  }

  /* ───────── LIVE 接线：知识检索（search_knowledge）─────────
     检索视图在 LIVE 模式下可用：真实向量检索知识库并渲染结果。 */
  var srInput = $("#srInput"), srBtn = $("#srBtn"), srResults = $("#srResults");
  function runSearch() {
    var q = srInput.value.trim();
    if (!q) return;
    srResults.innerHTML = '<p class="sr-note">检索中…</p>';
    api("/search_knowledge", { query: q, top_k: 5 }).then(function (d) {
      var rs = d.results || [];
      if (!rs.length) {
        srResults.innerHTML = '<p class="sr-note">没有命中 —— 换个问法试试。</p>';
        return;
      }
      srResults.innerHTML = rs.map(function (r, i) {
          return '<article class="sr-item"><span class="sr-rank">' + (i + 1) + '</span><div>' +
            "<h3>" + esc(r.title || "未命名") + "</h3>" +
            "<p>" + esc((r.content || "").slice(0, 160)) + "</p></div>" +
            (r.obsidian_uri ? '<span class="sr-open" title="在 Obsidian 中打开">↗</span>' : "") +
            "</article>";
        }).join("");
        /* 点击整条结果 → 在 Obsidian 中打开原笔记 */
        var items = srResults.querySelectorAll(".sr-item");
        rs.forEach(function (r, i) {
          if (!r.obsidian_uri) return;
          items[i].addEventListener("click", function () { openNote(r, r.path); });
        });
      }).catch(function () {
        srResults.innerHTML = '<p class="sr-note">检索失败：Bridge 未启动。</p>';
        bridgeDown();
      });
  }
  if (srBtn) { srBtn.addEventListener("click", runSearch); }
  if (srInput) {
    srInput.addEventListener("keydown", function (e) { if (e.key === "Enter") runSearch(); });
  }

  /* ───────── LIVE 接线：用量观测（/api/usage，GET）─────────
     Bridge 记录每次工具调用与 LLM token，这里渲染汇总 + 明细时间线。 */
  var usageSummary = $("#usageSummary"), usageList = $("#usageList"), usageNote = $("#usageNote");

  function fmtCost(c) {
    if (!c) return "¥0";
    return c < 0.01 ? "¥" + c.toFixed(4) : "¥" + c.toFixed(2);
  }
  function fmtTokens(n) {
    if (n >= 10000) return (n / 1000).toFixed(1) + "k";
    return String(n);
  }
  function renderUsage() {
    if (!usageSummary) return;
    if (MODE !== "live") {
      usageSummary.innerHTML = "";
      usageList.innerHTML = "";
      usageNote.textContent = "用量观测基于 Bridge 的真实调用记录 —— 切到 LIVE 后，这里会显示每次调用、token 与成本。";
      return;
    }
    fetch(API_BASE + "/usage").then(function (r) { return r.json(); }).then(function (d) {
      var t = d.totals || {}, p = d.prices || {};
      usageSummary.innerHTML =
        '<div class="us-card"><b>' + (t.tool_calls || 0) + '</b><span>工具调用</span></div>' +
        '<div class="us-card"><b>' + (t.llm_calls || 0) + '</b><span>LLM 调用</span></div>' +
        '<div class="us-card"><b>' + fmtTokens(t.prompt_tokens || 0) + '</b><span>输入 tokens</span></div>' +
        '<div class="us-card"><b>' + fmtTokens(t.completion_tokens || 0) + '</b><span>输出 tokens</span></div>' +
        '<div class="us-card us-cost"><b>' + fmtCost(t.cost || 0) + '</b><span>成本估算</span></div>';
      var evs = d.events || [];
      if (!evs.length) {
        usageList.innerHTML = "";
        usageNote.textContent = "还没有调用记录 —— 去输入条打个字、或切到「今天 / 检索」试一次，回来这里看数据。";
        return;
      }
      usageList.innerHTML = evs.map(function (e) {
        var isTool = e.kind === "tool";
        return '<li class="usage-item">' +
          '<span class="ui-ts mono">' + esc(e.ts) + '</span>' +
          '<span class="ui-kind ' + (isTool ? "ui-tool" : "ui-llm") + '">' + (isTool ? "工具" : "LLM") + '</span>' +
          '<span class="ui-name mono">' + esc(e.name) + '</span>' +
          '<span class="ui-detail">' + esc(e.detail || "") + '</span>' +
          '<span class="ui-tk mono">' + (e.pt || e.ct ? "↑" + fmtTokens(e.pt || 0) + " ↓" + fmtTokens(e.ct || 0) : (isTool ? (e.ms != null ? e.ms + "ms" : "—") : "—")) + '</span>' +
          '<span class="ui-cost mono">' + fmtCost(e.cost || 0) + '</span>' +
          "</li>";
      }).join("");
      usageNote.textContent = "单价（可改 .env）：输入 ¥" + (p.in_per_m || "?") + "/M · 输出 ¥" + (p.out_per_m || "?") +
        "/M，成本为估算值；Bridge 重启后计数清零。最近 " + evs.length + " 条 / 最多保留 50 条。";
    }).catch(bridgeDown);
  }

})();