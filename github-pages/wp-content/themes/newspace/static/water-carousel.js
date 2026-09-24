(() => {
  const track = document.querySelector('#water-service-cards');
  if (!track) return;
  const root = track.closest('.sd-carousel');
  const cards = [...track.children];
  const dots = [...root.querySelectorAll('.sd-carousel-pagination button')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let current = 0, timer, hovered = false, touching = false, visible = false;
  function update() {
    const left = track.getBoundingClientRect().left;
    current = cards.reduce((best, card, i) => Math.abs(card.getBoundingClientRect().left - left) < Math.abs(cards[best].getBoundingClientRect().left - left) ? i : best, 0);
    dots.forEach((dot, i) => dot.setAttribute('aria-current', String(i === current)));
  }
  function schedule() {
    clearTimeout(timer);
    if (reduced.matches || document.hidden || !visible || hovered || touching || root.contains(document.activeElement)) return;
    timer = setTimeout(() => { move((current + 1) % cards.length); schedule(); }, 5500);
  }
  function move(index) {
    track.scrollBy({left: cards[index].getBoundingClientRect().left - track.getBoundingClientRect().left, behavior: reduced.matches ? 'instant' : 'smooth'});
  }
  dots.forEach((dot, i) => dot.addEventListener('click', () => { move(i); schedule(); }));
  track.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault(); move((current + (e.key === 'ArrowRight' ? 1 : -1) + cards.length) % cards.length); schedule();
    }
  });
  track.addEventListener('scroll', update, {passive:true});
  track.addEventListener('wheel', schedule, {passive:true});
  root.addEventListener('mouseenter', () => { hovered = true; schedule(); });
  root.addEventListener('mouseleave', () => { hovered = false; schedule(); });
  root.addEventListener('pointerdown', () => { touching = true; schedule(); });
  window.addEventListener('pointerup', () => { touching = false; schedule(); });
  window.addEventListener('pointercancel', () => { touching = false; schedule(); });
  root.addEventListener('focusin', schedule);
  root.addEventListener('focusout', () => setTimeout(schedule, 0));
  document.addEventListener('visibilitychange', schedule);
  reduced.addEventListener('change', schedule);
  window.addEventListener('resize', update);
  new IntersectionObserver(entries => { visible = entries[0].isIntersecting; schedule(); }, {threshold:0.3}).observe(root);
  update();
})();
