(function () {
  "use strict";

  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

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
  }
  navItems.forEach(function (n) {
    n.addEventListener("click", function () { showView(n.dataset.view); });
  });

  /* ───────── 全局输入：AI 识别提示（隐形式 AI 的关键演示）───────── */
  var capture = $("#capture");
  var captureHint = $("#captureHint");
  capture.addEventListener("input", function () {
    var v = capture.value.trim();
    if (!v) { captureHint.hidden = true; return; }
    var type, rule;
    if (/(复盘|总结|回顾)/.test(v)) { type = "复盘"; rule = "生成今日复盘"; }
    else if (/(任务|做完|搞定|安排)/.test(v)) { type = "任务"; rule = "放入项目 · 行动"; }
    else if (/(决策|决定|要不要|该不该)/.test(v)) { type = "决策"; rule = "进入决策备忘"; }
    else { type = "想法"; rule = "归入收件箱"; }
    captureHint.hidden = false;
    captureHint.innerHTML =
      '<b>✦ AI 识别为「' + type + '」</b> · 建议' + rule +
      ' <button class="btn btn-mini" style="margin-left:8px">确认归位</button> <span style="opacity:.7">· 可改</span>';
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

})();