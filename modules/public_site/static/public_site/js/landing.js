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

  // Contact form
  const contactForm = document.getElementById('contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      clearErrors(contactForm);
      const data = new FormData(contactForm);
      let bad = false;
      if (!data.get('name').trim()) { showError(contactForm, 'name', '請填寫姓名'); bad = true; }
      const email = data.get('email').trim();
      if (!email) { showError(contactForm, 'email', '請填寫 Email'); bad = true; }
      else if (!emailRe.test(email)) { showError(contactForm, 'email', 'Email 格式不正確'); bad = true; }
      if (!data.get('phone').trim()) { showError(contactForm, 'phone', '請填寫聯絡電話'); bad = true; }
      const msg = data.get('message').trim();
      if (!msg || msg.length < 10) { showError(contactForm, 'message', '請至少描述 10 個字'); bad = true; }
      if (bad) return;
      flashSuccess(contactForm);
    });
  }

  // Appointment form (modal)
  const apptForm = document.getElementById('appointment-form');
  if (apptForm) {
    apptForm.addEventListener('submit', (e) => {
      e.preventDefault();
      clearErrors(apptForm);
      const data = new FormData(apptForm);
      let bad = false;
      if (!data.get('name').trim()) { showError(apptForm, 'name', '請填寫姓名'); bad = true; }
      const email = data.get('email').trim();
      if (!email) { showError(apptForm, 'email', '請填寫 Email'); bad = true; }
      else if (!emailRe.test(email)) { showError(apptForm, 'email', 'Email 格式不正確'); bad = true; }
      if (!data.get('phone').trim()) { showError(apptForm, 'phone', '請填寫電話'); bad = true; }
      if (bad) return;
      flashSuccess(apptForm);
      setTimeout(close, 2500);
    });
  }
})();
