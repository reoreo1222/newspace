(() => {
 const syncHeader = () => document.body.classList.toggle('has-scrolled', window.scrollY > 40);
 syncHeader();window.addEventListener('scroll', syncHeader, {passive:true});
 const select = document.querySelector('#service');
 const category = new URLSearchParams(location.search).get('service');
 if(select && [...select.options].some(option => option.value === category)) select.value = category;
 const button=document.querySelector('.menu-toggle');
 button?.addEventListener('click',()=>button.setAttribute('aria-label', button.getAttribute('aria-expanded')==='true'?'メニューを閉じる':'メニューを開く'));
})();

// Gently fade in the home service photos in sequence on first view.
(() => {
 const section = document.querySelector('.care-home .home-reform');
 const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
 if (!section || motion.matches || !('IntersectionObserver' in window)) return;
 const photos = [...section.querySelectorAll('.care-service-photo')];
 const entered = new Set();
 let stopped = false;
 const show = (photo, delay = 0) => {
  if (stopped || !photo.classList.contains('reform-photo-waiting')) return;
  photo.style.setProperty('--photo-enter-delay', `${delay}ms`);
  photo.classList.replace('reform-photo-waiting', 'reform-photo-entering');
  photo.addEventListener('animationend', () => {
   photo.classList.remove('reform-photo-entering');
   photo.style.removeProperty('--photo-enter-delay');
  }, {once:true});
 };
 const observer = new IntersectionObserver(entries => {
  const visible = entries.filter(entry => entry.isIntersecting && !entered.has(entry.target))
   .sort((a, b) => photos.indexOf(a.target) - photos.indexOf(b.target));
  visible.forEach(({target}, index) => {
   entered.add(target);
   observer.unobserve(target);
   const image = target.querySelector('img');
   const reveal = () => show(target, index * 240);
   if (image && !image.complete) {
    image.addEventListener('load', reveal, {once:true});
    image.addEventListener('error', reveal, {once:true});
   } else reveal();
  });
 }, {threshold:0.18, rootMargin:'0px 0px -24px 0px'});
 photos.forEach(photo => {
  photo.classList.add('reform-photo-waiting');
  observer.observe(photo);
 });
 const finish = () => {
  stopped = true;
  observer.disconnect();
  photos.forEach(photo => {
   photo.classList.remove('reform-photo-waiting', 'reform-photo-entering');
   photo.style.removeProperty('--photo-enter-delay');
  });
 };
 section.addEventListener('focusin', event => {
  const photo = event.target.closest('.care-service')?.querySelector('.care-service-photo');
  if (!photo) return;
  entered.add(photo);
  observer.unobserve(photo);
  photo.classList.remove('reform-photo-waiting', 'reform-photo-entering');
 });
 motion.addEventListener('change', event => { if (event.matches) finish(); });
 window.addEventListener('beforeprint', finish);
})();

// Desktop hover disclosure, with keyboard and touch-button support.
(() => {
 const group = document.querySelector('.reform-nav');
 const toggle = group?.querySelector('.reform-nav-toggle');
 if (!toggle) return;
 const desktop = matchMedia('(min-width:1121px)');
 const setOpen = open => {
  group.classList.toggle('is-open', open);
  toggle.setAttribute('aria-expanded', String(open));
 };
 group.addEventListener('pointerenter', e => { if(desktop.matches && e.pointerType !== 'touch') setOpen(true); });
 group.addEventListener('pointerleave', () => { if(!group.contains(document.activeElement)) setOpen(false); });
 group.addEventListener('focusin', e => { if(e.target !== toggle) setOpen(true); });
 group.addEventListener('focusout', e => { if(!group.contains(e.relatedTarget)) setOpen(false); });
 toggle.addEventListener('click', () => setOpen(!group.classList.contains('is-open')));
 group.addEventListener('keydown', e => {
  if(e.key === 'Escape') {e.stopPropagation();toggle.focus();setOpen(false);}
 });
 document.addEventListener('pointerdown', e => { if(!group.contains(e.target)) setOpen(false); });
 desktop.addEventListener('change', () => setOpen(false));
})();
