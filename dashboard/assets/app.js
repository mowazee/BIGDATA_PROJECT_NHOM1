/* Dashboard kết quả MapReduce – dữ liệu từ data/dashboard_data.js (tạo bởi build_data.py) */
(function () {
  "use strict";
  const D = window.DASHBOARD_DATA;
  if (!D) {
    document.querySelector(".wrap").innerHTML =
      "<p>Chưa có dữ liệu. Chạy <code>python dashboard/build_data.py</code> rồi tải lại trang.</p>";
    return;
  }
  if (!window.echarts) {
    document.getElementById("meta").textContent =
      "Không tải được thư viện ECharts (cần kết nối Internet để tải từ CDN).";
  }

  // ------------------------------------------------------------------ tiện ích
  const SOURCES = ["TGDD", "CellphoneS", "FPTShop"];
  const SOURCE_LABEL = { TGDD: "TGDĐ", CellphoneS: "CellphoneS", FPTShop: "FPT Shop" };
  const SOURCE_VAR = { TGDD: "--src-tgdd", CellphoneS: "--src-cps", FPTShop: "--src-fpt" };
  const active = new Set(SOURCES);
  const charts = {};

  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const srcColor = (s) => css(SOURCE_VAR[s]);
  const nf = new Intl.NumberFormat("vi-VN");
  const vnd = (v) => nf.format(Math.round(v)) + " đ";
  const tr = (v) => (v / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 }) + " tr";
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const romLabel = (gb) => (gb >= 1024 ? gb / 1024 + "TB" : gb + "GB");

  function theme() {
    return {
      ink1: css("--ink-1"), ink2: css("--ink-2"), muted: css("--ink-muted"),
      grid: css("--grid"), axis: css("--axis"), surface: css("--surface"),
      accent: css("--accent"),
      seq: ["--seq-100", "--seq-250", "--seq-400", "--seq-550", "--seq-700"].map(css),
    };
  }

  // Cấu hình chung: lưới mờ, trục nhạt, chữ dùng màu chữ (không dùng màu series)
  function base(t, extra) {
    return Object.assign({
      animationDuration: 400,
      textStyle: { fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: t.ink2 },
      grid: { left: 8, right: 24, top: 40, bottom: 8, containLabel: true },
      tooltip: {
        backgroundColor: t.surface, borderColor: t.axis, borderWidth: 1,
        textStyle: { color: t.ink1, fontSize: 12.5 }, extraCssText: "box-shadow:0 4px 16px rgba(0,0,0,.12);border-radius:8px;",
      },
      legend: { top: 0, left: 0, icon: "circle", itemWidth: 10, itemHeight: 10, textStyle: { color: t.ink2 } },
    }, extra);
  }
  const valueAxis = (t, extra) => Object.assign({
    type: "value", axisLine: { show: false }, axisTick: { show: false },
    axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.grid } },
  }, extra);
  const catAxis = (t, data, extra) => Object.assign({
    type: "category", data, axisLine: { lineStyle: { color: t.axis } }, axisTick: { show: false },
    axisLabel: { color: t.ink2 },
  }, extra);

  function chart(id) {
    if (!window.echarts) return null;
    const el = document.getElementById(id);
    if (!charts[id]) charts[id] = echarts.init(el, null, { renderer: "canvas" });
    return charts[id];
  }

  function table(el, cols, rows) {
    el.innerHTML =
      "<table><thead><tr>" + cols.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.label)}</th>`).join("") +
      "</tr></thead><tbody>" +
      rows.map((r) => "<tr>" + cols.map((c) => {
        const v = c.get(r);
        return `<td class="${c.num ? "num" : ""}">${c.html ? v : esc(v)}</td>`;
      }).join("") + "</tr>").join("") + "</tbody></table>";
  }
  const srcBadge = (s) => `<span class="src-badge" style="--c:${srcColor(s)}">${esc(SOURCE_LABEL[s] || s)}</span>`;

  // ------------------------------------------------------------------ KPI
  function renderKpis() {
    const P = D.products.filter((p) => active.has(p[0]));
    const brands = new Set(P.map((p) => p[1]));
    const avgPrice = P.length ? P.reduce((a, p) => a + p[6], 0) / P.length : 0;
    const discounted = P.filter((p) => p[7] > 0);
    const avgDisc = discounted.length ? discounted.reduce((a, p) => a + p[7], 0) / discounted.length : 0;
    const shared = D.mr5.length;
    const items = [
      ["Sản phẩm (phiên bản)", nf.format(P.length), [...active].map((s) => SOURCE_LABEL[s]).join(" · ")],
      ["Số hãng", nf.format(brands.size), "theo dữ liệu đã làm sạch"],
      ["Giá bán trung bình", tr(avgPrice), vnd(avgPrice)],
      ["Đang giảm giá", Math.round((100 * discounted.length) / Math.max(P.length, 1)) + "%", "mức giảm TB " + avgDisc.toFixed(1) + "%"],
      ["Mẫu máy bán ở ≥ 2 sàn", nf.format(shared), "dùng để so sánh giá (MR5)"],
    ];
    document.getElementById("kpis").innerHTML = items.map(([l, v, s]) =>
      `<div class="kpi"><div class="k-label">${esc(l)}</div><div class="k-value">${esc(v)}</div><div class="k-sub">${esc(s)}</div></div>`
    ).join("");
  }

  // ------------------------------------------------------------------ MR1
  function renderMR1(t) {
    const rows = D.mr1.filter((r) => active.has(r.source));
    const total = {};
    rows.forEach((r) => (total[r.brand] = (total[r.brand] || 0) + r.count));
    const brands = Object.keys(total).sort((a, b) => total[a] - total[b]); // nhỏ ở dưới, lớn ở trên
    const series = SOURCES.filter((s) => active.has(s)).map((s) => ({
      name: SOURCE_LABEL[s], type: "bar", stack: "x", barMaxWidth: 18,
      itemStyle: { color: srcColor(s), borderColor: t.surface, borderWidth: 1 },
      emphasis: { focus: "series" },
      data: brands.map((b) => (rows.find((r) => r.brand === b && r.source === s) || {}).count || 0),
    }));
    const c = chart("c-mr1");
    c && c.setOption(base(t, {
      tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" },
        formatter: (ps) => `<b>${ps[0].name}</b> – tổng ${total[ps[0].name]}<br>` +
          ps.filter((p) => p.value).map((p) => `${p.marker}${p.seriesName}: <b>${p.value}</b>`).join("<br>") }),
      xAxis: valueAxis(t), yAxis: catAxis(t, brands), series,
    }), true);
    table(document.getElementById("t-mr1"),
      [{ label: "Hãng", get: (b) => b }, ...SOURCES.filter((s) => active.has(s)).map((s) => ({
        label: SOURCE_LABEL[s], num: true, get: (b) => (rows.find((r) => r.brand === b && r.source === s) || {}).count || 0,
      })), { label: "Tổng", num: true, get: (b) => total[b] }],
      brands.slice().reverse());
  }

  // ------------------------------------------------------------------ MR4
  function renderMR4(t) {
    const rows = D.mr4.slice().sort((a, b) => a.order - b.order);
    const sum = rows.reduce((a, r) => a + r.count, 0);
    const ramp = [t.seq[1], t.seq[2], t.seq[3], t.seq[4]]; // thang thứ tự: rẻ → cao cấp
    const c = chart("c-mr4");
    c && c.setOption(base(t, {
      legend: { show: false },
      tooltip: Object.assign(base(t).tooltip, { trigger: "item",
        formatter: (p) => `<b>${p.name}</b><br>${p.value} sản phẩm (${((100 * p.value) / sum).toFixed(1)}%)` }),
      xAxis: catAxis(t, rows.map((r) => r.segment.replace(" (", "\n(")), { axisLabel: { color: t.ink2, interval: 0, fontSize: 11 } }),
      yAxis: valueAxis(t),
      series: [{ type: "bar", barMaxWidth: 44,
        data: rows.map((r, i) => ({ value: r.count, name: r.segment, itemStyle: { color: ramp[i], borderRadius: [4, 4, 0, 0] } })),
        label: { show: true, position: "top", color: t.ink1, formatter: (p) => `${p.value}\n${((100 * p.value) / sum).toFixed(0)}%` } }],
    }), true);
    table(document.getElementById("t-mr4"),
      [{ label: "Phân khúc", get: (r) => r.segment }, { label: "Số SP", num: true, get: (r) => r.count },
       { label: "Tỷ lệ", num: true, get: (r) => ((100 * r.count) / sum).toFixed(1) + "%" }], rows);
  }

  // ------------------------------------------------------------------ MR2
  function renderMR2(t) {
    const rows = D.mr2.slice().sort((a, b) => a.avg - b.avg);
    const c = chart("c-mr2");
    c && c.setOption(base(t, {
      legend: { show: false },
      tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" },
        formatter: (ps) => { const r = rows[ps[0].dataIndex];
          return `<b>${r.brand}</b> (${r.count} SP)<br>Thấp nhất: ${vnd(r.min)}<br>Trung bình: <b>${vnd(r.avg)}</b><br>Cao nhất: ${vnd(r.max)}`; } }),
      xAxis: valueAxis(t, { axisLabel: { color: t.muted, formatter: (v) => v / 1e6 + " tr" } }),
      yAxis: catAxis(t, rows.map((r) => r.brand)),
      series: [
        { type: "bar", stack: "r", silent: true, itemStyle: { color: "transparent" }, data: rows.map((r) => r.min), barMaxWidth: 8 },
        { type: "bar", stack: "r", barMaxWidth: 8, itemStyle: { color: t.seq[1], borderRadius: 4 }, data: rows.map((r) => r.max - r.min) },
        { type: "scatter", symbolSize: 10, itemStyle: { color: t.accent, borderColor: t.surface, borderWidth: 2 },
          data: rows.map((r) => r.avg), z: 5 },
      ],
    }), true);
    table(document.getElementById("t-mr2"),
      [{ label: "Hãng", get: (r) => r.brand }, { label: "Số SP", num: true, get: (r) => r.count },
       { label: "Thấp nhất", num: true, get: (r) => vnd(r.min) }, { label: "Trung bình", num: true, get: (r) => vnd(r.avg) },
       { label: "Cao nhất", num: true, get: (r) => vnd(r.max) }], rows.slice().reverse());
  }

  // ------------------------------------------------------------------ MR3
  const MR3_LABEL = {
    avg_discount: "% giảm giá trung bình trên mọi sản phẩm",
    avg_discount_discounted: "% giảm giá trung bình, chỉ tính sản phẩm đang giảm",
    discounted_pct: "Tỷ lệ sản phẩm đang được giảm giá",
  };
  function renderMR3(t) {
    const metric = document.getElementById("mr3-metric").value;
    document.getElementById("mr3-sub").textContent = MR3_LABEL[metric];
    const rows = SOURCES.filter((s) => active.has(s)).map((s) => D.mr3.find((r) => r.source === s)).filter(Boolean);
    const c = chart("c-mr3");
    c && c.setOption(base(t, {
      legend: { show: false },
      tooltip: Object.assign(base(t).tooltip, { trigger: "item",
        formatter: (p) => { const r = rows[p.dataIndex];
          return `<b>${SOURCE_LABEL[r.source]}</b><br>Tổng: ${r.total} SP · đang giảm: ${r.discounted} (${r.discounted_pct}%)` +
            `<br>Giảm TB (mọi SP): ${r.avg_discount}%<br>Giảm TB (SP đang giảm): ${r.avg_discount_discounted}%`; } }),
      xAxis: catAxis(t, rows.map((r) => SOURCE_LABEL[r.source])),
      yAxis: valueAxis(t, { axisLabel: { color: t.muted, formatter: "{value}%" } }),
      series: [{ type: "bar", barMaxWidth: 56,
        data: rows.map((r) => ({ value: r[metric], itemStyle: { color: srcColor(r.source), borderRadius: [4, 4, 0, 0] } })),
        label: { show: true, position: "top", color: t.ink1, fontWeight: 600, formatter: "{c}%" } }],
    }), true);
    table(document.getElementById("t-mr3"),
      [{ label: "Sàn", html: true, get: (r) => srcBadge(r.source) }, { label: "Tổng SP", num: true, get: (r) => r.total },
       { label: "SP đang giảm", num: true, get: (r) => `${r.discounted} (${r.discounted_pct}%)` },
       { label: "Giảm TB (mọi SP)", num: true, get: (r) => r.avg_discount + "%" },
       { label: "Giảm TB (SP đang giảm)", num: true, get: (r) => r.avg_discount_discounted + "%" }], rows);
  }

  // ------------------------------------------------------------------ MR5 (dumbbell)
  function renderMR5(t) {
    const n = +document.getElementById("mr5-n").value;
    const srcs = SOURCES.filter((s) => active.has(s));
    const rows = D.mr5
      .map((r) => {
        const prices = {};
        srcs.forEach((s) => { if (r.prices[s]) prices[s] = r.prices[s]; });
        const v = Object.values(prices);
        return { ...r, prices, diff: v.length ? Math.max(...v) - Math.min(...v) : 0, n: v.length };
      })
      .filter((r) => r.n >= 2)
      .sort((a, b) => b.diff - a.diff || a.model.localeCompare(b.model))
      .slice(0, n)
      .reverse(); // chênh lệch lớn nhất ở trên cùng
    const el = document.getElementById("c-mr5");
    el.style.height = Math.max(320, rows.length * 26 + 70) + "px";
    const c = chart("c-mr5");
    if (c) {
      c.resize();
      const lo = rows.map((r) => Math.min(...Object.values(r.prices)));
      const hi = rows.map((r) => Math.max(...Object.values(r.prices)));
      c.setOption(base(t, {
        grid: { left: 8, right: 90, top: 40, bottom: 8, containLabel: true },
        tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" },
          formatter: (ps) => { const r = rows[ps[0].dataIndex];
            return `<b>${r.model}</b> (${r.brand})<br>` +
              Object.keys(r.prices).sort((a, b) => r.prices[a] - r.prices[b])
                .map((s) => `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${srcColor(s)};margin-right:6px"></span>${SOURCE_LABEL[s]}: <b>${vnd(r.prices[s])}</b>`).join("<br>") +
              `<br>Chênh lệch: <b>${vnd(r.diff)}</b>`; } }),
        xAxis: valueAxis(t, { scale: true, axisLabel: { color: t.muted, formatter: (v) => v / 1e6 + " tr" } }),
        yAxis: catAxis(t, rows.map((r) => r.model), { axisLabel: { color: t.ink2, fontSize: 11.5 } }),
        series: [
          { type: "bar", stack: "d", silent: true, itemStyle: { color: "transparent" }, data: lo, barWidth: 2 },
          { type: "bar", stack: "d", silent: true, itemStyle: { color: t.axis }, barWidth: 2, data: hi.map((h, i) => h - lo[i]),
            label: { show: true, position: "right", distance: 14, color: t.ink2, fontSize: 11,
              formatter: (p) => (rows[p.dataIndex].diff ? "+" + tr(rows[p.dataIndex].diff) : "bằng giá") } },
          ...srcs.map((s) => ({
            name: SOURCE_LABEL[s], type: "scatter", symbolSize: 10, z: 5,
            itemStyle: { color: srcColor(s), borderColor: t.surface, borderWidth: 2 },
            data: rows.map((r) => (r.prices[s] ? r.prices[s] : null)),
          })),
        ],
      }), true);
    }
    table(document.getElementById("t-mr5"),
      [{ label: "Mẫu máy", get: (r) => r.model }, { label: "Hãng", get: (r) => r.brand },
       ...srcs.map((s) => ({ label: SOURCE_LABEL[s], num: true, get: (r) => (r.prices[s] ? vnd(r.prices[s]) : "–") })),
       { label: "Chênh lệch", num: true, get: (r) => vnd(r.diff) }], rows.slice().reverse());
  }

  // ------------------------------------------------------------------ MR6 (heatmap)
  function renderMR6(t) {
    const rams = [...new Set(D.mr6.map((r) => r.ram))].sort((a, b) => a - b);
    const roms = [...new Set(D.mr6.map((r) => r.rom))].sort((a, b) => a - b);
    const avgs = D.mr6.map((r) => r.avg);
    const c = chart("c-mr6");
    c && c.setOption(base(t, {
      legend: { show: false },
      grid: { left: 8, right: 16, top: 16, bottom: 56, containLabel: true },
      tooltip: Object.assign(base(t).tooltip, { trigger: "item",
        formatter: (p) => { const r = D.mr6.find((x) => x.ram === rams[p.value[1]] && x.rom === roms[p.value[0]]);
          return `<b>RAM ${r.ram}GB · ROM ${romLabel(r.rom)}</b><br>Giá TB: <b>${vnd(r.avg)}</b><br>${r.count} sản phẩm`; } }),
      xAxis: catAxis(t, roms.map(romLabel), { name: "ROM", nameLocation: "middle", nameGap: 28, nameTextStyle: { color: t.muted }, splitArea: { show: false } }),
      yAxis: catAxis(t, rams.map((r) => r + "GB"), { name: "RAM", nameTextStyle: { color: t.muted } }),
      visualMap: { min: Math.min(...avgs), max: Math.max(...avgs), calculable: false, orient: "horizontal", left: "center", bottom: 0,
        itemHeight: 160, itemWidth: 10, text: ["cao", "thấp"], textStyle: { color: t.muted },
        dimension: 2, // tô màu theo GIÁ TB (cột 2), không phải số SP (cột 3)
        inRange: { color: t.seq }, formatter: (v) => tr(v) },
      series: [{ type: "heatmap",
        data: D.mr6.map((r) => {
          // Chữ trong ô: nền đậm -> chữ sáng, nền nhạt -> chữ tối (đủ tương phản ở cả 2 giao diện)
          const k = (r.avg - Math.min(...avgs)) / (Math.max(...avgs) - Math.min(...avgs) || 1);
          const dark = document.documentElement.dataset.theme === "dark" ||
            (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
          const onStrong = dark ? k < 0.55 : k > 0.45;
          return { value: [roms.indexOf(r.rom), rams.indexOf(r.ram), r.avg, r.count],
            label: { color: onStrong ? (dark ? "#f0efec" : "#ffffff") : (dark ? "#0b0b0b" : "#0b0b0b") } };
        }),
        itemStyle: { borderColor: t.surface, borderWidth: 2, borderRadius: 4 },
        label: { show: true, fontSize: 11, formatter: (p) => p.value[3] },
        emphasis: { itemStyle: { borderColor: t.ink1, borderWidth: 1 } } }],
    }), true);
    table(document.getElementById("t-mr6"),
      [{ label: "RAM", get: (r) => r.ram + "GB" }, { label: "ROM", get: (r) => romLabel(r.rom) },
       { label: "Số SP", num: true, get: (r) => r.count }, { label: "Giá TB", num: true, get: (r) => vnd(r.avg) }],
      D.mr6.slice().sort((a, b) => a.ram - b.ram || a.rom - b.rom));
  }

  // ------------------------------------------------------------------ MR7 (scatter)
  function renderMR7(t) {
    const rows = D.mr7.filter((r) => r.rated > 0);
    const maxCount = Math.max(...rows.map((r) => r.count));
    const c = chart("c-mr7");
    c && c.setOption(base(t, {
      legend: { show: false },
      grid: { left: 8, right: 72, top: 24, bottom: 36, containLabel: true },
      tooltip: Object.assign(base(t).tooltip, { trigger: "item",
        formatter: (p) => { const r = rows[p.dataIndex];
          return `<b>${r.brand}</b><br>Sao TB (trọng số): <b>${r.rating_weighted}</b> · sao TB: ${r.rating}` +
            `<br>Tổng lượt đánh giá: <b>${nf.format(r.reviews)}</b><br>${r.count} SP (${r.rated} SP có đánh giá)`; } }),
      xAxis: valueAxis(t, { type: "log", name: "Tổng lượt đánh giá (log)", nameLocation: "middle", nameGap: 26,
        nameTextStyle: { color: t.muted }, axisLabel: { color: t.muted, formatter: (v) => nf.format(v) } }),
      yAxis: valueAxis(t, { min: (v) => Math.floor(v.min * 10 - 1) / 10, max: 5, name: "Sao TB", nameTextStyle: { color: t.muted } }),
      series: [{ type: "scatter",
        data: rows.map((r) => [Math.max(r.reviews, 1), r.rating_weighted]),
        symbolSize: (v, p) => 8 + 22 * Math.sqrt(rows[p.dataIndex].count / maxCount),
        itemStyle: { color: t.accent, opacity: 0.85, borderColor: t.surface, borderWidth: 2 },
        label: { show: true, position: "right", color: t.ink2, fontSize: 11, formatter: (p) => rows[p.dataIndex].brand },
        labelLayout: { hideOverlap: true } }],
    }), true);
    table(document.getElementById("t-mr7"),
      [{ label: "Hãng", get: (r) => r.brand }, { label: "Số SP", num: true, get: (r) => r.count },
       { label: "SP có đánh giá", num: true, get: (r) => r.rated }, { label: "Sao TB", num: true, get: (r) => r.rating },
       { label: "Sao TB (trọng số)", num: true, get: (r) => r.rating_weighted },
       { label: "Tổng lượt đánh giá", num: true, get: (r) => nf.format(r.reviews) }],
      D.mr7.slice().sort((a, b) => b.reviews - a.reviews));
  }

  // ------------------------------------------------------------------ MR8
  function renderMR8(t) {
    const sel = document.getElementById("mr8-brand");
    const brand = sel.value;
    const rows = D.mr8.filter((r) => r.brand === brand && active.has(r.source)).sort((a, b) => b.saved - a.saved);
    const shown = rows.slice().reverse();
    const srcs = SOURCES.filter((s) => active.has(s) && rows.some((r) => r.source === s));
    const c = chart("c-mr8");
    c && c.setOption(base(t, {
      grid: { left: 8, right: 80, top: 36, bottom: 8, containLabel: true },
      tooltip: Object.assign(base(t).tooltip, { trigger: "item",
        formatter: (p) => { const r = shown[p.dataIndex]; return `<b>${esc(r.name)}</b><br>${SOURCE_LABEL[r.source]} · giảm <b>${vnd(r.saved)}</b>`; } }),
      xAxis: valueAxis(t, { axisLabel: { color: t.muted, formatter: (v) => v / 1e6 + " tr" } }),
      yAxis: catAxis(t, shown.map((r) => r.name), { axisLabel: { color: t.ink2, fontSize: 11.5, width: 300, overflow: "truncate" } }),
      // 1 series / sàn để chú thích (legend) hiển thị đúng màu sàn
      series: srcs.map((s) => ({
        name: SOURCE_LABEL[s], type: "bar", stack: "m", barMaxWidth: 18,
        itemStyle: { color: srcColor(s), borderRadius: [0, 4, 4, 0] },
        data: shown.map((r) => (r.source === s ? r.saved : null)),
        label: { show: true, position: "right", color: t.ink1, formatter: (p) => (p.value ? tr(p.value) : "") },
      })),
    }), true);
    table(document.getElementById("t-mr8"),
      [{ label: "Hạng", num: true, get: (r) => r.rank }, { label: "Sản phẩm", get: (r) => r.name },
       { label: "Sàn", html: true, get: (r) => srcBadge(r.source) }, { label: "Số tiền giảm", num: true, get: (r) => vnd(r.saved) }],
      rows);
  }

  // ------------------------------------------------------------------ Tra cứu sản phẩm
  const COLS = [
    { key: 0, label: "Sàn", html: true, fmt: (v) => srcBadge(v) },
    { key: 1, label: "Hãng" },
    { key: 2, label: "Tên sản phẩm" },
    { key: 3, label: "RAM", num: true, fmt: (v) => (v ? v + "GB" : "–") },
    { key: 4, label: "ROM", num: true, fmt: (v) => (v ? romLabel(v) : "–") },
    { key: 5, label: "Giá gốc", num: true, fmt: vnd },
    { key: 6, label: "Giá bán", num: true, fmt: vnd },
    { key: 7, label: "Giảm", num: true, fmt: (v) => (v ? v.toFixed(1) + "%" : "–") },
    { key: 8, label: "Sao", num: true, fmt: (v) => (v ? v.toFixed(1) : "–") },
    { key: 9, label: "Lượt ĐG", num: true, fmt: (v) => nf.format(v) },
  ];
  let sortKey = 6, sortDir = 1;
  function renderExplorer() {
    const q = document.getElementById("q").value.trim().toLowerCase();
    const brand = document.getElementById("fBrand").value;
    const seg = document.getElementById("fSeg").value;
    const [lo, hi] = seg ? seg.split("-").map(Number) : [0, Infinity];
    const rows = D.products.filter((p) => active.has(p[0]) && (!brand || p[1] === brand) &&
      p[6] >= lo && p[6] < hi && (!q || p[2].toLowerCase().includes(q)))
      .sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : a[sortKey] < b[sortKey] ? -1 : 0) * sortDir);
    const LIMIT = 300;
    document.getElementById("countInfo").textContent =
      `${nf.format(rows.length)} sản phẩm` + (rows.length > LIMIT ? ` (hiển thị ${LIMIT} dòng đầu)` : "");
    const el = document.getElementById("explorer");
    el.innerHTML = "<table><thead><tr>" + COLS.map((c) =>
      `<th class="sortable ${c.num ? "num" : ""}" data-k="${c.key}">${c.label}${sortKey === c.key ? (sortDir > 0 ? " ▲" : " ▼") : ""}</th>`).join("") +
      "</tr></thead><tbody>" + rows.slice(0, LIMIT).map((p) => "<tr>" + COLS.map((c) => {
        const v = c.fmt ? c.fmt(p[c.key]) : p[c.key];
        return `<td class="${c.num ? "num" : ""}">${c.html ? v : esc(v)}</td>`;
      }).join("") + "</tr>").join("") + "</tbody></table>";
    el.querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
      const k = +th.dataset.k;
      sortDir = sortKey === k ? -sortDir : 1; sortKey = k; renderExplorer();
    }));
  }

  // ------------------------------------------------------------------ điều khiển
  function renderAll() {
    const t = theme();
    renderKpis(); renderMR1(t); renderMR4(t); renderMR2(t); renderMR3(t);
    renderMR5(t); renderMR6(t); renderMR7(t); renderMR8(t); renderExplorer();
  }

  function initControls() {
    document.getElementById("meta").textContent +=
      ` Dữ liệu cập nhật: ${D.generated_at} · ${nf.format(D.products.length)} sản phẩm`;

    const chips = document.getElementById("sourceChips");
    chips.innerHTML = SOURCES.map((s) =>
      `<button class="chip" type="button" aria-pressed="true" data-s="${s}"><span class="dot" style="background:var(${SOURCE_VAR[s]})"></span>${SOURCE_LABEL[s]}</button>`).join("");
    chips.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      const s = b.dataset.s;
      if (active.has(s) && active.size === 1) return; // luôn giữ ít nhất 1 sàn
      active.has(s) ? active.delete(s) : active.add(s);
      b.setAttribute("aria-pressed", active.has(s));
      renderAll();
    }));

    const brands = [...new Set(D.mr8.map((r) => r.brand))].sort();
    const sel = document.getElementById("mr8-brand");
    sel.innerHTML = brands.map((b) => `<option ${b === "Samsung" ? "selected" : ""}>${esc(b)}</option>`).join("");
    sel.addEventListener("change", () => renderMR8(theme()));

    const fb = document.getElementById("fBrand");
    [...new Set(D.products.map((p) => p[1]))].sort().forEach((b) => fb.insertAdjacentHTML("beforeend", `<option>${esc(b)}</option>`));
    ["q", "fBrand", "fSeg"].forEach((id) => document.getElementById(id).addEventListener("input", renderExplorer));
    document.getElementById("mr3-metric").addEventListener("change", () => renderMR3(theme()));
    document.getElementById("mr5-n").addEventListener("change", () => renderMR5(theme()));

    // Nút "Xem bảng" – phương án thay thế biểu đồ (đọc số chính xác, hỗ trợ người khó phân biệt màu)
    document.querySelectorAll("[data-table]").forEach((btn) => btn.addEventListener("click", () => {
      const id = btn.dataset.table;
      const tbl = document.getElementById("t-" + id), ch = document.getElementById("c-" + id);
      const showTable = tbl.classList.contains("hidden");
      tbl.classList.toggle("hidden", !showTable); ch.classList.toggle("hidden", showTable);
      btn.textContent = showTable ? "Xem biểu đồ" : "Xem bảng";
      if (!showTable && charts["c-" + id]) charts["c-" + id].resize();
    }));

    // Giao diện sáng / tối
    const themeBtn = document.getElementById("themeBtn");
    let saved = null;
    try { saved = localStorage.getItem("dash-theme"); } catch (e) { /* bỏ qua */ }
    const isDark = () => document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    if (saved) document.documentElement.dataset.theme = saved;
    const syncBtn = () => (themeBtn.textContent = isDark() ? "Giao diện sáng" : "Giao diện tối");
    syncBtn();
    themeBtn.addEventListener("click", () => {
      const next = isDark() ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("dash-theme", next); } catch (e) { /* bỏ qua */ }
      syncBtn(); renderAll();
    });
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { syncBtn(); renderAll(); });

    let timer;
    window.addEventListener("resize", () => {
      clearTimeout(timer);
      timer = setTimeout(() => Object.values(charts).forEach((c) => c.resize()), 150);
    });
  }

  initControls();
  renderAll();
})();
