// Turkish is the document itself; only English lives here.
const english = {
  skip: "Skip to main content",
  brandHome: "Kervan DPI home",
  navLabel: "Main menu",
  openMenu: "Open menu",
  closeMenu: "Close menu",
  languageLabel: "Choose language",
  navDpi: "What is DPI",
  navHow: "How it works",
  navPlatforms: "Platforms",
  navProgress: "Progress",
  navDownload: "Download",
  navFaq: "Questions",
  heroLine1: "Filters read the name.",
  heroLine2: "Kervan makes it harder.",
  heroLead: "Some networks read which site you are visiting in the first moments of a connection, then cut it off. Kervan DPI is an open-source app built to make that inspection harder, on your own device.",
  heroDownload: "Download options",
  sourceCode: "Source code",
  gateReads: "What the filter sees",
  siteNode: "Site",
  demoTitle: "A conceptual view of a connection with Kervan off and on",
  demoOff: "Kervan off",
  demoOn: "Kervan on",
  resultOff: "The name travels in one piece. The filter recognises it and cuts the connection.",
  resultOn: "The name is split into pieces. The filter cannot see the whole name in one packet.",
  statusOff: "Whole name read",
  statusOn: "Only pieces are visible",
  pauseDemo: "Pause the animation",
  playDemo: "Play the animation",
  demoNote: "Conceptual illustration. The method differs by platform and does not work against every filter.",
  dpiTitle: "The envelope is sealed, but the name on it can be read.",
  dpiLead: "HTTPS encrypts the contents of a page. Even so, the name of the site you are opening is usually sent in the clear while the connection is set up.",
  dpiBody: "Deep packet inspection (DPI) is the network reading that exposed information. If the name is on a blocklist, the connection can be reset. Some networks also alter the DNS answer before that; it is a separate layer and needs a separate solution.",
  envIp: "IP address",
  envIpState: "Visible to the network",
  envName: "Site name",
  envNameState: "Usually readable",
  envBody: "Pages, passwords, messages",
  envBodyState: "Encrypted by HTTPS",
  howTitle: "Works when you turn it on, steps back when you turn it off.",
  step1Title: "You turn it on",
  step1Body: "Kervan does not start unless you ask; on desktop, running at sign-in is optional. If administrator or system permission is needed, your operating system asks you.",
  step2Title: "An engine starts on your device",
  step2Body: "Each platform uses an open-source engine suited to it. There is no Kervan server in between.",
  step3Title: "The start of the connection is reshaped",
  step3Body: "The engine splits or adjusts the first packets of new connections. Your content is not opened or decrypted.",
  step4Title: "Turning it off cleans up",
  step4Body: "When you stop it, the app undoes the changes it made. Recovery after a crash is tested separately on each platform.",
  platformsTitle: "Four platforms, four different roads.",
  platformsLead: "Operating systems allow access to network traffic in different ways, so the engine, the scope and the level of evidence differ on each platform.",
  tabsLabel: "Choose a platform",
  fScope: "Scope",
  fEvidence: "Verified",
  fMissing: "Missing",
  winState: "Release candidate available",
  winLead: "A desktop app that manages GoodbyeDPI and WinDivert from one window.",
  winScope: "System-wide. Needs administrator permission.",
  winEvidence: "v1.0.1-rc2: the Windows build and 126 automated tests passed.",
  winMissing: "Extensive testing of this build in a real Windows session is not complete. The EXE is not digitally signed.",
  linState: "Coming soon: in development, not released",
  linLead: "A desktop app with a SpoofDPI local proxy mode and an experimental Zapret2 system-wide mode.",
  linScope: "In proxy mode, only apps that use the proxy; in experimental mode, new HTTPS connections. DNS protection is optional.",
  linEvidence: "DNS 8.1: 93 of 93 checks passed on Debian 13, Ubuntu 24.04 and Kali virtual machines.",
  linMissing: "Trying DNS 8.1 on a real machine and verifying bypass with this build. 93/93 measures DNS integration; it is not proof of bypass.",
  andState: "Public beta available",
  andLead: "A native app that uses Android’s VPN permission locally. It does not connect to a remote VPN server.",
  andScope: "App traffic on the device, through a local tunnel (hev-socks5-tunnel and ByeDPI).",
  andEvidence: "0.2.0-beta1: 39 unit tests passed; installed, turned on and turned off on a Redmi Note 10S (Android 13). One blocked site opened only with Kervan on, on one mobile and one Wi-Fi network (the Wi-Fi check used an earlier debug build).",
  andMissing: "QUIC/UDP, switching networks while on, recovery from an engine crash and long sessions are not fully validated. Results may differ on other devices and networks.",
  iosState: "Coming soon: development version, not downloadable",
  iosLead: "A native app that uses Apple’s packet tunnel framework on the device.",
  iosScope: "Device traffic, through a local packet tunnel. There is no remote VPN server.",
  iosEvidence: "Reported by the developer: the signed app was installed on a real iPhone 14 Pro; the tunnel and basic HTTPS connectivity were tried.",
  iosMissing: "Bypass has not been conclusively shown. There is no App Store or TestFlight distribution.",
  progressTitle: "We say plainly where we are.",
  progressLead: "Passing one stage does not prove the next. The table reflects 25 November 2026.",
  thPlatform: "Platform",
  thAuto: "Automated tests",
  thVm: "Virtual environment",
  thReal: "Real device",
  thBypass: "Bypass",
  thPublic: "Public download",
  cPass: "Passed",
  cNone: "None",
  cPartial: "Partial",
  cNoRecord: "Not measured in this build",
  cPre: "Release candidate",
  cDns: "DNS 93/93",
  cLinBypass: "Reported on an earlier build",
  cEmu: "Emulator passed",
  cAndReal: "Passed on one phone",
  cAndBypass: "Seen with one site on two networks",
  cBeta: "Beta",
  cSoon: "Coming soon",
  cSim: "Simulator passed",
  cIosReal: "Installed, HTTPS tried",
  cNotShown: "Not shown",
  downloadTitle: "What you can download today",
  getAndBody: "A public, experimental beta. Android 10 or later on arm64 or x86_64. It does not work on every network.",
  getAndButton: "Download the Android APK",
  getAndNotes: "Release notes and SHA-256",
  getAndStep1: "Download the APK and compare its hash with SHA256SUMS on the release page.",
  getAndStep2: "If Android asks, allow your browser to install this app, then remove that permission.",
  getAndStep3: "Tap Turn on in the app and approve the VPN request. Only one VPN can run at a time.",
  getBody: "A release candidate published under the Kervan DPI name. It is not a stable release and the EXE is not signed, so Windows may show a security warning.",
  getButton: "Open the Windows release on GitHub",
  getStep1: "Download the file and the SHA-256 list from the same release page.",
  getStep2: "Compare the hash in PowerShell:",
  getStep3: "Run it if the hash matches. If it does not, delete the file and report it.",
  codeLabel: "PowerShell command",
  otherTitle: "Linux and iOS: coming soon",
  otherBody: "No package has been published under the Kervan DPI name for Linux or iOS yet. If you find one elsewhere, it is not from this project.",
  legacyTitle: "Older releases",
  legacyBody: "v1.0.0 and v1.0.1-rc1 were published under the project’s former name, GoodbyeDPI Turkey. The Linux packages in rc1 belong to that older version and are not the current Kervan DPI.",
  allReleases: "See all releases",
  limitsTitle: "What Kervan is not",
  limit1: "It is not a VPN service. On mobile it uses the system’s VPN permission, but connects to no remote server.",
  limit2: "It does not hide your IP address or make you anonymous.",
  limit3: "It adds no new encryption to your traffic.",
  limit4: "It does not guarantee access on every network or to every site.",
  limit5: "Following the laws where you are is your responsibility.",
  faqTitle: "Frequently asked questions",
  q1: "Is Kervan DPI safe?",
  a1: "The source code is open, and the app has no account, ads or analytics. Even so, the pre-releases have not had an independent security audit. Get files only from this project’s GitHub page and verify their hashes.",
  q2: "Does my data pass through a server?",
  a2: "Kervan has no server. Your traffic is processed on your device and goes to its destination over your own internet connection. The DNS provider you choose and the sites you visit apply their own privacy rules.",
  q3: "What if a site still does not open?",
  a3: "The block may be in DNS or use another method. First try other sites on the same network with Kervan off. If the problem continues, report it on GitHub with your operating system, version and steps.",
  q4: "Why is there no Linux or iOS download?",
  a4: "The Linux version is in development. The iOS app has run on a real iPhone, but bypass is not proven and public distribution is not ready. They will be announced here when they are.",
  q5: "Does it cost anything?",
  a5: "No. The application code is MIT licensed. The engines it works with, and Qt, have their own licences.",
  q6: "Why the name Kervan?",
  a6: "Kervan means caravan: it keeps walking even when the road gets hard. It is a metaphor; the app does not send your traffic along another route.",
  osTitle: "We stand on other people’s work.",
  osLead: "The engines are independent projects. Kervan DPI manages them; they belong to their own developers.",
  cr1: "Windows engine, Apache 2.0",
  cr2: "Windows packet driver, LGPL 3.0",
  cr3: "Linux local proxy, Apache 2.0, installed separately",
  cr4: "Experimental Linux engine, MIT",
  cr5: "Mobile engine, MIT",
  cr6: "Mobile tunnel, MIT",
  cr7: "Desktop interface, LGPL 3.0",
  camelAlt: "Kervan DPI blue camel mark",
  sloganNote: "The road is open, the caravan moves.",
  madeBy: "Developer",
  footerNav: "Project links",
  repo: "Project repository",
  docs: "Documentation",
  issues: "Report a problem",
  license: "License",
  notices: "Third-party notices",
  footerSmall: "© 2026 MacallanTheRoot. This site uses no cookies or trackers; it sends one request to GitHub to find the latest Windows release."
};
const meta = {
  tr: { title: document.title, description: document.querySelector('meta[name="description"]').content },
  en: {
    title: 'Kervan DPI: an open-source DPI tool',
    description: 'Kervan DPI is an open-source app built against the deep packet inspection (DPI) some networks use to block sites. Status for Windows, Linux, Android and iOS.'
  }
};
const root = document.documentElement;
const targets = [
  ['i18n', (el) => el.textContent, (el, v) => { el.textContent = v; }],
  ['i18nAria', (el) => el.getAttribute('aria-label'), (el, v) => el.setAttribute('aria-label', v)],
  ['i18nAlt', (el) => el.alt, (el, v) => { el.alt = v; }]
];
const turkish = new Map([['closeMenu', 'Menüyü kapat'], ['playDemo', 'Animasyonu oynat'], ['sloganNote', '']]);
for (const [name, read] of targets) {
  const selector = '[data-' + name.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase()) + ']';
  document.querySelectorAll(selector).forEach((el) => {
    if (!turkish.has(el.dataset[name])) turkish.set(el.dataset[name], read(el));
  });
}
const text = (key, language = root.lang) => (language === 'en' ? english[key] : turkish.get(key)) ?? turkish.get(key);

/* Menu */
const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.primary-nav');
function setMenu(open) {
  nav.classList.toggle('is-open', open);
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', text(open ? 'closeMenu' : 'openMenu'));
}
menuButton.addEventListener('click', () => setMenu(menuButton.getAttribute('aria-expanded') !== 'true'));
nav.addEventListener('click', (event) => { if (event.target.closest('a')) setMenu(false); });
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
    setMenu(false);
    menuButton.focus();
  }
});
document.addEventListener('click', (event) => { if (!event.target.closest('.site-header')) setMenu(false); });

/* Language */
function setLanguage(language) {
  root.lang = language;
  for (const [name, , write] of targets) {
    const selector = '[data-' + name.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase()) + ']';
    document.querySelectorAll(selector).forEach((el) => write(el, text(el.dataset[name], language)));
  }
  document.querySelectorAll('[data-language]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.language === language));
  });
  document.title = meta[language].title;
  document.querySelector('meta[name="description"]').content = meta[language].description;
  document.querySelector('.slogan-en').hidden = language !== 'en';
  const heads = [...document.querySelectorAll('thead th')].map((th) => th.textContent);
  document.querySelectorAll('tbody tr').forEach((row) => {
    row.querySelectorAll('td').forEach((cell, i) => { cell.dataset.label = heads[i + 1]; });
  });
  setMenu(false);
}
document.querySelectorAll('[data-language]').forEach((button) => {
  button.addEventListener('click', () => {
    setLanguage(button.dataset.language);
    try { localStorage.setItem('kervan-language', button.dataset.language); } catch (_) { /* Storage can be unavailable. */ }
  });
});

/* Platform tabs (ARIA APG, automatic activation). Without JavaScript every panel is shown. */
const tabList = document.querySelector('.tab-list');
const tabs = [...tabList.querySelectorAll('a')];
const panelOf = (tab) => document.getElementById(tab.hash.slice(1));
tabList.setAttribute('role', 'tablist');
tabs.forEach((tab) => {
  tab.setAttribute('role', 'tab');
  tab.setAttribute('aria-controls', tab.hash.slice(1));
  const panel = panelOf(tab);
  panel.setAttribute('role', 'tabpanel');
  panel.setAttribute('aria-labelledby', tab.id);
  panel.tabIndex = 0;
});
function selectTab(tab, focus) {
  tabs.forEach((item) => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    panelOf(item).hidden = !selected;
  });
  if (focus) tab.focus();
}
tabList.addEventListener('click', (event) => {
  const tab = event.target.closest('a');
  if (tab) { event.preventDefault(); selectTab(tab, true); }
});
tabList.addEventListener('keydown', (event) => {
  const index = tabs.indexOf(document.activeElement);
  const next = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 }[event.key];
  if (event.key === ' ') { event.preventDefault(); selectTab(tabs[index], true); }
  if (next === undefined || index < 0) return;
  event.preventDefault();
  selectTab(tabs[(next + tabs.length) % tabs.length], true);
});
selectTab(tabs.find((tab) => tab.hash === location.hash) || tabs[0]);

/* Scene: CSS draws both states; motion.js may animate between them. */
const demo = document.getElementById('demo');
demo.querySelectorAll('input[name="kervan"]').forEach((input) => {
  input.addEventListener('change', () => {
    demo.dataset.mode = input.value;
    demo.dispatchEvent(new Event('kervan:mode'));
  });
  // A click on the option already chosen plays it again.
  input.addEventListener('click', () => { if (demo.dataset.mode === input.value) demo.dispatchEvent(new Event('kervan:mode')); });
});
// Some browsers restore the radio on reload.
demo.dataset.mode = demo.querySelector('input[name="kervan"]:checked').value;

/* /releases/latest excludes prereleases, so find the newest published Windows binary. */
const windowsReleasesPage = 'https://github.com/MacallanTheRoot/kervan-dpi/releases';
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
    document.getElementById('windows-release-link').href = latest.html_url;
    // The text beside it describes a pre-release; show another version only if it is one.
    if (latest.prerelease === true) document.getElementById('windows-release-version').textContent = latest.tag_name;
  } catch (_) {
    // The Releases page remains a working fallback even without the API.
  }
}

root.classList.replace('no-js', 'js');
let saved;
try { saved = localStorage.getItem('kervan-language'); } catch (_) { /* Storage can be unavailable. */ }
const asked = new URLSearchParams(location.search).get('lang');
setLanguage((asked || saved) === 'en' ? 'en' : 'tr');
resolveLatestWindowsRelease();
