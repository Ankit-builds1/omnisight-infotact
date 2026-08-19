# open-sauce.js

Playwright script that automates a full checkout run on [saucedemo.com](https://saucedemo.com), capturing screenshots (and matching HTML snapshots) at desktop and mobile viewport sizes, plus one deliberately broken UI state — organized into a clean/broken dataset for testing.

## What it does, step by step

1. **Login** — logs in as `standard_user` / `secret_sauce` on saucedemo.com, using `page.type()` with a small delay (instead of `fill()`) so the typing is actually visible when running headed.

2. **Product detail page** — clicks into the first product's own page (not just the list view) before adding anything to the cart.

3. **Add to cart** — adds multiple products to the cart (not just one), so the cart screenshot actually shows a multi-item cart. Logs the cart badge count to confirm it worked.

4. **Checkout flow** — clicks into the cart, hits Checkout, fills in the checkout info form with dummy data (first name, last name, zip), continues through to the order overview, and clicks Finish. Waits for the "Thank you for your order" confirmation page to confirm the run succeeded.

5. **Screenshot + HTML snapshot, together** — every capture point saves both a `.png` and a matching `.html` with the same base name, so there's both a visual and the raw DOM to work from.

6. **Broken UI state (desktop, on purpose)** — after the main desktop run, injects some junk CSS via `page.addStyleTag()` that pushes the first "Add to cart" button 2200px wide off the right edge of the screen, then captures it. This never touches the real site — it's injected into that one page load only, so it's a clean, repeatable way to generate a "bad" screenshot + matching broken DOM for test data.

7. **Mobile pass (375x812, ~iPhone size)** — repeats the clean flow at a mobile viewport, capturing product, cart, and confirmation.

8. **Auto-closes when done** — waits 2 seconds after the mobile pass finishes, then closes the browser automatically instead of leaving the window sitting open.

## Output structure — clean/broken dataset

Every run creates `screenshots/`, `screenshots/clean/`, and `screenshots/broken/` automatically if they don't already exist. All bug-free captures go into `clean/`, the one deliberately broken capture goes into `broken/`, so ML tooling can point at either folder and know exactly what it's getting without cross-referencing filenames:

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
└── broken/
    └── broken-button-clip.png / .html
```

Since every capture goes through the shared `captureSnapshot()` helper (see below), every `.png` in both folders is guaranteed to have its matching `.html` right next to it — the folder split doubles as the organization, no separate checklist needed.

## Structure

**`captureSnapshot(page, screenshotsDir, filename)`** — every screenshot in the file goes through this instead of calling `page.screenshot()` directly. It takes the screenshot, then calls `page.content()` to grab the live rendered DOM and writes it out to a matching `.html` file. Since `page.content()` runs after any CSS injection, the broken screenshot's HTML file includes the injected broken styles too — not just the clean original markup. The `screenshotsDir` param is just whatever target folder it's handed (`clean/` or `broken/`) — the function itself doesn't care which.

**`runCheckoutFlow(page, screenshotsDir, viewport, filenames, options = {})`** — the whole login → detail page → cart → checkout → capture sequence, in one reusable function. Both the desktop and mobile passes write into `clean/`. `options` is what makes it flexible instead of needing a separate copy-pasted function per screenshot variation:

| option | default | what it does |
|---|---|---|
| `itemCount` | `1` | how many products to add to the cart |
| `captureLogin` | `false` | capture the login page before logging in |
| `captureDetail` | `false` | click into the first product's detail page and capture it |
| `stopAtCart` | `false` | stop after the cart capture instead of going through checkout |

The desktop pass uses `itemCount: 3, captureLogin: true, captureDetail: true` to grab everything in one go. The mobile pass calls the same function with no options, so it just gets the plain default flow (1 item, straight through to confirmation) at a smaller viewport.

**`captureBrokenState(page, screenshotsDir)`** — separate function since this flow is genuinely different (no cart/checkout at all, just inject CSS and capture). Writes into `broken/`. Runs at the desktop viewport, grouped right after the desktop pass so the script isn't bouncing between viewport sizes.

## Pacing / delays

A few small `waitForTimeout()` calls are sprinkled in purely so the browser run is easy to watch when running headed:
- Short delay before clicking the cart icon
- A ~1.5s pause on the order overview page before clicking Finish, so it doesn't flash by
- A 2s pause before the browser auto-closes at the end

Verified all the screenshots in screenshots/clean/ and screenshots/broken/
- All clean screenshots correctly show bug-free UI states
- broken-button-clip.png clearly shows the injected bug (button clipping outside viewport)
- Every .png has a matching .html file
Dataset is ready for ML's Vision Audit.