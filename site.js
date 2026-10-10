(() => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#primary-nav');
  const mobile = window.matchMedia('(max-width: 900px)');

  if (toggle && nav) {
    document.documentElement.classList.add('navigation-ready');
    const setOpen = (open, restoreFocus = false) => {
      nav.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
      if (restoreFocus) toggle.focus();
    };
    toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
    nav.addEventListener('click', event => {
      if (event.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && nav.classList.contains('open')) setOpen(false, true);
    });
    document.addEventListener('click', event => {
      if (!event.target.closest('.nav-wrap')) setOpen(false);
    });
    mobile.addEventListener('change', () => setOpen(false));
  }

  const product = document.querySelector('#product');
  const category = new URLSearchParams(window.location.search).get('category');
  if (product && Array.from(product.options).some(option => option.value === category)) {
    product.value = category;
  }
})();
