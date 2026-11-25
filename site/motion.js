/* One scene moves, because it explains something. Everything is readable without this file.
   motion.js moves the packets; data-phase lets styles.css change the gate, labels and colours. */
(() => {
  const demo = document.getElementById('demo');
  if (!window.gsap || !demo) return;
  const { gsap } = window;
  const $ = (selector) => demo.querySelector(selector);
  const whole = $('.packet-whole');
  const a = $('.packet-a');
  const b = $('.packet-b');
  const scan = $('.scan');
  const readOff = $('.read-off');
  const [readA, readB] = demo.querySelectorAll('.read-on i');
  const readLine = $('.read-on b');
  const button = $('.demo-pause');
  const result = $('.demo-result');
  const all = [whole, a, b, scan, readOff, readA, readB, readLine];
  // The curves from styles.css: strong ease-out for arrivals, ease-in-out for travel.
  const arrive = 'power4.out';
  const travel = 'power2.inOut';
  const unread = 'inset(0 100% 0 0)';
  const read = 'inset(0 0% 0 0)';
  const hold = 2.2;
  let timeline;
  let auto = false; // the guided loop is on
  let held = false; // paused by the visitor
  let visible = false;

  const phase = (name) => { if (name) demo.dataset.phase = name; else delete demo.dataset.phase; };

  function rest() {
    if (timeline) timeline.kill();
    timeline = null;
    phase('');
    gsap.set(all, { clearProps: 'all' });
  }

  function sync() {
    if (timeline) timeline.paused(held || !visible);
    const key = auto && !held ? 'pauseDemo' : 'playDemo';
    button.dataset.i18nAria = key;
    button.setAttribute('aria-label', text(key));
    button.classList.toggle('is-paused', key === 'playDemo');
    // The loop must not talk over a screen reader; a choice made by hand is announced.
    result.setAttribute('aria-live', auto ? 'off' : 'polite');
  }

  function setMode(mode) {
    demo.dataset.mode = mode;
    $(`input[value="${mode}"]`).checked = true;
  }

  // Sweeps the reading line over a packet while its text appears above the gate.
  function sweep(element, left, label, duration, at) {
    const width = element.offsetWidth;
    timeline
      .set(scan, { x: left }, at)
      .to(scan, { opacity: 1, duration: .12 }, at)
      .to(scan, { x: left + width - 3, duration, ease: 'sine.inOut' }, at + .06)
      .to(label, { clipPath: read, duration, ease: 'sine.inOut' }, at + .06)
      .to(scan, { opacity: 0, duration: .15 }, at + .06 + duration);
  }

  function play() {
    rest();
    const stage = $('.stage').getBoundingClientRect();
    const gate = $('.gate').getBoundingClientRect();
    const left = (element) => element.getBoundingClientRect().left - stage.left;
    const x = (element) => Number(gsap.getProperty(element, 'x'));
    // Offset that puts an element's left edge at a stage position.
    const to = (element, position) => position - left(element) + x(element);
    const camel = $('.stage-camel');
    const start = getComputedStyle(camel).opacity === '0' ? 12 : left(camel) + camel.offsetWidth + 16;
    const site = $('.site-node').getBoundingClientRect();
    // Pieces end behind the site box, never past its far edge.
    const home = (element) => Math.min(site.left, site.right - element.offsetWidth) - stage.left;
    timeline = gsap.timeline({
      paused: true,
      onComplete() {
        if (!auto) return rest();
        rest();
        setMode(demo.dataset.mode === 'off' ? 'on' : 'off');
        play();
      }
    });
    phase('reading');

    if (demo.dataset.mode === 'off') {
      const stop = left(whole);
      const stopX = x(whole);
      gsap.set(whole, { x: to(whole, Math.max(4, Math.min(start, stop - 24))), opacity: 0 });
      gsap.set(readOff, { clipPath: unread });
      timeline
        .to(whole, { opacity: 1, duration: .3 }, .1)
        .to(whole, { x: stopX, duration: 1, ease: travel }, .1);
      sweep(whole, stop, readOff, .8, 1.15);
      timeline.call(phase, [''], 2.15).to({}, { duration: .3 });
      if (auto) {
        timeline
          .to({}, { duration: hold })
          .to([whole, readOff], { opacity: 0, duration: .35, ease: 'power1.out' })
          .call(phase, ['reading'], '<')
          .to({}, { duration: .15 });
      }
    } else {
      const restA = x(a);
      const restB = x(b);
      const leftA = left(a);
      const leftB = left(b);
      const gap = a.offsetWidth;
      // Cut so that the two halves sit exactly on the whole packet's letters.
      const pad = parseFloat(getComputedStyle(a).paddingRight);
      const cut = whole.offsetWidth - b.offsetWidth;
      const from = Math.max(8, Math.min(left(whole), leftB - cut) - 24);
      const split = Math.min(14, from - 4);
      const arch = gate.left - stage.left + (gate.width - gap) / 2;
      gsap.set(whole, { x: to(whole, Math.min(start, from)), opacity: 0 });
      gsap.set(a, { x: to(a, from), opacity: 0, clipPath: `inset(0 ${pad}px 0 0px)` });
      gsap.set(b, { x: to(b, from + cut), opacity: 0, clipPath: `inset(0 0px 0 ${pad}px)` });
      gsap.set([readA, readB], { clipPath: unread });
      gsap.set(readLine, { opacity: 0 });
      // It sets out whole, then parts.
      timeline
        .to(whole, { opacity: 1, duration: .3 }, .1)
        .to(whole, { x: to(whole, from), duration: .7, ease: travel }, .1)
        .set(whole, { opacity: 0 }, .9)
        .set([a, b], { opacity: 1 }, .9)
        .to([a, b], { clipPath: 'inset(0 0px 0 0px)', duration: .4, ease: arrive }, .9)
        .to(a, { x: to(a, from - split), duration: .4, ease: arrive }, .9)
        .to(b, { x: to(b, from + gap + 8), duration: .4, ease: arrive }, .9)
        // The first piece lifts over the second, because it is sent first.
        .to(a, { y: -a.offsetHeight - 10, duration: .4, ease: 'sine.inOut' }, 1.35)
        .to(a, { x: to(a, arch), duration: .85, ease: travel }, 1.45)
        .to(a, { y: 0, duration: .4, ease: 'sine.inOut' }, 1.95)
        .to(a, { x: restA, duration: .55, ease: travel }, 2.95)
        .to(b, { x: restB, duration: .6, ease: travel }, 2.75)
        .to(readLine, { opacity: 1, duration: .2 }, 3.3);
      sweep(a, arch, readA, .4, 2.35);
      sweep(b, leftB, readB, .4, 3.35);
      timeline.call(phase, [''], 3.95).to({}, { duration: .3 });
      if (auto) {
        // Both pieces go on to the site, one after the other.
        timeline
          .to({}, { duration: hold })
          .addLabel('go')
          .to(a, { x: restA + home(a) - leftA, duration: .7, ease: travel }, 'go')
          .to(a, { opacity: 0, duration: .2 }, 'go+=.45')
          .call(phase, ['arrived'], 'go+=.55')
          .to(b, { x: restB + home(b) - leftB, duration: 1, ease: travel }, 'go+=.1')
          .to(b, { opacity: 0, duration: .25 }, 'go+=.75')
          .to([readA, readB, readLine], { opacity: 0, duration: .35 }, 'go+=1.3')
          .call(phase, ['reading'], 'go+=1.3')
          .to({}, { duration: .15 });
      }
    }
    sync();
  }

  const media = gsap.matchMedia();
  media.add('(prefers-reduced-motion: no-preference)', () => {
    let live = true;
    let width = window.innerWidth;
    auto = true;
    held = false;
    setMode('off');
    phase('reading');
    gsap.set([whole, readOff], { opacity: 0 });
    button.hidden = false;
    sync();
    // Once the font has settled, so widths are right.
    document.fonts.ready.then(() => { if (live && !timeline && auto) play(); });

    // A choice made by hand plays that state once and leaves it there.
    const choose = () => { auto = false; held = false; play(); };
    const press = () => {
      if (auto) { held = !held; sync(); return; }
      auto = true;
      held = false;
      setMode(demo.dataset.mode === 'off' ? 'on' : 'off');
      play();
    };
    // Never move the selection under someone's keyboard.
    const focus = () => { if (auto && !held) { held = true; sync(); } };
    const resize = () => {
      if (window.innerWidth === width) return; // mobile address bar
      width = window.innerWidth;
      if (auto) play(); else rest();
    };
    const watch = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }, { threshold: .4 });
    watch.observe($('.stage'));
    demo.addEventListener('kervan:mode', choose);
    button.addEventListener('click', press);
    $('.switch').addEventListener('focusin', focus);
    window.addEventListener('resize', resize);
    return () => {
      live = false;
      watch.disconnect();
      demo.removeEventListener('kervan:mode', choose);
      button.removeEventListener('click', press);
      $('.switch').removeEventListener('focusin', focus);
      window.removeEventListener('resize', resize);
      rest();
      auto = false;
      button.hidden = true;
      sync();
    };
  });
  media.add('(prefers-reduced-motion: reduce)', () => {
    const fade = () => gsap.fromTo($('.stage'), { opacity: .4 }, { opacity: 1, duration: .15, clearProps: 'opacity' });
    demo.addEventListener('kervan:mode', fade);
    return () => demo.removeEventListener('kervan:mode', fade);
  });
})();
