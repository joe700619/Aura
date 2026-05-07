// 扣繳計算機
(function () {
  'use strict';

  const INCOME_TYPES = {
    salary: {
      label: "勞務報酬（薪資）",
      options: [
        { value: "9b", label: "9B · 兼職薪資所得", rate: 0.05, threshold: 88501,
          note: "單次給付未達 88,501 元免扣繳；超過則扣 5%", foreign: false },
        { value: "9b-foreign", label: "9B · 非居住者薪資", rate: 0.18, threshold: 0,
          note: "非居住者一律扣 18%（每月給付未達基本工資 1.5 倍時為 6%）", foreign: true }
      ]
    },
    professional: {
      label: "執行業務所得",
      options: [
        { value: "9a-1", label: "9A · 一般執行業務（10%）", rate: 0.10, threshold: 20001,
          note: "如顧問、講師、設計、翻譯等；單次未達 20,001 元免扣", foreign: false },
        { value: "9a-2", label: "9A · 稿費 / 版稅（10%）", rate: 0.10, threshold: 20001,
          note: "稿費、版稅、樂譜等執行業務所得", foreign: false },
        { value: "9a-foreign", label: "9A · 非居住者執行業務", rate: 0.20, threshold: 0,
          note: "非居住者執行業務所得扣 20%", foreign: true },
      ]
    },
    rent: {
      label: "租金",
      options: [
        { value: "51", label: "51 · 不動產租金（10%）", rate: 0.10, threshold: 20001,
          note: "土地、房屋、工廠、廠房等租金；單次未達 20,001 元免扣", foreign: false },
        { value: "51-foreign", label: "51 · 非居住者租金", rate: 0.20, threshold: 0,
          note: "非居住者租金所得扣 20%", foreign: true },
      ]
    }
  };
  const NHI_THRESHOLD = 20000;
  const NHI_RATE = 0.0211;

  const TIPS = {
    salary: "薪資所得不適用二代健保補充保費，但需依公司規模申報勞健保。",
    professional: "執行業務所得需於每年 1 月底前由扣繳義務人開立扣繳憑單。若同一年度給付同一人累計達 1,000 元以上需申報免扣繳憑單。",
    rent: "租金扣繳需注意：押金生息（年息 1%）也需列入計算。承租戶為公司行號時需扣繳，個人之間租賃通常不需扣繳。"
  };

  let state = { tab: "salary", resident: "yes", nhiExempt: false, typeIdx: 0, amount: 50000, reverse: false };

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Math.round(n).toLocaleString();

  function availableTypes() {
    return INCOME_TYPES[state.tab].options.filter(o => state.resident === "yes" ? !o.foreign : o.foreign);
  }

  function syncTypeSelect() {
    const sel = $('wt-type');
    const types = availableTypes();
    sel.innerHTML = '';
    types.forEach((t, i) => {
      const o = document.createElement('option');
      o.value = i; o.textContent = t.label;
      sel.appendChild(o);
    });
    if (state.typeIdx >= types.length) state.typeIdx = 0;
    sel.value = state.typeIdx;
    $('wt-type-note').textContent = (types[state.typeIdx] || {}).note || '';
  }

  function calc() {
    const types = availableTypes();
    const cur = types[state.typeIdx] || types[0];
    if (!cur) return null;
    const amt = parseFloat(state.amount) || 0;
    const rate = cur.rate;
    const threshold = cur.threshold;
    let payable, withhold, nhi, net;

    if (state.reverse) {
      const trial = amt / (1 - rate);
      const willCharge = !state.nhiExempt && trial >= NHI_THRESHOLD && state.tab !== "salary";
      const willWithhold = trial >= threshold;
      const r = willWithhold ? rate : 0;
      const n = willCharge ? NHI_RATE : 0;
      payable = Math.round(amt / (1 - r - n));
      withhold = Math.round(payable * r);
      nhi = Math.round(payable * n);
      net = payable - withhold - nhi;
    } else {
      payable = Math.round(amt);
      const willWithhold = payable >= threshold;
      const willCharge = !state.nhiExempt && payable >= NHI_THRESHOLD && state.tab !== "salary";
      withhold = willWithhold ? Math.round(payable * rate) : 0;
      nhi = willCharge ? Math.round(payable * NHI_RATE) : 0;
      net = payable - withhold - nhi;
    }
    return {
      payable, withhold, nhi, net,
      withholdRate: rate, threshold,
      willWithhold: payable >= threshold,
      willChargeNhi: !state.nhiExempt && payable >= NHI_THRESHOLD && state.tab !== "salary"
    };
  }

  function render() {
    syncTypeSelect();
    const c = calc();
    if (!c) return;

    $('wt-headline-label').textContent = state.reverse ? "你需要支付" : "對方實領";
    $('wt-headline').textContent = fmt(state.reverse ? c.payable : c.net);
    $('wt-payable').textContent = fmt(c.payable) + ' 元';

    let withholdLabel = `代扣繳稅額（${(c.withholdRate * 100).toFixed(0)}%）`;
    if (!c.willWithhold) withholdLabel += ' <span class="tcf-tag">未達起扣門檻</span>';
    $('wt-withhold-label').innerHTML = withholdLabel;
    $('wt-withhold').textContent = '− ' + fmt(c.withhold) + ' 元';

    let nhiLabel = '二代健保（2.11%）';
    if (state.tab === "salary") nhiLabel += ' <span class="tcf-tag">薪資不適用</span>';
    else if (state.nhiExempt) nhiLabel += ' <span class="tcf-tag">免扣</span>';
    else if (!c.willChargeNhi) nhiLabel += ' <span class="tcf-tag">未達 20,000</span>';
    $('wt-nhi-label').innerHTML = nhiLabel;
    $('wt-nhi-val').textContent = '− ' + fmt(c.nhi) + ' 元';
    $('wt-net').textContent = fmt(c.net) + ' 元';

    $('wt-amount-hint').textContent = state.reverse
      ? '輸入實領金額，自動回推應付總額'
      : '輸入應付給對方的金額（稅前）';
    $('wt-tip').textContent = TIPS[state.tab];
    $('wt-nhi-row').style.display = state.tab === "salary" ? 'none' : '';
  }

  // Tab change
  document.querySelectorAll('#wt-tabs .t-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#wt-tabs .t-tab').forEach((b) => b.classList.toggle('active', b === btn));
      state.tab = btn.dataset.tab;
      state.typeIdx = 0;
      render();
    });
  });

  // Resident
  document.querySelectorAll('#wt-resident input[name="wt-res"]').forEach((r) => {
    r.addEventListener('change', () => {
      state.resident = r.value;
      document.querySelectorAll('#wt-resident .t-radio').forEach((label) => {
        label.classList.toggle('active', label.querySelector('input').checked);
      });
      state.typeIdx = 0;
      render();
    });
  });

  // NHI exempt
  document.querySelectorAll('#wt-nhi input[name="wt-nhi-r"]').forEach((r) => {
    r.addEventListener('change', () => {
      state.nhiExempt = r.value === 'exempt';
      document.querySelectorAll('#wt-nhi .t-radio').forEach((label) => {
        label.classList.toggle('active', label.querySelector('input').checked);
      });
      render();
    });
  });

  $('wt-type').addEventListener('change', (e) => {
    state.typeIdx = parseInt(e.target.value) || 0;
    $('wt-type-note').textContent = (availableTypes()[state.typeIdx] || {}).note || '';
    render();
  });

  $('wt-amount').addEventListener('input', (e) => {
    state.amount = parseFloat(e.target.value) || 0;
    render();
  });

  $('wt-reverse').addEventListener('change', (e) => {
    state.reverse = e.target.checked;
    render();
  });

  render();
})();
