# open-sauce.js

Playwright script that automates a full checkout run on [saucedemo.com](https://saucedemo.com), capturing screenshots along the way at both desktop and mobile viewport sizes.

## What it does, step by step

1. **Login** — logs in as `standard_user` / `secret_sauce` on saucedemo.com, using `page.type()` with a small delay (instead of `fill()`) so the typing is actually visible when running headed.

2. **Add to cart** — grabs the first product on the inventory page and adds it to the cart. Logs the cart badge count to confirm it worked.

3. **Checkout flow** — clicks into the cart, hits Checkout, fills in the checkout info form with dummy data (first name, last name, zip), continues through to the order overview, and clicks Finish. Waits for the "Thank you for your order" confirmation page to confirm the run succeeded.

4. **Desktop screenshots (1920x1080)** — captures three screenshots into a `screenshots/` folder (created automatically if it doesn't exist):
   - `product-page.png`
   - `cart-page.png`
   - `confirmation-page.png`

   Includes a `waitForLoadState('networkidle')` before the product page screenshot specifically, since the inventory list renders in the DOM before the product images finish loading — without that wait, screenshots were catching half-loaded images.

5. **Mobile screenshots (375x812, ~iPhone size)** — repeats the exact same flow (login → cart → checkout → confirmation) at a mobile viewport, saving:
   - `mobile-product.png`
   - `mobile-cart.png`
   - `mobile-confirmation.png`

## Structure

The login → cart → checkout → screenshot sequence is pulled out into a single reusable function:

```js
async function runCheckoutFlow(page, screenshotsDir, viewport, filenames) { ... }
```

The desktop and mobile passes are just two calls to this function with different viewport sizes and filenames — this replaced an earlier version where the whole flow was copy-pasted twice, to keep things maintainable as more screenshot variations get added (e.g. Week 2's broken UI states).

## Pacing / delays

A few small `waitForTimeout()` calls are sprinkled in purely so the browser run is easy to watch when running headed:
- Short delay before clicking the cart icon
- A ~1.5s pause on the order overview page before clicking Finish, so it doesn't flash by
- Browser close is commented out by default (`browser.close()`), so the window stays open after the run for inspection — uncomment those two lines if you want it to close automatically.
