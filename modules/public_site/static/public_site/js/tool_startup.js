// 創業設立評估 — 6 題 wizard + 結果頁
(function () {
  'use strict';

  const wizard = document.getElementById('sa-wizard');
  const report = document.getElementById('sa-report');
  if (!wizard) return;

  const cards = Array.from(wizard.querySelectorAll('.sa-card'));
  const totalSteps = cards.length;
  const fill = document.getElementById('sa-progress-fill');
  const currentText = document.getElementById('sa-step-current');
  const pctText = document.getElementById('sa-step-pct');

  let step = 0;
  const answers = {};

  function show(idx) {
    cards.forEach((c, i) => { c.style.display = i === idx ? '' : 'none'; });
    if (currentText) currentText.textContent = idx + 1;
    const pct = Math.round(((idx + 1) / totalSteps) * 100);
    if (pctText) pctText.textContent = pct;
    if (fill) fill.style.width = pct + '%';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function updateNextButton(card) {
    const id = card.dataset.stepId;
    const nextBtn = card.querySelector('[data-sa-next]');
    if (nextBtn) nextBtn.disabled = !answers[id];
  }

  function buildConclusion(a) {
    const groups = [];

    // 組織型態建議
    const org = [];
    if (a.purpose === '最省稅') {
      if (a.entity === '行號') {
        org.push('您的設立目的偏向節稅，且偏好行號型態——這是常見的省稅組合。行號採綜合所得稅課稅，營收較低時稅負通常優於公司。');
      } else if (a.entity === '尚未決定 — 想要建議') {
        org.push('您的設立目的偏向節稅，建議優先考慮行號型態，多數情況下可獲得較佳的稅務優勢。');
      } else {
        org.push('您的設立目的偏向節稅，但偏好的組織型態為「' + a.entity + '」。一般情況下行號會比公司有更好的租稅優勢，建議再評估。');
      }
    } else if (a.purpose === '減少法律責任' || a.purpose === '募集資金') {
      if (a.entity === '行號') {
        org.push('您的設立目的是「' + a.purpose + '」，但行號屬於無限責任的個人事業（無法人格），不適合此目的，建議改選有限公司或股份有限公司，可享有限責任保障。');
      } else if (a.entity === '尚未決定 — 想要建議') {
        org.push('您的設立目的是「' + a.purpose + '」，建議選擇公司型態（有限公司或股份有限公司）以享有限責任保障。');
      }
    }

    if (a.shareholders === '1 人' && a.entity === '股份有限公司') {
      org.push('股份有限公司依法須有 2 名以上發起人，1 名股東無法設立股份有限公司，建議改選有限公司（1 人即可設立）。');
    }

    if (a.purpose === '募集資金') {
      org.push('股份有限公司較適合對外募集資金，但增資、減資、股權變動等事項需經股東會或董事會決議，行政程序較繁瑣，請納入考量。');
    }

    if (org.length) groups.push({ heading: '組織型態建議', paragraphs: org });

    // 資本額
    if (a.capital === '未滿 25 萬') {
      const cap = (a.entity === '行號')
        ? '您選擇行號型態且資本額未滿 25 萬，依規定行號資本額 25 萬以下無須實際出資，可降低初期資金壓力。'
        : '資本額未滿 25 萬，若選擇行號型態（25 萬以下無須實際出資）可進一步降低初期資金壓力。';
      groups.push({ heading: '資本額', paragraphs: [cap] });
    }

    // 地址
    let addr = '';
    if (a.address === '商務中心') {
      addr = '商務中心：營業項目可能受到限制，例如餐飲業、飯店業等實體營運項目通常無法登記，建議先確認商務中心可登記的營業項目範圍。';
    } else if (a.address === '自有房屋') {
      addr = '自有房屋：即使房屋是負責人自己的，仍視為「出租給公司」。房屋稅與地價稅可能會變高（依登記使用範圍，依房屋稅及地價稅現值，可能有 1/6 改用營業使用稅率）；且房東須設算租金收入併入個人所得稅，即使實際未收取租金。';
    } else if (a.address === '承租實體辦公室') {
      addr = '承租實體辦公室：若房東為自然人，單次給付租金超過 2 萬元時，需依規定辦理扣繳（10%）並繳納二代健保補充保費（2.11%）。';
    }
    if (addr) groups.push({ heading: '地址規劃', paragraphs: [addr] });

    // 健保（不論答案都加說明）
    groups.push({
      heading: '負責人健保',
      paragraphs: [
        '負責人依規定須投保在自己的公司，除非已在其他公司擔任負責人、或受聘於其他單位並以受雇者身分投保。若目前投保在職業工會，設立公司後將會被要求改投保在自己公司，並以負責人身分投保。'
      ],
    });

    return groups;
  }

  function renderConclusion() {
    const body = document.getElementById('sa-conclusion-body');
    if (!body) return;
    const groups = buildConclusion(answers);
    body.innerHTML = groups.map(g => `
      <div class="sa-r-conclusion-group">
        <h4 class="sa-r-conclusion-heading">${g.heading}</h4>
        ${g.paragraphs.map(p => `<p>${p}</p>`).join('')}
      </div>
    `).join('') + `
      <p class="sa-r-placeholder-note">
        ※ 以上建議為系統依您的作答自動產生的初步分析，實際情況請以會計師面談為準。
      </p>`;
  }

  function showReport() {
    wizard.style.display = 'none';
    report.style.display = '';
    Object.entries(answers).forEach(([qid, val]) => {
      const el = report.querySelector(`[data-answer-value="${qid}"]`);
      if (el) el.textContent = val;
    });
    renderConclusion();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cards.forEach((card, idx) => {
    const qid = card.dataset.stepId;

    card.querySelectorAll(`input[type="radio"][name="sa-${qid}"]`).forEach((r) => {
      r.addEventListener('change', () => {
        answers[qid] = r.value;
        updateNextButton(card);
      });
    });

    const nextBtn = card.querySelector('[data-sa-next]');
    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (idx < totalSteps - 1) {
          step = idx + 1;
          show(step);
        } else {
          showReport();
        }
      });
    }

    const backBtn = card.querySelector('[data-sa-back]');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        if (idx > 0) {
          step = idx - 1;
          show(step);
        }
      });
    }
  });

  const restartBtn = document.getElementById('sa-restart');
  if (restartBtn) {
    restartBtn.addEventListener('click', () => {
      Object.keys(answers).forEach((k) => delete answers[k]);
      wizard.querySelectorAll('input[type="radio"]').forEach((r) => { r.checked = false; });
      cards.forEach((c) => updateNextButton(c));
      wizard.querySelectorAll('.faq-item.open').forEach((d) => d.classList.remove('open'));
      report.querySelectorAll('details').forEach((d) => d.removeAttribute('open'));
      report.querySelectorAll('[data-answer-value]').forEach((el) => { el.textContent = '—'; });
      step = 0;
      report.style.display = 'none';
      wizard.style.display = '';
      show(0);
    });
  }

  // FAQ accordion（與 bookkeeping 服務頁同樣的展開邏輯）
  document.querySelectorAll('.sa-tips .faq-item').forEach((item) => {
    const btn = item.querySelector('.faq-q');
    if (!btn) return;
    btn.addEventListener('click', () => item.classList.toggle('open'));
  });

  show(0);
})();
