# Kervan DPI website preview · V3

A bilingual Turkish/English static website. Runtime files are plain HTML, CSS, JavaScript, the approved camel PNG, original packet-diagram SVGs, and locally vendored GSAP. No build step, framework, or external font request is required.

## Preview

From the repository root:

```sh
python3 -m http.server 8765 --directory site
```

Open <http://localhost:8765/>. Relative stylesheet, script, and image paths also work when these files are served at `/kervan-dpi/`.

## Editorial design

The off-white page places an oversized product statement beside concise engine facts. The approved blue camel mark stays small. Type, asymmetric columns, whitespace, and thin rules carry the hierarchy; navy supports the brand story and footer. The packet diagrams are original conceptual drawings in desktop and mobile arrangements. They distinguish packet fields that DPI may inspect from the application's separate engine controls. They are not exact packet formats or claims of traffic rerouting or verified bypass. No authentic Fix04 screenshot was found in the available repository assets, so the site does not show a fabricated one.

Key colors: navy `#0b1724`, paper `#f4f3ee`, ink `#151e25`, blue `#08679f`. Keyboard focus uses blue on paper and light blue on navy. Content width is 1240 px. Layout changes at 880 and 650 px, with a further compact adjustment at 430 px.

## Motion

`motion.js` adds a short hero timeline, one-time section reveals, and a one-time packet sequence. It uses only opacity and small translations for page content. The diagram sequence briefly emphasizes the existing conceptual IP, transport, protocol, and UI-to-engine elements. The original `<picture>` remains visible when JavaScript is disabled or the optional SVG enhancement fails. Reduced-motion users see all content immediately, with no entrance or scroll animation. CSS handles hover feedback and the mobile menu.

GSAP core and ScrollTrigger are pinned at **3.15.0** and served from `vendor/gsap/`; no CDN is needed. Their original license headers remain in the files. See [the vendor notice](vendor/gsap/NOTICE.md) for GreenSock's Standard License and source. GSAP is not covered by this repository's MIT license.

## Product boundaries

Windows Fix04 was locally tested and remains on public-release HOLD. Linux K4 passed offline tests; native system-wide bypass is unverified. Android and iOS are planned. Public `v1.0.1-rc1` belongs to the older GoodbyeDPI Turkey identity and is not either current candidate. The page makes no VPN, anonymity, IP masking, or universal access claim.

The owner confirms that the approved blue camel image was generated through ChatGPT specifically for Kervan DPI. The website copy is byte-for-byte identical to `assets/kervan-camel.png`; its source and export hashes are recorded in `docs/branding/kervan-camel-source.md`. No trademark registration, exclusivity, or MIT license is claimed for the image. Public publication remains subject to owner authorization. The footer links to the application license and third-party notices.

## GitHub Pages proposal · not executed

The GitHub repository is already [MacallanTheRoot/kervan-dpi](https://github.com/MacallanTheRoot/kervan-dpi). A manual-only workflow is prepared at `.github/workflows/pages.yml`; it uploads an explicit ten-file website artifact, excluding this README, screenshots, and application sources. After owner authorization and the artwork rights review, set Pages source to GitHub Actions, dispatch the workflow from `main`, then verify `https://macallantheroot.github.io/kervan-dpi/` and its links. Do not rename the local directory or change its remote as part of website work. No commit, push, tag, release, or Pages publication was performed for this preview.
