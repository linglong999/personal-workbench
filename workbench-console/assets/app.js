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
  function mockRule(v) {
    if (/(复盘|总结|回顾)/.test(v)) { return { type: "复盘", rule: "生成今日复盘" }; }
    if (/(任务|做完|搞定|安排)/.test(v)) { return { type: "任务", rule: "放入项目 · 行动" }; }
    if (/(决策|决定|要不要|该不该)/.test(v)) { return { type: "决策", rule: "进入决策备忘" }; }
    return { type: "想法", rule: "归入收件箱" };
  }
  function showHint(type, rule, live) {
    captureHint.hidden = false;
    captureHint.innerHTML =
      '<b>✦ AI 识别为「' + type + '」' + (live ? ' <span class="mono" style="font-size:.75em;opacity:.75">· 真实 LLM</span>' : "") + '</b> · 建议' + rule +
      ' <button class="btn btn-mini" style="margin-left:8px">确认归位</button> <span style="opacity:.7">· 可改</span>';
  }
  capture.addEventListener("input", function () {
    var v = capture.value.trim();
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
  capture.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && capture.value.trim()) {
      toast("已接住，AI 自动归位为「想法」到收件箱 [撤销]");
      capture.value = ""; captureHint.hidden = true;
    }
  });
  captureHint.addEventListener("click", function (e) {
    if (e.target.tagName === "BUTTON") { toast("已归位到「收件箱」 [撤销]"); capture.value = ""; captureHint.hidden = true; }
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
  function favicon(url) {
    try { return "https://www.google.com/s2/favicons?domain=" + new URL(url).hostname + "&sz=64"; }
    catch (e) { return null; }
  }
  function letterOf(url) { try { return (new URL(url).hostname || "•")[0].toUpperCase(); } catch (e) { return "•"; } }
  function cardHTML(it) {
    var img = favicon(it.url);
    return '<div class="wcard">' +
      '<span class="wcard-fav">' + (img ? '<img src="' + img + '" alt="" loading="lazy">' : '<span class="fallback">' + letterOf(it.url) + '</span>') +
      "</span><span class=\"wcard-info\"><span class=\"wcard-title\">" + it.title + "</span>" +
      '<span class="wcard-site">' + it.site + "</span></span></div>";
  }
  var halves = watchList.map(cardHTML).join("");
  // 无缝循环：一份内容渲染两组（A+A），动画精度平移 -50%，首尾相接
  track.innerHTML = halves + halves;

  /* ───────── Toast ───────── */
  var toastEl = $("#toast");
  var toastTimer;
  function toast(msg) {
    toastEl.innerHTML = msg;
    toastEl.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 2600);
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
          "<p>" + esc((r.content || "").slice(0, 160)) + "</p></div></article>";
      }).join("");
    }).catch(function () {
      srResults.innerHTML = '<p class="sr-note">检索失败：Bridge 未启动。</p>';
      bridgeDown();
    });
  }
  if (srBtn) { srBtn.addEventListener("click", runSearch); }
  if (srInput) {
    srInput.addEventListener("keydown", function (e) { if (e.key === "Enter") runSearch(); });
  }

})();