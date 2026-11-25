# Kervan DPI website

Static Turkish/English site for GitHub Pages: plain HTML, CSS and JavaScript, no build step and no third-party requests except one call to the GitHub Releases API.

## Preview

```sh
python3 -m http.server 8765 --directory site
```

Open <http://localhost:8765/> (add `?lang=en` for English). All paths are relative, so it also works under `/kervan-dpi/`.

## Design

Night to day and back: a navy hero, daylight sections, a navy close. Colours come from the approved camel mark; ember `#ffab85` means only "cut off". Type is Instrument Sans (OFL 1.1, self-hosted subset), condensed and tight at display sizes.

One thing moves, on a loop with a pause button: the hero scene, where a packet carrying a site's name meets a caravanserai gate that reads it, with Kervan off or on. CSS draws both end states, so it is complete without JavaScript, without GSAP and with reduced motion. `motion.js` (GSAP core 3.15.0) only plays the journey between them. Platform tabs follow the ARIA tabs pattern; without JavaScript every panel is shown.

## Content

Turkish is the document; English lives in `script.js`. Change both together. Status claims and the progress table are dated; update the date when they change. Never state bypass, VPN, anonymity or downloads beyond the evidence. Pre-release wording beside the Windows link must be reviewed when a stable version ships.

## Publishing

`.github/workflows/pages.yml` is manual-only and stages an explicit ten-file list; add any new asset there. `assets/packet-anatomy*.svg` and `vendor/gsap/ScrollTrigger.min.js` are no longer used or staged.
