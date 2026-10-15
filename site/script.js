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
    productWindows: 'Controls the bundled GoodbyeDPI and WinDivert components. Windows v1.0.1-rc2 is available as a prerelease; full native QA remains pending.',
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
    statusAside: 'The Windows prerelease is available; Linux and mobile releases are not yet published.',
    statusWindows: 'The Windows prerelease is published. Full real-device QA is still pending.',
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
    releaseLabel: 'Windows prerelease',
    releaseBody: 'Windows v1.0.1-rc2 is available as a prerelease. Linux K4 has not been published.',
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
const releaseLabels = {
  tr: { prerelease: 'Son ön sürüm ↗', stable: 'Son sürüm ↗', aria: 'Son Windows sürümünü GitHub’da aç' },
  en: { prerelease: 'Latest pre-release ↗', stable: 'Latest release ↗', aria: 'Open the latest Windows release on GitHub' }
};
let latestWindowsRelease = {
  url: 'https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc2',
  version: 'v1.0.1-rc2',
  prerelease: true
};

function updateWindowsReleaseLink(language) {
  const label = releaseLabels[language];
  windowsReleaseLink.href = latestWindowsRelease.url;
  windowsReleaseLink.textContent = latestWindowsRelease.prerelease ? label.prerelease : label.stable;
  windowsReleaseLink.setAttribute('aria-label', label.aria);
  windowsReleaseVersion.textContent = latestWindowsRelease.version;
}

// GitHub's /releases/latest redirects to stable releases only, skipping prereleases.
// Query the public releases API to include published prereleases with Windows binaries.
// A verified RC2 link remains usable when the API is unavailable or rate limited.
async function resolveLatestWindowsRelease() {
  try {
    const response = await fetch('https://api.github.com/repos/MacallanTheRoot/kervan-dpi/releases?per_page=30', {
      headers: { Accept: 'application/vnd.github+json' }
    });
    if (!response.ok) return;
    const releases = await response.json();
    if (!Array.isArray(releases)) return;
    const candidates = releases.filter((release) =>
      !release.draft &&
      typeof release.html_url === 'string' &&
      release.html_url.startsWith('https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/') &&
      typeof release.tag_name === 'string' &&
      Array.isArray(release.assets) &&
      release.assets.some((asset) => asset.state === 'uploaded' && (
        asset.name === 'Kervan-DPI.exe' ||
        /^Kervan-DPI-.*-windows-portable\\.zip$/i.test(asset.name)
      ))
    );
    candidates.sort((a, b) => Date.parse(b.published_at || 0) - Date.parse(a.published_at || 0));
    const latest = candidates[0];
    if (!latest) return;
    latestWindowsRelease = {
      url: latest.html_url,
      version: latest.tag_name,
      prerelease: latest.prerelease === true
    };
    updateWindowsReleaseLink(document.documentElement.lang);
  } catch (_) {
    // Network/API failures must not break the site's static release link.
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
