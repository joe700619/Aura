// 共用：t-radio-group 切換（按鈕版）
(function () {
  document.querySelectorAll('[data-radio-group]').forEach((group) => {
    group.dataset.value = group.dataset.default || '';
    group.querySelectorAll('.t-radio[data-value]').forEach((btn) => {
      btn.addEventListener('click', () => {
        group.querySelectorAll('.t-radio').forEach((b) => b.classList.toggle('active', b === btn));
        group.dataset.value = btn.dataset.value;
        group.dispatchEvent(new CustomEvent('radio-change', { detail: btn.dataset.value }));
      });
    });
  });
})();
