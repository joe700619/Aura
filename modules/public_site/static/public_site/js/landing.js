// 對外網站 — landing 頁面互動
(function () {
  'use strict';

  // ── Modal ────────────────────────────────────────────────
  const modal = document.querySelector('[data-modal]');
  const open = () => modal && modal.classList.add('show');
  const close = () => modal && modal.classList.remove('show');

  document.querySelectorAll('[data-open-modal]').forEach((el) => {
    el.addEventListener('click', open);
  });
  document.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', close);
  });
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) close();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });

  // ── FAQ accordion ────────────────────────────────────────
  document.querySelectorAll('[data-faq-list] .faq-item').forEach((item) => {
    const btn = item.querySelector('.faq-q');
    if (!btn) return;
    btn.addEventListener('click', () => {
      item.classList.toggle('open');
    });
  });

  // ── Audience tabs ────────────────────────────────────────
  const tabs = document.querySelectorAll('[data-audience-tab]');
  const panels = document.querySelectorAll('[data-audience-panel]');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const idx = tab.dataset.audienceTab;
      tabs.forEach((t) => t.classList.toggle('active', t === tab));
      panels.forEach((p) => p.classList.toggle('active', p.dataset.audiencePanel === idx));
    });
  });

  // ── Form helpers (前端驗證；送出尚未串後端) ────────────────
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function showError(form, name, msg) {
    const el = form.querySelector(`[data-error-for="${name}"]`);
    if (el) el.textContent = msg || '';
    const input = form.querySelector(`[name="${name}"]`);
    if (input) input.classList.toggle('error', !!msg);
  }

  function clearErrors(form) {
    form.querySelectorAll('[data-error-for]').forEach((el) => (el.textContent = ''));
    form.querySelectorAll('.error').forEach((el) => el.classList.remove('error'));
  }

  function flashSuccess(form) {
    const ok = form.querySelector('[data-form-success]');
    if (ok) ok.classList.add('show');
    setTimeout(() => {
      if (ok) ok.classList.remove('show');
      form.reset();
    }, 4000);
  }

  // ── Inquiry form submit (contact + appointment 共用) ──────
  // 流程：前端驗證 → POST /inquiry/submit/ → 成功 → 顯示提示 → 跳 LINE
  function clientValidate(form) {
    clearErrors(form);
    const data = new FormData(form);
    let bad = false;
    if (!(data.get('name') || '').trim()) { showError(form, 'name', '請填寫姓名'); bad = true; }
    const email = (data.get('email') || '').trim();
    const phone = (data.get('phone') || '').trim();
    if (email && !emailRe.test(email)) { showError(form, 'email', 'Email 格式不正確'); bad = true; }
    if (!email && !phone) {
      showError(form, 'email', '請至少留下 Email 或電話');
      showError(form, 'phone', '請至少留下 Email 或電話');
      bad = true;
    }
    return !bad;
  }

  document.querySelectorAll('[data-inquiry-form]').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!clientValidate(form)) return;

      const submitBtn = form.querySelector('[type="submit"], .form-submit');
      if (submitBtn) { submitBtn.disabled = true; submitBtn.dataset.origText = submitBtn.textContent; submitBtn.textContent = '送出中…'; }

      const fd = new FormData(form);
      if (form.dataset.source) fd.set('source', form.dataset.source);
      const csrf = (form.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';

      try {
        const res = await fetch('/inquiry/submit/', {
          method: 'POST',
          headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
          body: fd,
        });
        const json = await res.json().catch(() => ({}));

        if (res.ok && json.ok) {
          flashSuccess(form);
          // 1.2 秒後跳 LINE 加好友
          setTimeout(() => {
            if (json.redirect) window.location.href = json.redirect;
          }, 1200);
        } else if (json.errors) {
          Object.entries(json.errors).forEach(([k, v]) => showError(form, k, v));
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = submitBtn.dataset.origText; }
        } else {
          alert(res.status === 429 ? '太頻繁了，請稍後再試。' : '送出失敗，請稍後再試或直接 LINE 聯繫。');
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = submitBtn.dataset.origText; }
        }
      } catch (err) {
        alert('網路異常，請稍後再試。');
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = submitBtn.dataset.origText; }
      }
    });
  });
})();
