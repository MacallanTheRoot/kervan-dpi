# Kervan DPI blue camel artwork — source and icon exports

The user-designated Kervan symbol was located at `/home/macallan/Downloads/Minimalist Mavi Deve İkonu.png` during STEP 02. It is a 1254 × 1254 RGB PNG showing a minimalist blue camel on a dark navy background. The original bytes were copied unchanged to `assets/kervan-camel-source.png` (SHA-256 `ee6ebe53c70be47126777e836485ef36e525cb994d6a384f199018a4368835d5`). The file name and appearance match the approved symbol description; creator identity, written assignment/license and other provenance have **not** been independently established. Record them before public distribution.

To reproduce the application icons from the checked-in source:

```text
.venv/bin/python packaging/generate_kervan_icon.py assets/kervan-camel-source.png
```

On Windows, use `.venv\Scripts\python.exe` instead. The script checks the exact source SHA-256 and dimensions, removes only the dark navy matte using a fixed green-minus-red chroma range, recovers anti-aliased edge alpha, centers the complete original silhouette in a padded square, and scales with integer bilinear interpolation in premultiplied alpha, avoiding platform-specific Qt scaling and painter rounding. It writes transparent `assets/kervan-camel.png` (256 px, SHA-256 `d8c50fe84cdb362a45d3382e422a0650ecdf4e191fab5b247e0b6f5c3cedf2e3`) and `assets/kervan-camel.ico` (PNG frames at 16, 24, 32, 48, 64, 128 and 256 px; SHA-256 `2776b8ae4a81842d18053ab1cea1bc8778891d8e05c85077d58e592bb983a0cb`). No camel shape is redrawn or replaced.

`tests/test_windows_branding.py` checks source identity, frame sizes, alpha/canvas margins and Windows/Qt references. The original RGB source intentionally retains its navy background; the application PNG and ICO use transparent backgrounds. Linux's legacy desktop icon/package identity remains separate. Source rendering and headless Qt inspection do not verify native Windows Explorer, taskbar, UAC, tray or high-DPI appearance; record those results against the final EXE.
