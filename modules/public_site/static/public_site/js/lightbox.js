(function () {
  'use strict';

  function ensureOverlay() {
    var overlay = document.getElementById('lb-overlay');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'lb-overlay';
    overlay.className = 'lightbox-overlay';
    overlay.innerHTML = '<button type="button" class="lightbox-close" aria-label="關閉">×</button><img alt="">';
    document.body.appendChild(overlay);

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay || e.target.classList.contains('lightbox-close')) {
        close();
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
    return overlay;
  }

  function open(src, alt) {
    var overlay = ensureOverlay();
    var img = overlay.querySelector('img');
    img.src = src;
    img.alt = alt || '';
    overlay.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    var overlay = document.getElementById('lb-overlay');
    if (!overlay) return;
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  document.addEventListener('click', function (e) {
    var img = e.target.closest('.ps-visual-img');
    if (!img) return;
    e.preventDefault();
    open(img.src, img.alt);
  });
})();
