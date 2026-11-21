/* arq decisions · Kopfzeile, Menü, Dialoge. Keine Cookies, kein Tracking. */
(function () {
  var header = document.querySelector('.site-header');
  var hero = document.querySelector('.hero');

  // Kopfzeile: transparent über dem Hero, danach weiß
  function onScroll() {
    var limit = hero ? Math.max(40, hero.offsetHeight - header.offsetHeight - 10) : 0;
    header.classList.toggle('is-solid', window.scrollY > limit || !hero);
  }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);

  // Mobiles Menü
  var toggle = document.querySelector('.nav-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.has-sub > .nav-link').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var li = btn.parentElement;
      var open = !li.classList.contains('open');
      document.querySelectorAll('.has-sub.open').forEach(function (o) { if (o !== li) { o.classList.remove('open'); o.firstElementChild.setAttribute('aria-expanded', 'false'); } });
      li.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-sub')) {
      document.querySelectorAll('.has-sub.open').forEach(function (o) { o.classList.remove('open'); o.firstElementChild.setAttribute('aria-expanded', 'false'); });
    }
  });
  document.querySelectorAll('.nav a').forEach(function (a) {
    a.addEventListener('click', function () { document.body.classList.remove('nav-open'); if (toggle) toggle.setAttribute('aria-expanded', 'false'); });
  });

  // Dialoge (Terminbuchung, Thema in zwei Sätzen)
  function openModal(id) {
    var d = document.getElementById(id);
    if (!d) return;
    var f = d.querySelector('iframe[data-src]');
    if (f && !f.src) f.src = f.getAttribute('data-src');
    document.body.classList.remove('nav-open');
    if (typeof d.showModal === 'function') d.showModal(); else d.setAttribute('open', '');
    document.body.classList.add('modal-open');
  }
  document.querySelectorAll('[data-modal]').forEach(function (b) {
    b.addEventListener('click', function () { openModal(b.getAttribute('data-modal')); });
  });
  document.querySelectorAll('dialog.modal').forEach(function (d) {
    d.addEventListener('close', function () { document.body.classList.remove('modal-open'); });
    d.addEventListener('click', function (e) {
      var close = e.target.hasAttribute('data-close');
      if (e.target === d) {
        var r = d.getBoundingClientRect();
        close = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      }
      if (close) { if (d.close) d.close(); else d.removeAttribute('open'); }
    });
  });

  // Animierte Videos anhalten, wenn reduzierte Bewegung gewünscht ist
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('video[autoplay]').forEach(function (v) { v.removeAttribute('autoplay'); v.pause(); v.controls = true; });
  }
})();
