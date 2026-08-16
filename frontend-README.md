# open-sauce.js

Playwright script that automates a full checkout run on [saucedemo.com](https://saucedemo.com), capturing screenshots along the way at both desktop and mobile viewport sizes.

## What it does, step by step

1. **Login** — logs in as `standard_user` / `secret_sauce` on saucedemo.com, using `page.type()` with a small delay (instead of `fill()`) so the typing is actually visible when running headed.

2. **Product detail page** — clicks into the first product's own page (not just the list view) before adding anything to the cart.

3. **Add to cart** — adds multiple products to the cart (not just one), so the cart screenshot actually shows a multi-item cart. Logs the cart badge count to confirm it worked.

4. **Checkout flow** — clicks into the cart, hits Checkout, fills in the checkout info form with dummy data (first name, last name, zip), continues through to the order overview, and clicks Finish. Waits for the "Thank you for your order" confirmation page to confirm the run succeeded.

5. **Screenshots, all in one pass** — captures everything into a `screenshots/` folder (created automatically if it doesn't exist), in a single continuous run — one login, one flow, no repeated navigation:
   - `login-page.png` — grabbed before logging in
   - `product-page.png` — the product list
   - `product-detail.png` — a single product's detail page
   - `cart-multi-item.png` — the cart with multiple items added
   - `confirmation-page.png` — the order confirmation page

   Includes a `waitForLoadState('networkidle')` before the product page screenshot specifically, since the inventory list renders in the DOM before the product images finish loading — without that wait, screenshots were catching half-loaded images.

6. **Mobile pass (375x812, ~iPhone size)** — repeats the same flow at a mobile viewport, saving:
   - `mobile-product.png`
   - `mobile-cart.png`
   - `mobile-confirmation.png`

   This runs as its own separate pass since it's a different viewport size and needs its own fresh navigation.

## Structure

The whole login → detail page → cart → checkout → screenshot sequence lives in one reusable function:

```js
async function runCheckoutFlow(page, screenshotsDir, viewport, filenames, options = {}) { ... }
```

`options` is what makes it flexible instead of needing a separate copy-pasted function for every screenshot variation:

| option | default | what it does |
|---|---|---|
| `itemCount` | `1` | how many products to add to the cart |
| `captureLogin` | `false` | screenshot the login page before logging in |
| `captureDetail` | `false` | click into the first product's detail page and screenshot it |
| `stopAtCart` | `false` | stop after the cart screenshot instead of going through checkout |

The desktop pass uses `itemCount: 3, captureLogin: true, captureDetail: true` to grab everything in one go. The mobile pass calls the same function with no options, so it just gets the plain default flow (1 item, straight through to confirmation) at a smaller viewport.

This used to be split into separate desktop / extras runs, each logging in and navigating from scratch — merged into one pass since there was no real reason to log in twice.

## Pacing / delays

A few small `waitForTimeout()` calls are sprinkled in purely so the browser run is easy to watch when running headed:
- Short delay before clicking the cart icon
- A ~1.5s pause on the order overview page before clicking Finish, so it doesn't flash by
- Browser close is commented out by default (`browser.close()`), so the window stays open after the run for inspection — uncomment those two lines if you want it to close automatically.



