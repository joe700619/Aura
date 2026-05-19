// 勞務報酬單
(function () {
  'use strict';
  const TAX_RATES = { "9a": 0.10, "9b": 0.10 };
  const WITHHOLD_TAX_FLOOR = 2000;   // 扣繳稅額 > 2000 才需扣繳
  const NHI_RATE = 0.0211;
  const NHI_THRESHOLD = 20000;       // 給付金額 >= 20000 須扣補充保費

  const fmt = (n) => Math.round(n).toLocaleString();
  const $ = (id) => document.getElementById(id);

  function setText(id, v) { const el = $(id); if (el) el.textContent = v || '—'; }

  function items() {
    return Array.from(document.querySelectorAll('#pr-items .t-item-row')).map((row) => ({
      desc: row.querySelector('[data-item-desc]').value,
      amount: parseFloat(row.querySelector('[data-item-amount]').value) || 0,
    }));
  }

  function getRadio(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : '';
  }

  function render() {
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
    const residency = getRadio('pr-residency') || 'local';
    const inUnion = getRadio('pr-union') === 'yes';

    // 外國人未滿 183 天：扣繳稅率一律 20%，全額扣繳（無 2000 起扣保留）
    // 本國人 / 外國人滿 183 天：依所得類別套用稅率；應扣稅額 > 2000 才需扣繳
    let rate, willWithhold, rateLabel;
    if (residency === 'foreign_nonresident') {
      rate = 0.20;
      willWithhold = total > 0;
      rateLabel = '非居住者 20%';
    } else {
      rate = TAX_RATES[taxType];
      const provisional = total * rate;
      willWithhold = provisional > WITHHOLD_TAX_FLOOR;
      rateLabel = `${taxType.toUpperCase()} · ${(rate * 100).toFixed(0)}%`;
    }
    const withhold = willWithhold ? Math.round(total * rate) : 0;

    // 二代健保補充保費：已加入職業工會則免扣
    const willNHI = !inUnion && total >= NHI_THRESHOLD && taxType !== '9b';
    const nhi = willNHI ? Math.round(total * NHI_RATE) : 0;
    const net = total - withhold - nhi;

    setText('pv-total', fmt(total) + ' 元');
    let wlbl = `扣繳稅額（${rateLabel}）`;
    if (!willWithhold) wlbl += ' · 未達起扣門檻';
    setText('pv-withhold-label', wlbl);
    setText('pv-withhold', '− ' + fmt(withhold) + ' 元');

    let nlbl = '二代健保補充保費（2.11%）';
    if (inUnion) nlbl += ' · 已加入職業工會免扣';
    else if (!willNHI) nlbl += ' · 不適用';
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
  ['pr-payer-name','pr-payer-id','pr-payer-contact','pr-payer-addr','pr-payee-name','pr-payee-id','pr-payee-addr','pr-tax-type','pr-date'].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener('input', render);
    if (el) el.addEventListener('change', render);
  });
  // bind new radio groups
  document.querySelectorAll('input[name="pr-residency"], input[name="pr-union"]').forEach((el) => {
    el.addEventListener('change', render);
  });

  render();
})();
