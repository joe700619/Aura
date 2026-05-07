// 勞務報酬單
(function () {
  'use strict';
  const TAX_RATES = { "9a": 0.10, "9b": 0.05, "50": 0.10 };
  const TAX_THRESHOLDS = { "9a": 20000, "9b": 88501, "50": 5000 };
  const NHI_RATE = 0.0211;
  const NHI_THRESHOLD = 20000;

  const fmt = (n) => Math.round(n).toLocaleString();
  const $ = (id) => document.getElementById(id);

  function setText(id, v) { const el = $(id); if (el) el.textContent = v || '—'; }

  function items() {
    return Array.from(document.querySelectorAll('#pr-items .t-item-row')).map((row) => ({
      desc: row.querySelector('[data-item-desc]').value,
      amount: parseFloat(row.querySelector('[data-item-amount]').value) || 0,
    }));
  }

  function render() {
    setText('pv-doc', $('pr-doc-no').value);
    setText('pv-date', $('pr-date').value);
    setText('pv-payer-name', $('pr-payer-name').value);
    setText('pv-payer-id', $('pr-payer-id').value);
    setText('pv-payer-addr', $('pr-payer-addr').value);
    setText('pv-payer-contact', $('pr-payer-contact').value);
    setText('pv-payee-name', $('pr-payee-name').value);
    setText('pv-payee-id', $('pr-payee-id').value);
    setText('pv-payee-addr', $('pr-payee-addr').value);

    const list = items();
    const total = list.reduce((s, i) => s + i.amount, 0);

    const tbody = $('pv-items');
    tbody.innerHTML = '';
    list.forEach((it) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${it.desc || '—'}</td><td style="text-align:right">${fmt(it.amount)}</td>`;
      tbody.appendChild(tr);
    });

    const taxType = $('pr-tax-type').value;
    const rate = TAX_RATES[taxType];
    const threshold = TAX_THRESHOLDS[taxType];
    const willWithhold = total >= threshold;
    const withhold = willWithhold ? Math.round(total * rate) : 0;
    const willNHI = total >= NHI_THRESHOLD && taxType !== '9b';
    const nhi = willNHI ? Math.round(total * NHI_RATE) : 0;
    const net = total - withhold - nhi;

    setText('pv-total', fmt(total) + ' 元');
    let wlbl = `扣繳稅額（${taxType.toUpperCase()} · ${(rate * 100).toFixed(0)}%）`;
    if (!willWithhold) wlbl += ' · 未達起扣門檻';
    setText('pv-withhold-label', wlbl);
    setText('pv-withhold', '− ' + fmt(withhold) + ' 元');

    let nlbl = '二代健保補充保費（2.11%）';
    if (!willNHI) nlbl += ' · 不適用';
    setText('pv-nhi-label', nlbl);
    setText('pv-nhi', '− ' + fmt(nhi) + ' 元');
    setText('pv-net', fmt(net) + ' 元');

    // disable remove if only 1 row
    const rows = document.querySelectorAll('#pr-items .t-item-row');
    rows.forEach((r) => {
      const btn = r.querySelector('[data-item-remove]');
      btn.disabled = rows.length === 1;
    });
  }

  function bindRow(row) {
    row.querySelectorAll('input').forEach((i) => i.addEventListener('input', render));
    const rm = row.querySelector('[data-item-remove]');
    rm.addEventListener('click', () => {
      const rows = document.querySelectorAll('#pr-items .t-item-row');
      if (rows.length <= 1) return;
      row.remove();
      render();
    });
  }

  document.querySelectorAll('#pr-items .t-item-row').forEach(bindRow);

  $('pr-add').addEventListener('click', () => {
    const div = document.createElement('div');
    div.className = 't-item-row';
    div.innerHTML = `<input class="tf-input" placeholder="項目說明" data-item-desc/><input type="number" class="tf-input ti-amount" placeholder="金額" value="0" data-item-amount/><button type="button" class="ti-remove" data-item-remove>×</button>`;
    $('pr-items').appendChild(div);
    bindRow(div);
    render();
  });

  // bind static fields
  ['pr-payer-name','pr-payer-id','pr-payer-contact','pr-payer-addr','pr-payee-name','pr-payee-id','pr-payee-addr','pr-tax-type','pr-date','pr-doc-no'].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener('input', render);
    if (el) el.addEventListener('change', render);
  });

  render();
})();
