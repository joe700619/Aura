// 創業分析表
(function () {
  'use strict';
  const STEPS = 4;
  let step = 0;
  const data = { concerns: [] };

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Math.round(n).toLocaleString();

  function showStep() {
    document.querySelectorAll('[data-step]').forEach((el) => {
      el.style.display = parseInt(el.dataset.step) === step ? '' : 'none';
    });
    $('sa-back').disabled = step === 0;
    $('sa-next').textContent = step === STEPS - 1 ? '產生報告' : '下一步';
    const pct = ((step + 1) / STEPS) * 100;
    $('sa-progress').style.width = pct + '%';
    $('sa-step-text').textContent = (step + 1) + ' / ' + STEPS;
    $('sa-pct').textContent = Math.round(pct) + '%';
  }

  // text/number/select inputs
  document.querySelectorAll('[data-field]').forEach((el) => {
    el.addEventListener('input', () => { data[el.dataset.field] = el.value; });
    el.addEventListener('change', () => { data[el.dataset.field] = el.value; });
  });

  // radio fields
  document.querySelectorAll('[data-radio-field]').forEach((group) => {
    const field = group.dataset.radioField;
    group.querySelectorAll('input[type="radio"]').forEach((r) => {
      r.addEventListener('change', () => {
        data[field] = r.value;
        group.querySelectorAll('.t-radio').forEach((label) => {
          label.classList.toggle('active', label.querySelector('input').checked);
        });
      });
    });
  });

  // checkbox group (concerns)
  document.querySelectorAll('#sa-concerns input[type="checkbox"]').forEach((cb) => {
    cb.addEventListener('change', () => {
      const lbl = cb.closest('.t-check');
      lbl.classList.toggle('active', cb.checked);
      const v = cb.value;
      if (cb.checked) { if (!data.concerns.includes(v)) data.concerns.push(v); }
      else data.concerns = data.concerns.filter((x) => x !== v);
    });
  });

  $('sa-next').addEventListener('click', () => {
    if (step < STEPS - 1) { step++; showStep(); }
    else renderReport();
  });
  $('sa-back').addEventListener('click', () => {
    if ($('sa-report').style.display !== 'none') {
      $('sa-report').style.display = 'none';
      $('sa-wizard').style.display = '';
      step = STEPS - 1; showStep(); return;
    }
    if (step > 0) { step--; showStep(); }
  });

  function renderReport() {
    const cap = parseFloat(data.capital) || 0;
    const fixed = parseFloat(data.fixedCost) || 0;
    const rev = parseFloat(data.expectedRevenue) || 0;
    const margin = (parseFloat(data.grossMargin) || 0) / 100;
    const monthlyProfit = rev * margin - fixed;
    const runway = fixed > 0 ? Math.floor(cap / fixed) : 0;
    const breakeven = margin > 0 ? Math.ceil(fixed / margin) : 0;

    const recs = [];
    const entity = data.entity || '';
    if (entity.startsWith('獨資')) {
      recs.push(['登記建議', '選擇行號可享較低設立成本與彈性，但要注意「責任無限」——個人財產與事業綁在一起。若預期業務涉及合約風險，建議直接設立有限公司。']);
    } else if (entity.startsWith('有限')) {
      recs.push(['登記建議', '有限公司是最常見的中小企業選擇。最低資本額無限制，1 人即可設立。記得章程要寫清楚股東出資比例與盈餘分配。']);
    } else if (entity.startsWith('股份')) {
      recs.push(['登記建議', '股份有限公司適合預期未來募資、引入投資人。設立成本較高（需董事 3 人以上、監察人 1 人），股東會、董事會的會議紀錄要留存。']);
    } else {
      recs.push(['登記建議', '從你勾選的多個選項看，建議與會計師面談 30 分鐘，根據你的業務性質、合夥情況、未來募資規劃，給出最適合的型態建議。']);
    }

    if (data.vat === '未滿 240 萬（小規模 / 1% 營業稅）') {
      recs.push(['稅務', '年營收未滿 240 萬可申請小規模營業人，由國稅局每季核定營業稅（1%），不需開立統一發票。但無法抵扣進項稅額，若進貨成本高反而吃虧。']);
    } else if (data.vat) {
      recs.push(['稅務', '年營收 240 萬以上需依法開立統一發票，營業稅 5%（可扣抵進項）。建議使用電子發票系統節省成本。']);
    }

    if (runway > 0 && runway < 6) {
      recs.push(['資金', `以你目前的資本（${fmt(cap)} 元）扣除每月固定支出（${fmt(fixed)} 元），現金跑道約 ${runway} 個月。少於 6 個月偏緊，建議準備備用金或調整成本結構。`]);
    } else if (runway >= 6) {
      recs.push(['資金', `現金跑道約 ${runway} 個月，屬於健康範圍。建議仍預留 6 個月以上備用金，以應對非預期狀況。`]);
    }

    if (data.employees && parseFloat(data.employees) > 0) {
      recs.push(['勞健保', `聘僱 ${data.employees} 人需在 5 人以上強制投保勞保、健保。即使未滿 5 人，仍須代扣代繳就業保險（5 人以下無強制勞保但有就保義務需確認最新法令）。`]);
    }

    if (data.concerns.length > 0) {
      recs.push(['你關注的問題', `你勾選了 ${data.concerns.length} 個擔憂，包括「${data.concerns.slice(0, 2).join('」、「')}」等。這些議題建議在 30 分鐘的免費諮詢中逐一釐清。`]);
    }

    const recsHtml = recs.map(([tag, text]) =>
      `<div class="t-rec-item"><div class="t-rec-tag">${tag}</div><div class="t-rec-text">${text}</div></div>`
    ).join('');

    const profitClass = monthlyProfit >= 0 ? 'pos' : 'neg';
    const profitSign = monthlyProfit >= 0 ? '+' : '';

    $('sa-report').innerHTML = `
      <div class="t-report">
        <div class="t-report-head">
          <div class="t-report-eyebrow">創業財務診斷報告 · DIAGNOSTIC</div>
          <h2 class="t-report-title">${data.name || '你的事業'} · 初步分析</h2>
          <div class="t-report-meta">
            <span>${data.industry || '—'}</span><span>·</span>
            <span>${data.stage || '—'}</span><span>·</span>
            <span>創始 ${data.founders || 1} 人</span>
          </div>
        </div>
        <div class="t-report-stats">
          <div class="t-stat-card"><div class="t-stat-label">月損益（穩定後）</div><div class="t-stat-value ${profitClass}">${profitSign}${fmt(monthlyProfit)}</div><div class="t-stat-unit">元 / 月</div></div>
          <div class="t-stat-card"><div class="t-stat-label">損益兩平營收</div><div class="t-stat-value">${fmt(breakeven)}</div><div class="t-stat-unit">元 / 月</div></div>
          <div class="t-stat-card"><div class="t-stat-label">現金跑道</div><div class="t-stat-value">${runway || '—'}</div><div class="t-stat-unit">個月</div></div>
        </div>
        <div class="t-report-section">
          <h3 class="t-report-h3">會計師建議</h3>
          <div class="t-rec-list">${recsHtml}</div>
        </div>
        <div class="t-report-cta">
          <div>
            <div class="t-rcta-eyebrow">下一步</div>
            <div class="t-rcta-title">想針對這份診斷深入討論？</div>
            <p>免費 30 分鐘諮詢，會計師會根據你的回答提供具體的登記、稅務、勞健保規劃建議。</p>
          </div>
          <div class="t-rcta-actions">
            <button type="button" class="btn-primary-lg" data-open-modal>預約免費諮詢</button>
            <button type="button" class="btn-secondary-lg" id="sa-restart">重新填寫</button>
          </div>
        </div>
      </div>`;

    $('sa-wizard').style.display = 'none';
    $('sa-report').style.display = '';
    document.getElementById('sa-restart').addEventListener('click', () => {
      $('sa-report').style.display = 'none';
      $('sa-wizard').style.display = '';
      step = 0;
      showStep();
    });
    // Re-bind modal trigger on freshly inserted button
    $('sa-report').querySelectorAll('[data-open-modal]').forEach((b) => {
      b.addEventListener('click', () => {
        const m = document.querySelector('[data-modal]');
        if (m) m.classList.add('show');
      });
    });
  }

  showStep();
})();
