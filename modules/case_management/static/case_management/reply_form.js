/* 案件回覆表單 — 檔案預覽 chip render */
function renderFilePreview(input) {
  const preview = input.form.querySelector('[data-file-preview]');
  preview.innerHTML = '';
  const files = Array.from(input.files);
  files.forEach((f, idx) => {
    const chip = document.createElement('span');
    chip.className = 'inline-flex items-center gap-1 bg-gray-100 hover:bg-gray-200 text-xs rounded-full px-2 py-1';
    const isImg = f.type.startsWith('image/');
    chip.innerHTML = `
      <span>${isImg ? '🖼️' : '📄'}</span>
      <span class="max-w-[140px] truncate">${escapeHtml(f.name)}</span>
      <span class="text-gray-400">(${formatSize(f.size)})</span>
      <button type="button" class="text-gray-400 hover:text-red-500 ml-1" data-remove-idx="${idx}">✕</button>
    `;
    chip.querySelector('[data-remove-idx]').addEventListener('click', (e) => {
      e.stopPropagation();
      removeFileAt(input, parseInt(e.target.dataset.removeIdx));
    });
    preview.appendChild(chip);
  });
}

function removeFileAt(input, idx) {
  const dt = new DataTransfer();
  Array.from(input.files).forEach((f, i) => { if (i !== idx) dt.items.add(f); });
  input.files = dt.files;
  renderFilePreview(input);
}

function formatSize(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB';
  return (b/(1024*1024)).toFixed(1) + ' MB';
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
