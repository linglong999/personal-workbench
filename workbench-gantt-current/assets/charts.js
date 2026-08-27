(function() {
  var style = getComputedStyle(document.documentElement);
  function cv(n) { return style.getPropertyValue(n).trim(); }
  var accent = cv('--accent');
  var accent2 = cv('--accent2');
  var ink = cv('--ink');
  var muted = cv('--muted');
  var rule = cv('--rule');
  var bg2 = cv('--bg2');
  var warn = cv('--warn');
  var ok = cv('--ok');
  var todo = cv('--todo');

  var gantt = echarts.init(document.getElementById('chart-gantt'), null, { renderer: 'svg' });

  /*
    甘特数据：用横向条形，每行代表一个任务。
    第一阶段（完成）D1-D5，第二阶段（完成）D6-D9，验收（完成）D9-D10，阶段三（规划中）D10.
    为了表达"已完成 vs 规划"，使用双系列：当前状态用 accent 实心，规划中虚线/置灰。
  */
  var tasks = [
    { name: '阶段一 · 六层 Prompt 工程', start: 1, end: 5, status: 'done', group: ' 阶段一' },
    { name: '   ├ 输入/决策/实践层', start: 1, end: 3, status: 'done' },
    { name: '   └ 复盘/知识/愿景层 + 配套', start: 3, end: 5, status: 'done' },
    { name: 'Task 2-1 初始化工程', start: 6, end: 6, status: 'done' },
    { name: 'Task 2-2 配置模块', start: 6, end: 6, status: 'done' },
    { name: 'Task 2-3 知识库读写', start: 6, end: 7, status: 'done' },
    { name: 'Task 2-4 向量检索', start: 7, end: 7, status: 'done' },
    { name: 'Task 2-5 AI 引擎 + Agent', start: 7, end: 8, status: 'done' },
    { name: 'Task 2-6 FastMCP 服务', start: 8, end: 9, status: 'done' },
    { name: 'Task 2-7 入口集成', start: 9, end: 9, status: 'done' },
    { name: 'Task 2-8 阶段二验收', start: 9, end: 10, status: 'done' },
    { name: '阶段三 · 开源展示', start: 10, end: 10, status: 'plan' },
    { name: '   ├ README 重写', start: 10, end: 10, status: 'plan' },
    { name: '   └ UI 壳页面 / GitHub 上传', start: 10, end: 10, status: 'todo' }
  ];

  var statusColor = { done: ok, plan: accent, todo: warn };

  // 反向 y 轴使第一个任务在顶部
  var yNames = tasks.map(function(t) { return t.name; }).reverse();

  // 每个任务两条：占位（透明） + 实际（带 offsetX via stack 的空占位技巧）
  // 用堆叠两条来实现从 start 到 end：bar1 = start-1 (透明占位), bar2 = end-start+1 (着色)
  var series = [];
  var xAxis = { type: 'value', min: 0, max: 10, interval: 1,
    axisLine: { lineStyle: { color: rule } },
    axisLabel: { color: muted, formatter: '{value}D', fontFamily: 'JetBrainsMono' },
    splitLine: { lineStyle: { color: rule } },
    name: '天数', nameTextStyle: { color: muted }
  };
  var yAxis = { type: 'category', data: yNames, inverse: true,
    axisLine: { lineStyle: { color: rule } },
    axisTick: { show: false },
    axisLabel: { color: ink, fontSize: 12 },
    splitLine: { show: false }
  };

  // placeholder series (在下方，先画)
  var phData = tasks.map(function(t) { return (t.start - 1) * 1; }).reverse();
  var segData = tasks.map(function(t) { return (t.end - t.start + 1) * 1; }).reverse();

  series.push({
    name: 'day-marker', type: 'bar', stack: 'gantt', barWidth: '70%',
    data: phData,
    itemStyle: { color: 'rgba(0,0,0,0)' },
    emphasis: { disabled: true },
    silent: true
  });
  series.push({
    name: 'task', type: 'bar', stack: 'gantt', barWidth: '70%',
    data: segData.map(function(v, i) {
      var t = tasks[tasks.length - 1 - i];
      return {
        value: v,
        itemStyle: {
          color: statusColor[t.status],
          opacity: t.status === 'done' ? 0.92 : 0.75,
          borderRadius: [0, 4, 4, 0]
        }
      };
    }),
    label: {
      show: true,
      position: 'right',
      formatter: function(p) {
        var t = tasks[tasks.length - 1 - p.dataIndex];
        return { done: '✅ 已完成', plan: '设计中', todo: '待设计' }[t.status] || '';
      },
      color: muted, fontSize: 11
    },
    tooltip: { trigger: 'item' }
  });

  gantt.setOption({
    animation: false,
    tooltip: {
      trigger: 'item',
      appendToBody: true,
      formatter: function(p) {
        var i = tasks.length - 1 - p.dataIndex;
        var t = tasks[i];
        if (!t) return '';
        var st = { done: '✅ 已完成', plan: '🔶 设计中', todo: '○ 待设计' }[t.status] || t.status;
        return '<b>' + t.name + '</b><br/>' + st + ' · D' + t.start + '–D' + t.end;
      }
    },
    grid: { left: '1%', right: '14%', top: 12, bottom: 8, containLabel: true },
    xAxis: xAxis,
    yAxis: yAxis,
    series: series
  });
  window.addEventListener('resize', function() { gantt.resize(); });
})();