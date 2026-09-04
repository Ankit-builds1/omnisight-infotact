# open-sauce.js

Playwright script that automates a full checkout run on [saucedemo.com](https://saucedemo.com), capturing self-contained screenshot+HTML+asset bundles for every page at desktop and mobile viewport sizes, plus a deliberately broken UI state with a before/after/fix comparison and an automatic visual diff — organized into a clean/broken/after/diff dataset for testing.

## What it does, step by step

1. **Login** — logs in as `standard_user` / `secret_sauce` on saucedemo.com, using `page.type()` with a small delay (instead of `fill()`) so the typing is actually visible when running headed.

2. **Product detail page** — clicks into the first product's own page (not just the list view) before adding anything to the cart.

3. **Add to cart** — adds multiple products to the cart (not just one), so the cart screenshot actually shows a multi-item cart. Logs the cart badge count to confirm it worked.

4. **Checkout flow** — clicks into the cart, hits Checkout, fills in the checkout info form with dummy data (first name, last name, zip), continues through to the order overview, and clicks Finish. Waits for the "Thank you for your order" confirmation page to confirm the run succeeded.

5. **Screenshot + HTML + real assets, all together, per page** — every capture point gets its own folder named after the page, and everything (the `.png`, the `.html`, and the actual `.js`/`.css`/image files the page loaded) lands together in that folder's `assets/` subfolder — fully self-contained, nothing shared across pages:
   ```
   screenshots/clean/product-page/assets/
   ├── product-page.png
   ├── product-page.html
   ├── index-XyuNVFOR.js
   ├── index-Co7SA-g_.css
   └── sauce-backpack-1200x1500-CjRW-Djj.jpg  (etc.)
   ```
   The real JS/CSS/image files are grabbed via a network response listener and cached in memory as they load, then replayed into every page's own `assets/` folder — since the bundle only loads once per navigation, not once per screenshot, a naive "save what just loaded" approach would miss it for every capture after the first.

   Includes a `waitForLoadState('networkidle')` before the product page capture specifically, since the inventory list renders in the DOM before the product images finish loading — without that wait, screenshots were catching half-loaded images.

6. **Broken UI state (desktop, on purpose)** — after the main desktop run, injects some junk CSS via `page.addStyleTag()` that pushes the first "Add to cart" button 2200px wide off the right edge of the screen, then captures `broken-button-clip`. This never touches the real site — it's injected into that one page load only, so it's a clean, repeatable way to generate a "bad" screenshot + matching broken DOM for test data.

7. **Manual reference + real fix, for comparison** — `captureBrokenState()` re-runs with the bug turned off manually (`broken-button-reference`, a placeholder baseline), and separately with the actual verified CSS fix from the ML side (`broken-button-fixed`) — both saved into `after/`.

8. **Automatic visual diff** — right after the fix screenshot is captured, shells out to `visual_diff.py` to diff it against the original bug screenshot, highlighting exactly what changed. Saves `screenshots/diff/broken-button-diff.png`. Wrapped in a try/catch — if Python or Pillow isn't installed, it logs a warning and the rest of the run continues rather than crashing.

9. **Mobile pass (375x812, ~iPhone size)** — repeats the clean flow at a mobile viewport, capturing product, cart, and confirmation the same self-contained way.

10. **Auto-closes when done** — waits 2 seconds after the mobile pass finishes, then closes the browser automatically instead of leaving the window sitting open.

## Output structure — clean/broken/after/diff dataset

```
screenshots/
├── clean/
│   ├── login-page/assets/           (png, html, js, css, images)
│   ├── product-page/assets/
│   ├── product-detail/assets/
│   ├── cart-multi-item/assets/
│   ├── confirmation-page/assets/
│   ├── mobile-product/assets/
│   ├── mobile-cart/assets/
│   └── mobile-confirmation/assets/
├── broken/
│   └── broken-button-clip/assets/   (the bug)
├── after/
│   ├── broken-button-reference/assets/  (bug manually turned off - placeholder baseline)
│   └── broken-button-fixed/assets/      (the actual ML-verified fix)
└── diff/
    └── broken-button-diff.png       (highlighted pixel diff: bug vs fix)
```

## Structure

**`setupAssetCapture(page)`** — hooks a `page.on('response', ...)` listener that catches every network response whose URL contains `/assets/`, and caches the raw bytes in memory keyed by URL path. Called once on the page.

**`saveAssetsFor(pageDir)`** — writes everything currently in that in-memory cache into `<pageDir>/assets/`. Called from inside `captureSnapshot()` every single time a screenshot is taken, so every page ends up with a full local copy of the bundle regardless of when it actually loaded.

**`captureSnapshot(page, screenshotsDir, filename)`** — every screenshot in the file goes through this. Creates the per-page `assets/` folder, saves the `.png` and `.html` into it, then calls `saveAssetsFor()`.

**`generateVisualDiff(beforePath, afterPath, outputPath)`** — shells out to `visual_diff.py` (must sit in the same folder as `open-sauce.js`) via `child_process.execFileSync`. Failure (missing Python/Pillow) is caught and logged, not fatal.

**`runCheckoutFlow(page, screenshotsDir, viewport, filenames, options = {})`** — the whole login → detail page → cart → checkout → capture sequence. Both the desktop and mobile passes write into `clean/`. `options`:

| option | default | what it does |
|---|---|---|
| `itemCount` | `1` | how many products to add to the cart |
| `captureLogin` | `false` | capture the login page before logging in |
| `captureDetail` | `false` | click into the first product's detail page and capture it |
| `stopAtCart` | `false` | stop after the cart capture instead of going through checkout |

**`captureBrokenState(page, screenshotsDir, options = {})`** — separate function since this flow is genuinely different (no cart/checkout at all, just inject CSS and capture). `applyBrokenCss` toggles the built-in bug on/off; `customCss` injects any CSS string instead (used for the real ML fix); `filename` lets each call save under its own name.

**`rerunFlowForComparison(flowFn, ...args)`** — generic re-run helper, takes whatever capture function you used the first time plus a fresh set of args and calls it again.

## visual_diff.py

Standalone Python script (Pillow) that compares two screenshots and produces a highlighted diff:
```bash
python visual_diff.py <before.png> <after.png> <output-diff.png>
```
Computes per-pixel difference via `ImageChops.difference()`, thresholds it into a changed/unchanged mask, paints changed pixels semi-transparent red over the `after` image, and draws a bounding box around the overall changed region. Prints the bounding box, pixel count, and percentage changed. Resizes `after` to match `before` automatically if their dimensions don't line up.

**Must sit in the same folder as `open-sauce.js`** — `generateVisualDiff()` looks for it via `path.join(__dirname, 'visual_diff.py')`.

## Pacing / delays

A few small `waitForTimeout()` calls are sprinkled in purely so the browser run is easy to watch when running headed:
- Short delay before clicking the cart icon
- A ~1.5s pause on the order overview page before clicking Finish, so it doesn't flash by
- A 2s pause before the browser auto-closes at the end

