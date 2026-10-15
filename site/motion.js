/* Editorial motion only. Every element is fully readable without this file. */
(() => {
  if (!window.gsap || !window.ScrollTrigger) return;

  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);
  const motionMedia = gsap.matchMedia();

  motionMedia.add('(prefers-reduced-motion: no-preference)', () => {
    let active = true;
    let requestId = 0;
    let diagramTrigger;
    let diagramTimeline;
    let diagramSvg;
    let diagramPlayed = false;
    const sectionTweens = [];
    const sectionTriggers = [];
    const compactArt = window.matchMedia('(max-width: 880px)');
    const compactMotion = window.matchMedia('(max-width: 650px)').matches;
    const art = document.querySelector('.packet-art');
    const picture = art?.querySelector('picture');
    const hero = document.querySelector('.hero');

    hero.dataset.motionState = 'running';
    const heroTimeline = gsap.timeline({
      defaults: { ease: 'power2.out' },
      onComplete: () => { hero.dataset.motionState = 'complete'; }
    });
    heroTimeline
      .fromTo('#hero-title', { opacity: .62, y: compactMotion ? 6 : 10 }, { opacity: 1, y: 0, duration: .48, clearProps: 'opacity,transform' }, 0)
      .fromTo('.hero-description', { opacity: .54, y: compactMotion ? 5 : 8 }, { opacity: 1, y: 0, duration: .38, clearProps: 'opacity,transform' }, .08)
      .fromTo('.hero-actions', { opacity: .55, y: compactMotion ? 5 : 7 }, { opacity: 1, y: 0, duration: .36, clearProps: 'opacity,transform' }, .18)
      .fromTo('.hero-camel', { opacity: .55 }, { opacity: 1, duration: .32, clearProps: 'opacity' }, .22);

    const revealSections = [
      ['#product', '.editorial-grid'],
      ['#diagram', '.diagram-heading'],
      ['#status', '.editorial-grid'],
      ['#story', '.editorial-grid'],
      ['#downloads', '.editorial-grid']
    ];
    revealSections.forEach(([sectionSelector, contentSelector]) => {
      const section = document.querySelector(sectionSelector);
      const content = section.querySelector(contentSelector);
      sectionTriggers.push(ScrollTrigger.create({
        trigger: section,
        start: 'top 84%',
        once: true,
        onEnter: () => {
          if (!active || section.dataset.motionState) return;
          section.dataset.motionState = 'running';
          sectionTweens.push(gsap.fromTo(content,
            { opacity: .78, y: compactMotion ? 6 : 11 },
            {
              opacity: 1, y: 0, duration: compactMotion ? .32 : .4,
              ease: 'power1.out', clearProps: 'opacity,transform',
              onComplete: () => { section.dataset.motionState = 'complete'; }
            }
          ));
        }
      }));
    });

    function restorePicture() {
      if (!diagramSvg || !picture) return;
      picture.querySelector('img').alt = diagramSvg.getAttribute('aria-label') || picture.querySelector('img').alt;
      diagramSvg.replaceWith(picture);
      diagramSvg = undefined;
    }

    function playDiagram() {
      if (!active || !diagramSvg || diagramPlayed) return;
      diagramPlayed = true;
      art.dataset.motionState = 'running';
      const svg = diagramSvg;
      const link = svg.querySelectorAll('[data-motion-stage="link"]');
      const overlays = svg.querySelectorAll('[data-motion-stage="ip"], [data-motion-stage="transport"], [data-motion-stage="protocol"], [data-motion-stage="control"]');
      diagramTimeline = gsap.timeline({
        defaults: { ease: 'power1.out' },
        onComplete: () => {
          gsap.set(svg, { clearProps: 'opacity,transform' });
          gsap.set([...overlays, ...link], { clearProps: 'opacity' });
          art.dataset.motionState = 'complete';
          art.dataset.motionPhase = 'complete';
        }
      });
      diagramTimeline.fromTo(svg,
        { opacity: .7, y: compactMotion ? 5 : 8 },
        { opacity: 1, y: 0, duration: .27 }, 0
      );
      ['ip', 'transport', 'protocol', 'control'].forEach((stage, index) => {
        const overlay = svg.querySelector(`[data-motion-stage="${stage}"]`);
        const at = .28 + index * (compactMotion ? .3 : .36);
        diagramTimeline.call(() => { art.dataset.motionPhase = stage; }, [], at);
        diagramTimeline.fromTo(overlay, { opacity: 0 },
          { opacity: stage === 'protocol' ? .22 : .16, duration: .17 }, at);
        diagramTimeline.to(overlay, { opacity: 0, duration: .19 }, at + .17);
        if (stage === 'control') {
          diagramTimeline.fromTo(link, { opacity: .3 },
            { opacity: 1, duration: .32 }, at);
        }
      });
    }

    async function loadDiagram() {
      if (!art || !picture || !active) return;
      const thisRequest = ++requestId;
      diagramTrigger?.kill();
      diagramTrigger = undefined;
      diagramTimeline?.kill();
      diagramTimeline = undefined;
      restorePicture();
      const asset = compactArt.matches ? 'packet-anatomy-mobile.svg' : 'packet-anatomy.svg';
      try {
        const response = await fetch(`./assets/${asset}`);
        if (!response.ok) return;
        const parsed = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
        if (parsed.querySelector('parsererror') || !active || thisRequest !== requestId) return;
        const svg = document.importNode(parsed.documentElement, true);
        svg.removeAttribute('aria-labelledby');
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', picture.querySelector('img').alt);
        svg.setAttribute('data-i18n-aria', 'diagramAlt');
        svg.setAttribute('focusable', 'false');
        svg.classList.add('packet-svg');
        picture.replaceWith(svg);
        diagramSvg = svg;
        art.dataset.motionState = diagramPlayed ? 'complete' : 'ready';
        if (!diagramPlayed) {
          diagramTrigger = ScrollTrigger.create({
            trigger: art,
            start: 'top 82%',
            once: true,
            onEnter: playDiagram
          });
        }
        ScrollTrigger.refresh();
      } catch (_) {
        // Keep the original picture if the optional enhancement cannot load.
      }
    }

    const onArtworkBreakpoint = () => { if (active) loadDiagram(); };
    compactArt.addEventListener('change', onArtworkBreakpoint);
    loadDiagram();

    return () => {
      active = false;
      requestId++;
      compactArt.removeEventListener('change', onArtworkBreakpoint);
      diagramTrigger?.kill();
      diagramTimeline?.kill();
      heroTimeline.kill();
      sectionTriggers.forEach((trigger) => trigger.kill());
      sectionTweens.forEach((tween) => tween.kill());
      gsap.set(['#hero-title', '.hero-description', '.hero-actions', '.hero-camel', ...revealSections.map(([section, content]) => `${section} ${content}`)], { clearProps: 'opacity,transform' });
      restorePicture();
      delete hero.dataset.motionState;
      delete art.dataset.motionState;
      delete art.dataset.motionPhase;
      revealSections.forEach(([selector]) => { delete document.querySelector(selector).dataset.motionState; });
    };
  });
})();
