/* 公共工具: API / DOM / 图表 / 状态标记 */

const PHASE_COLORS = {
  idle: '#3a4454', reach: '#4f8cff', grasp: '#7ee787',
  manipulate: '#bc8cff', release: '#d29922', retreat: '#f85149',
};

async function apiGet(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

function $(sel) { return document.querySelector(sel); }
function $id(sel) { return document.getElementById(sel); }

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c) node.append(c);
  }
  return node;
}

function statCard(label, value, cls = '', hint = '') {
  return el('div', { class: `stat-card ${cls}` }, [
    el('div', { class: 'label', html: label }),
    el('div', { class: `value ${cls}`, html: value }),
    hint ? el('div', { class: 'hint', html: hint }) : null,
  ]);
}

function statusTag(status) {
  const map = {
    succeeded: ['green', '成功'], running: ['accent', '运行中'],
    pending: ['dim', '排队中'], failed: ['danger', '失败'], cancelled: ['warn', '已取消'],
    open: ['warn', '开放'], in_curation: ['accent', '筛选中'],
    added_to_training: ['purple', '已入训练集'], verified: ['green', '已验证'],
    closed: ['dim', '已关闭'], keep: ['green', '保留'], discard: ['danger', '丢弃'],
  };
  const [cls, text] = map[status] || ['dim', status];
  return `<span class="tag ${cls}">${text}</span>`;
}

function fmtTime(v) {
  if (!v) return '—';
  return String(v).replace('T', ' ').slice(0, 19);
}

function table(columns, rows, rowRender) {
  const head = el('thead', {}, [el('tr', {}, columns.map(c =>
    el('th', { html: c.title })))]);
  const body = el('tbody', {}, rows.map((r, i) => {
    const cells = rowRender ? rowRender(r, i) : columns.map(c => el('td', { html: r[c.key] ?? '—' }));
    return el('tr', {}, cells);
  }));
  const t = el('table', {}, [head, body]);
  const wrap = el('div', { class: 'table-wrap' }, [t]);
  return wrap;
}

function initChart(id, option) {
  const node = $id(id);
  if (!node) return null;
  const chart = echarts.init(node);
  chart.setOption(option);
  window.addEventListener('resize', () => chart.resize());
  return chart;
}

const ECHARTS_BASE = {
  textStyle: { color: '#8b949e' },
  legend: { textStyle: { color: '#8b949e' } },
  tooltip: { backgroundColor: '#1c2333', borderColor: '#2d3748', textStyle: { color: '#e6edf3' } },
};

function phaseChartOption(spans, totalDuration) {
  const seriesData = [];
  for (const s of spans) {
    seriesData.push({
      name: s.phase, value: Math.round((s.end_time - s.start_time) * 10) / 10,
      itemStyle: { color: PHASE_COLORS[s.phase] || '#4f8cff' },
    });
  }
  return {
    ...ECHARTS_BASE,
    tooltip: { ...ECHARTS_BASE.tooltip, formatter: p => `${p.name}: ${p.value}s` },
    series: [{
      type: 'pie', radius: ['42%', '68%'], center: ['50%', '50%'],
      label: { color: '#8b949e', fontSize: 11 },
      data: seriesData,
    }],
  };
}

function barOption(categories, values, color = '#4f8cff', formatter) {
  return {
    ...ECHARTS_BASE,
    grid: { left: 48, right: 24, top: 24, bottom: 40 },
    xAxis: { type: 'category', data: categories, axisLine: { lineStyle: { color: '#2d3748' } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#21262d' } } },
    tooltip: { ...ECHARTS_BASE.tooltip, formatter },
    series: [{
      type: 'bar', data: values, itemStyle: { color, borderRadius: [4, 4, 0, 0] },
      barMaxWidth: 36,
    }],
  };
}

function pieOption(data, colors) {
  return {
    ...ECHARTS_BASE,
    series: [{
      type: 'pie', radius: ['40%', '66%'],
      label: { color: '#8b949e', fontSize: 11 },
      data: data.map((d, i) => ({
        name: d.name, value: d.value,
        itemStyle: { color: colors ? colors[i % colors.length] : undefined },
      })),
    }],
  };
}
