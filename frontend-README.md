# open-sauce.js

Playwright script that automates a full checkout run on [saucedemo.com](https://saucedemo.com), capturing screenshots (and matching HTML snapshots) at desktop and mobile viewport sizes, plus a deliberately broken UI state with a before/after comparison — organized into a clean/broken/after dataset for testing.

## What it does, step by step

1. **Login** — logs in as `standard_user` / `secret_sauce` on saucedemo.com, using `page.type()` with a small delay (instead of `fill()`) so the typing is actually visible when running headed.

2. **Product detail page** — clicks into the first product's own page (not just the list view) before adding anything to the cart.

3. **Add to cart** — adds multiple products to the cart (not just one), so the cart screenshot actually shows a multi-item cart. Logs the cart badge count to confirm it worked.

4. **Checkout flow** — clicks into the cart, hits Checkout, fills in the checkout info form with dummy data (first name, last name, zip), continues through to the order overview, and clicks Finish. Waits for the "Thank you for your order" confirmation page to confirm the run succeeded.

5. **Screenshot + HTML snapshot, together** — every capture point saves both a `.png` and a matching `.html` with the same base name, so there's both a visual and the raw DOM to work from.

6. **Broken UI state (desktop, on purpose)** — after the main desktop run, injects some junk CSS via `page.addStyleTag()` that pushes the first "Add to cart" button 2200px wide off the right edge of the screen, then captures `broken-button-clip.png`. This never touches the real site — it's injected into that one page load only, so it's a clean, repeatable way to generate a "bad" screenshot + matching broken DOM for test data. Kept to just the overflow (no color/border styling) so it reads as a genuine layout bug rather than an obviously staged one.

7. **After-fix comparison** — re-runs the exact same page through `captureBrokenState` again, this time with the broken CSS skipped (`applyBrokenCss: false`), saving it as `broken-button-fixed.png` into a separate `after/` folder — so the "before" (broken/) and "after" (after/) screenshots of the same bug can be diffed side by side once a real fix goes in.

8. **Mobile pass (375x812, ~iPhone size)** — repeats the clean flow at a mobile viewport, capturing product, cart, and confirmation.

9. **Auto-closes when done** — waits 2 seconds after the mobile pass finishes, then closes the browser automatically instead of leaving the window sitting open.

## Output structure — clean/broken/after dataset

Every run creates `screenshots/`, `screenshots/clean/`, `screenshots/broken/`, and `screenshots/after/` automatically if they don't already exist:

```
screenshots/
├── clean/
│   ├── login-page.png / .html
│   ├── product-page.png / .html
│   ├── product-detail.png / .html
│   ├── cart-multi-item.png / .html
│   ├── confirmation-page.png / .html
│   ├── mobile-product.png / .html
│   ├── mobile-cart.png / .html
│   └── mobile-confirmation.png / .html
├── broken/
│   └── broken-button-clip.png / .html      (the bug)
└── after/
    └── broken-button-fixed.png / .html     (same page, bug removed)
```

Since every capture goes through the shared `captureSnapshot()` helper, every `.png` in every folder is guaranteed to have its matching `.html` right next to it.

## Structure

**`captureSnapshot(page, screenshotsDir, filename)`** — every screenshot in the file goes through this instead of calling `page.screenshot()` directly. It takes the screenshot, then calls `page.content()` to grab the live rendered DOM and writes it out to a matching `.html` file.

**`runCheckoutFlow(page, screenshotsDir, viewport, filenames, options = {})`** — the whole login → detail page → cart → checkout → capture sequence, in one reusable function. Both the desktop and mobile passes write into `clean/`. `options`:

| option | default | what it does |
|---|---|---|
| `itemCount` | `1` | how many products to add to the cart |
| `captureLogin` | `false` | capture the login page before logging in |
| `captureDetail` | `false` | click into the first product's detail page and capture it |
| `stopAtCart` | `false` | stop after the cart capture instead of going through checkout |

**`captureBrokenState(page, screenshotsDir, applyBrokenCss = true, filename = 'broken-button-clip.png')`** — separate function since this flow is genuinely different (no cart/checkout at all, just inject CSS and capture). Runs at the desktop viewport. `applyBrokenCss` toggles whether the broken CSS gets injected at all — `true` (default) for the actual bug, `false` to capture the same page with no bug, for the after-fix comparison. `filename` lets each call save under its own name so the two don't overwrite each other.

**`rerunFlowForComparison(flowFn, ...args)`** — generic re-run helper. Takes whatever capture function you used the first time (`runCheckoutFlow` or `captureBrokenState`) plus a fresh set of args, and just calls it again. Used here to grab the "after" screenshot once a fix is simulated, but works for re-running any flow, not just this one.

## Pacing / delays

A few small `waitForTimeout()` calls are sprinkled in purely so the browser run is easy to watch when running headed:
- Short delay before clicking the cart icon
- A ~1.5s pause on the order overview page before clicking Finish, so it doesn't flash by
- A 2s pause before the browser auto-closes at the end






- Still working on fetching the related CSS, JS and other assets of the captured screenshots to help the VLM give proper and correct output/fix..