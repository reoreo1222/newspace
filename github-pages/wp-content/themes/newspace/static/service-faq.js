/* Animate native disclosure panels while retaining keyboard and reduced-motion support. */
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('.service-detail .sd-faq details').forEach(panel => {
    const summary = panel.querySelector('summary');
    let animation = null;
    let expanded = panel.open;
    summary.addEventListener('click', event => {
      if (reduced.matches) return;
      event.preventDefault();
      const start = panel.getBoundingClientRect().height;
      if (animation) animation.cancel();
      expanded = !expanded;
      panel.style.height = '';
      panel.style.overflow = 'hidden';
      panel.open = true;
      const border = parseFloat(getComputedStyle(panel).borderTopWidth) + parseFloat(getComputedStyle(panel).borderBottomWidth);
      const end = expanded ? panel.getBoundingClientRect().height : summary.getBoundingClientRect().height + border;
      animation = panel.animate([{height:`${start}px`},{height:`${end}px`}], {duration:380,easing:'cubic-bezier(.22,.65,.3,1)'});
      animation.onfinish = () => {
        panel.open = expanded;
        panel.style.overflow = '';
        animation = null;
      };
    });
    panel.addEventListener('toggle', () => { if (!animation) expanded = panel.open; });
  });
})();
