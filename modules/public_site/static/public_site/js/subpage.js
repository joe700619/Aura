// 對外子頁共用互動：FAQ 折疊、step 網格切換、accordion
(function () {
  'use strict';

  // FAQ accordion
  document.querySelectorAll('.faq-item').forEach((item) => {
    const btn = item.querySelector('.faq-q');
    if (!btn) return;
    btn.addEventListener('click', () => item.classList.toggle('open'));
  });

  // 通用 step grid 切換（family-office、registration 用）
  // data-step-grid 包住一組 .{prefix}-step + .{prefix}-step-detail-panel[data-step-index]
  document.querySelectorAll('[data-step-grid]').forEach((grid) => {
    const prefix = grid.dataset.stepGrid;
    const steps = grid.querySelectorAll('[data-step-index]');
    const detailRoot = document.querySelector(`[data-step-detail="${prefix}"]`);
    if (!detailRoot) return;
    const panels = detailRoot.querySelectorAll('[data-step-panel]');
    const timelineSegs = document.querySelectorAll(`[data-step-timeline="${prefix}"] [data-step-seg]`);

    steps.forEach((step) => {
      step.addEventListener('click', () => {
        const idx = step.dataset.stepIndex;
        steps.forEach((s) => s.classList.toggle('is-active', s === step));
        steps.forEach((s) => {
          const cue = s.querySelector('[data-step-cue]');
          if (cue) cue.textContent = s === step ? '目前檢視中' : '查看詳情 →';
        });
        panels.forEach((p) => p.classList.toggle('is-active', p.dataset.stepPanel === idx));
        timelineSegs.forEach((seg) => seg.classList.toggle('is-active', seg.dataset.stepSeg === idx));
      });
    });
  });

  // Accordion 樣式（家族辦公室備用）
  document.querySelectorAll('[data-accordion-row]').forEach((row) => {
    const head = row.querySelector('[data-accordion-head]');
    if (!head) return;
    head.addEventListener('click', () => {
      const opening = !row.classList.contains('is-open');
      row.parentElement.querySelectorAll('[data-accordion-row]').forEach((r) => r.classList.remove('is-open'));
      if (opening) row.classList.add('is-open');
    });
  });
})();
