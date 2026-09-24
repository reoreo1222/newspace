const menu = document.querySelector('.menu-toggle');
menu?.addEventListener('click', () => { const open = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(open)); document.querySelector('nav').classList.toggle('open', open); menu.querySelector('span').textContent = open ? '−' : '＋'; });
document.addEventListener('keydown', e => { if(e.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') { menu.click(); menu.focus(); } });
document.querySelectorAll('#navigation a, .footer-nav a').forEach(a => {
  const path = decodeURI(location.pathname).replace(/\/$/, '');
  const target = decodeURI(a.pathname).replace(/\/$/, '');
  if (path === target) a.setAttribute('aria-current', 'page');
  else if (target && path.startsWith(target + '/')) a.setAttribute('aria-current', 'location');
});
const form = document.querySelector('#contact-form');
form?.addEventListener('submit', e => {
  e.preventDefault();
  const name = form.elements.name.value.trim();
  const email = form.elements.email.value.trim();
  const message = form.elements.message.value.trim();
  for (const [field,value] of [[form.elements.name,name],[form.elements.message,message]]) {field.setCustomValidity(value ? '' : '内容を入力してください。');}
  if (!form.reportValidity()) return;
  const service = form.elements.service?.selectedOptions[0]?.textContent || '';
  const body = `相談分野：${service}\nお名前：${name}\nメールアドレス：${email}\n\nお問い合わせ内容：\n${message}`;
  document.querySelector('#message-preview').textContent = body;
  document.querySelector('#mail-link').href = 'mailto:info@newspace.co.jp?subject=' + encodeURIComponent('Webサイトからのお問い合わせ') + '&body=' + encodeURIComponent(body);
  const result = document.querySelector('#form-result'); result.hidden = false; result.focus();
});
form?.addEventListener('input', e => { e.target.setCustomValidity?.(''); document.querySelector('#form-result').hidden = true; document.querySelector('#mail-link').removeAttribute('href'); });
document.querySelector('#edit-message')?.addEventListener('click', () => {document.querySelector('#form-result').hidden = true; document.querySelector('#name').focus();});

// Progressive enhancement: content remains visible without JavaScript or motion support.
(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (motion.matches) return;
  const images = [...document.querySelectorAll('.image-reveal, .work-card-photo, .work-gallery figure')];
  images.forEach(element => element.classList.add('image-reveal'));
  const headings = [...document.querySelectorAll('.intro h2, .english-title, .page-heading h1, h2.japanese, .values article, .principle-copy, .principle-diagram')];
  const targets = [...images, ...headings];
  const show = element => {
    element.classList.remove('reveal-waiting');
    element.classList.add('reveal-visible');
  };
  const entered = new Set();
  const revealEntries = entries => {
    entries.forEach(({target, isIntersecting}) => {
      if (!isIntersecting) return;
      if (entered.has(target)) return;
      entered.add(target);
      const img = target.querySelector('img');
      // Wait for a lazy image to load before unveiling it.
      if (img && !img.complete) {
        const loaded = () => show(target);
        img.addEventListener('load', loaded, {once:true});
        img.addEventListener('error', loaded, {once:true});
      } else show(target);
      observer?.unobserve(target);
    });
  };
  const observer = typeof IntersectionObserver === 'function'
    ? new IntersectionObserver(revealEntries, {threshold:0.12, rootMargin:'0px 0px -24px 0px'})
    : null;
  headings.forEach(element => element.classList.add('text-reveal'));
  targets.forEach(element => {
    element.classList.add('reveal-waiting');
    observer?.observe(element);
  });
  let frame = 0;
  const checkScroll = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      revealEntries(targets.filter(target => !entered.has(target)).map(target => {
        const box = target.getBoundingClientRect();
        return {target, isIntersecting:box.top < innerHeight - 24 && box.bottom > 0};
      }));
    });
  };
  if (!observer) {
    window.addEventListener('scroll', checkScroll, {passive:true});
    window.addEventListener('resize', checkScroll);
    checkScroll();
  }
  const finish = () => {
    observer?.disconnect();
    window.removeEventListener('scroll', checkScroll);
    window.removeEventListener('resize', checkScroll);
    cancelAnimationFrame(frame);
    targets.forEach(show);
  };
  motion.addEventListener('change', event => { if (event.matches) finish(); });
  // Never conceal a keyboard-focused element or a printed document.
  document.addEventListener('focusin', event => {
    const target = event.target.closest('.reveal-waiting');
    if (target) { show(target); observer?.unobserve(target); }
  });
  window.addEventListener('beforeprint', finish);
})();

// Three-slide hero: begin after the depth entrance, keep unloaded photos hidden.
(() => {
  const hero = document.querySelector('.hero');
  if (!hero) return;
  const slides = [...hero.querySelectorAll('.hero-slide')].slice(0, 3);
  if (slides.length < 2) return;
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let current = 0, timer = 0, ready = false, inView = true;
  const loaded = slide => slide.complete && slide.naturalWidth > 0;
  const show = index => {
    if (!loaded(slides[index])) return;
    current = index;
    slides.forEach((slide, i) => {
      slide.classList.toggle('is-active', i === index);
      if (i === index) slide.classList.add('is-zooming');
      else setTimeout(() => {
        if (!slide.classList.contains('is-active')) slide.classList.remove('is-zooming');
      }, 1100);
    });

  };
  const sync = () => {
    clearTimeout(timer);
    const suspended = !ready || motion.matches || !inView || document.hidden;
    hero.classList.toggle('is-slideshow-paused', suspended);
    if (suspended) return;
    timer = setTimeout(() => {
      for (let step = 1; step < slides.length; step++) {
        const next = (current + step) % slides.length;
        if (loaded(slides[next])) { show(next); break; }
      }
      sync();
    }, 3000);
  };
  document.addEventListener('visibilitychange', sync);
  motion.addEventListener('change', sync);
  if (typeof IntersectionObserver === 'function') {
    new IntersectionObserver(entries => { inView = entries[0].isIntersecting; sync(); }).observe(hero);
  }
  const begin = () => { if (!ready) { ready = true; sync(); } };
  hero.querySelector('.hero-visual')?.addEventListener('animationend', event => {
    if (event.animationName === 'depth-photo') begin();
  });
  // Also covers disabled animation, restored pages, or a missing animation event.
  setTimeout(begin, motion.matches ? 0 : 2100);
  sync();
})();
