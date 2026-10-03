document.querySelectorAll('[data-character-count]').forEach(counter => {
  const input = document.getElementById(counter.dataset.characterCount);
  if (!input) return;
  const update = () => { counter.textContent = `${input.value.length} / ${input.maxLength}`; };
  input.addEventListener('input', update);
  update();
});
document.querySelectorAll('.notice-close').forEach(button => {
  button.addEventListener('click', () => button.closest('.notice').remove());
});
const sort = document.getElementById('idea-sort');
if (sort) sort.addEventListener('change', () => sort.form.requestSubmit());
const copy = document.querySelector('[data-copy-link]');
if (copy) copy.addEventListener('click', async () => {
  const status = document.querySelector('.copy-status');
  try {
    await navigator.clipboard.writeText(window.location.href);
    status.textContent = 'Link copied';
  } catch {
    status.textContent = 'Copy the address from your browser to share this idea.';
  }
});
