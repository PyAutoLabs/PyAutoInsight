(() => {
  function route() {
    const query = new URLSearchParams(location.search);
    const pages = [...document.querySelectorAll('.setup-page')];
    const selected = pages.find(p => p.dataset.instance === query.get('instance') && p.dataset.setup === query.get('setup') && (!query.has('implementation') || p.dataset.implementation === query.get('implementation')));
    const detail = query.get('view') === 'setup' && !!selected;
    document.body.classList.toggle('setup-view', detail);
    document.getElementById('inference-home').hidden = detail;
    document.getElementById('inference-pages').hidden = !detail;
    for (const page of pages) {
      page.hidden = page !== selected;
      page.open = page === selected;
      const instrument = page.querySelector('[data-instrument]');
      if (instrument) instrument.selectedIndex = [...instrument.options].findIndex(option => new URL(option.value, location.href).searchParams.get('setup') === page.dataset.setup);
    }
    document.getElementById('setup-route-status').textContent = query.get('view') === 'setup' && !selected ? 'This setup is unavailable in the captured evidence. Choose an available setup below.' : '';
    document.title = detail ? selected.querySelector('h1').textContent + ' · PyAutoInsight' : 'PyAutoInsight dashboard';
  }
  route();
  addEventListener('popstate', route);
  document.querySelectorAll('[data-instrument]').forEach(select => select.addEventListener('change', () => {
    history.pushState({}, '', select.value);
    route();
  }));
  document.querySelectorAll('[data-candidate-copy]').forEach(button => button.addEventListener('click', async () => {
    const panel = button.closest('[data-candidate]');
    const text = panel.querySelector('textarea');
    const status = panel.querySelector('[role="status"]');
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(text.value);
      status.textContent = 'Prompt copied';
    } catch (_) {
      text.closest('details').open = true;
      text.focus(); text.select();
      status.textContent = 'Select and copy the prompt below';
    }
  }));
})();
