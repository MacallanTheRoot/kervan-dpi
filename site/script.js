const translations = {
  tr: {},
  en: {
    skip: 'Skip to main content',
    brandHome: 'Kervan DPI — home',
    navLabel: 'Main navigation',
    openMenu: 'Open menu',
    closeMenu: 'Close menu',
    navProduct: 'Product',
    navDiagram: 'Diagram',
    navStatus: 'Status',
    navStory: 'Why Kervan?',
    navDownloads: 'Open source',
    heroType: ' / open-source desktop project',
    heroLine1: 'A desktop interface',
    heroLine2: 'for DPI tools.',
    heroSummaryLabel: 'Product summary',
    heroDescription: 'Kervan DPI is being developed to start, stop, and monitor engines used to address DPI-related access restrictions from one window.',
    heroGithub: 'Explore the source code',
    heroStatus: 'Check release status',
    camelAlt: 'Kervan DPI blue camel symbol',
    heroLinux: 'SpoofDPI / local proxy',
    productIndex: '01 / Product',
    productTitle: 'What does the desktop app do?',
    productLead: 'Kervan DPI provides a Qt interface to start and stop the selected engine and watch its state. DNS selection and an activity log are in the same window.',
    flowLabel: 'Application workflow',
    flow1: 'Choose settings',
    flow3: 'Check status',
    productWindows: 'Controls the bundled GoodbyeDPI and WinDivert components. Windows releases are available on GitHub; prereleases may still require full native QA.',
    productLinux: 'Can start a separately installed SpoofDPI local HTTP proxy. The browser or application must explicitly use that proxy.',
    diagramIndex: '02 / Diagram',
    diagramTitle: 'Inside a packet',
    diagramIntro: 'DPI can examine connection and protocol fields. Kervan DPI manages the selected engine’s start and stop controls.',
    diagramAlt: 'Conceptual technical drawing of packet fields, a possible DPI inspection region, and separate engine controls',
    diagramKey1: 'IP and transport headers',
    diagramKey2: 'Application protocol fields',
    diagramKey3: 'Engine control from the interface',
    diagramNote: 'Conceptual drawing only. It does not depict an exact packet format, traffic routing, or verified system-wide bypass.',
    statusIndex: '03 / Status',
    statusTitle: 'Current status',
    statusAside: 'Windows releases are available; Linux and mobile releases are not yet published.',
    statusWindows: 'Windows releases are published. Prereleases may not yet have completed full real-device QA.',
    statusLinux: 'Offline tests passed. Native system-wide bypass has not yet been verified.',
    statusUnpublished: 'Unpublished',
    statusAndroid: 'A mobile app is planned; no tested release exists.',
    statusIos: 'A mobile app is planned; no tested release exists.',
    statusPlanned: 'Planned',
    storyIndex: '04 / Name',
    storyTitle: 'Why Kervan?',
    storyLead: 'When a caravan finds its road closed, it looks for another way to continue its journey.',
    storyBody: 'The name Kervan reflects a determination to find solutions to DPI-related access restrictions. It is a metaphor for persistence; the application does not reroute IP traffic.',
    downloadsIndex: '05 / Open source',
    downloadsTitle: 'Code, documentation, and releases',
    downloadsLead: 'Development is visible on GitHub. The source code, documentation, and published releases are available there.',
    sourceLink: 'Source code',
    docsLink: 'Documentation',
    contributeLink: 'Contribute or report an issue',
    releasesLink: 'All releases',
    releaseLabel: 'Windows releases',
    releaseBody: 'Browse Windows releases on GitHub Releases. Linux K4 has not been published.',
    boundaryNote: 'Kervan DPI is not a VPN, anonymity tool, or IP masking tool. It cannot guarantee access on every network.',
    licenseNote: 'The application code is MIT licensed. GoodbyeDPI, WinDivert, SpoofDPI, and Zapret2 are independent upstream projects; their licenses and notices are documented separately.',
    footerCredit: 'Developed by MacallanTheRoot.',
    issuesLink: 'Report an issue',
    licenseLink: 'License',
    noticesLink: 'Third-party notices',
    footerAttribution: 'GoodbyeDPI, WinDivert, SpoofDPI, and Zapret2 are independent upstream projects.'
  }
};

const sourceText = new Map();
document.querySelectorAll('[data-i18n], [data-i18n-aria], [data-i18n-alt]').forEach((element) => {
  const key = element.dataset.i18n || element.dataset.i18nAria || element.dataset.i18nAlt;
  const value = element.dataset.i18n
    ? element.textContent
    : element.dataset.i18nAria
      ? element.getAttribute('aria-label')
      : element.getAttribute('alt');
  sourceText.set(key, value);
});


const windowsReleaseLink = document.querySelector('#windows-release-link');
const windowsReleaseVersion = document.querySelector('#windows-release-version');
const windowsReleasesPage = 'https://github.com/MacallanTheRoot/kervan-dpi/releases';
const releaseLabels = {
  tr: {
    prerelease: 'Son ön sürüm ↗',
    stable: 'Son sürüm ↗',
    fallback: 'Sürümleri gör ↗',
    aria: 'Son Windows sürümünü GitHub’da aç',
    fallbackAria: 'Windows sürümlerini GitHub’da aç'
  },
  en: {
    prerelease: 'Latest pre-release ↗',
    stable: 'Latest release ↗',
    fallback: 'View releases ↗',
    aria: 'Open the latest Windows release on GitHub',
    fallbackAria: 'View Windows releases on GitHub'
  }
};

// On network errors or GitHub API rate limits, link to the live Releases list,
// not an old fixed release tag. No per-release HTML edits are necessary.
let latestWindowsRelease = null;

function updateWindowsReleaseLink(language) {
  const label = releaseLabels[language];
  windowsReleaseLink.href = latestWindowsRelease?.url || windowsReleasesPage;
  windowsReleaseLink.textContent = !latestWindowsRelease
    ? label.fallback
    : latestWindowsRelease.prerelease ? label.prerelease : label.stable;
  windowsReleaseLink.setAttribute(
    'aria-label', latestWindowsRelease ? label.aria : label.fallbackAria
  );
  windowsReleaseVersion.textContent = latestWindowsRelease?.version || 'Windows x64';
}

// /releases/latest excludes prereleases, so discover the newest published Windows
// binary through the GitHub Releases API. Ignore Linux-only and source-only releases.
async function resolveLatestWindowsRelease() {
  try {
    const response = await fetch(
      'https://api.github.com/repos/MacallanTheRoot/kervan-dpi/releases?per_page=100',
      { headers: { Accept: 'application/vnd.github+json' } }
    );
    if (!response.ok) return;
    const releases = await response.json();
    if (!Array.isArray(releases)) return;
    const isWindowsAsset = (asset) =>
      asset.state === 'uploaded' &&
      typeof asset.name === 'string' &&
      (/^Kervan[-_. ]?DPI.*\.exe$/i.test(asset.name) ||
        (/^Kervan[-_. ]?DPI.*windows.*\.zip$/i.test(asset.name) &&
          !/source|symbols|debug/i.test(asset.name)));
    const candidates = releases.filter((release) =>
      !release.draft &&
      typeof release.published_at === 'string' &&
      typeof release.html_url === 'string' &&
      release.html_url.startsWith(windowsReleasesPage + '/tag/') &&
      typeof release.tag_name === 'string' &&
      Array.isArray(release.assets) &&
      release.assets.some(isWindowsAsset)
    );
    candidates.sort((a, b) =>
      Date.parse(b.published_at) - Date.parse(a.published_at)
    );
    const latest = candidates[0];
    if (!latest) return;
    latestWindowsRelease = {
      url: latest.html_url,
      version: latest.tag_name,
      prerelease: latest.prerelease === true
    };
    updateWindowsReleaseLink(document.documentElement.lang);
  } catch (_) {
    // The Releases page remains a working fallback even without the API.
  }
}

const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.primary-nav');

function closeMenu() {
  nav.classList.remove('is-open');
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.setAttribute('aria-label', translations[document.documentElement.lang].openMenu || sourceText.get('openMenu'));
}

function setLanguage(language) {
  const strings = translations[language];
  document.documentElement.lang = language;

  document.querySelectorAll('[data-i18n]').forEach((element) => {
    element.textContent = strings[element.dataset.i18n] || sourceText.get(element.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-aria]').forEach((element) => {
    element.setAttribute('aria-label', strings[element.dataset.i18nAria] || sourceText.get(element.dataset.i18nAria));
  });
  document.querySelectorAll('[data-i18n-alt]').forEach((element) => {
    element.setAttribute('alt', strings[element.dataset.i18nAlt] || sourceText.get(element.dataset.i18nAlt));
  });
  document.querySelectorAll('[data-language]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.language === language));
  });

  document.title = language === 'tr'
    ? 'Kervan DPI — Yol Açık, Kervan Yürür.'
    : 'Kervan DPI — The road is open, the caravan moves.';
  document.querySelector('meta[name="description"]').content = language === 'tr'
    ? 'Kervan DPI, DPI kaynaklı erişim kısıtlamalarında kullanılan motorları başlatmak, durdurmak ve izlemek için geliştirilen açık kaynaklı masaüstü uygulamasıdır.'
    : 'Kervan DPI is an open-source desktop application for starting, stopping, and monitoring engines used to address DPI-related access restrictions.';

  updateWindowsReleaseLink(language);
  try { localStorage.setItem('kervan-language', language); } catch (_) { /* Storage can be unavailable. */ }
  closeMenu();
}

document.querySelectorAll('[data-language]').forEach((button) => {
  button.addEventListener('click', () => setLanguage(button.dataset.language));
});
menuButton.addEventListener('click', () => {
  const isOpen = nav.classList.toggle('is-open');
  menuButton.setAttribute('aria-expanded', String(isOpen));
  menuButton.setAttribute('aria-label', isOpen
    ? (translations[document.documentElement.lang].closeMenu || 'Menüyü kapat')
    : (translations[document.documentElement.lang].openMenu || sourceText.get('openMenu')));
});
nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeMenu();
});

let savedLanguage;
try { savedLanguage = localStorage.getItem('kervan-language'); } catch (_) { /* Storage can be unavailable. */ }
setLanguage(savedLanguage === 'en' ? 'en' : 'tr');
document.documentElement.classList.remove('no-js');
resolveLatestWindowsRelease();
