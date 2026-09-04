const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

// shells out to visual_diff.py (sits alongside this script) to compare a before/after pair and
// save a highlighted diff image. keeping the actual pixel-diffing logic in python/pillow instead
// of reimplementing it here - this just wires it into the run so it happens automatically______note: sid
function generateVisualDiff(beforePath, afterPath, outputPath) {
  try {
    execFileSync('python3', [path.join(__dirname, 'visual_diff.py'), beforePath, afterPath, outputPath], {
      stdio: 'inherit'
    });
  } catch (err) {
    console.log('visual diff failed to run - is python3/Pillow installed? skipping, not a fatal error');
  }
}

// keeps every asset (js/css/image/font under /assets/) we've seen so far in memory, keyed by
// url pathname. most of these - especially the js/css bundle - only actually load ONCE per page
// navigation, not once per screenshot, so relying on fresh network events at the exact moment
// of each individual screenshot would miss them for every capture after the first. caching them
// as they come in and replaying the cache into each page's own folder fixes that______note: sid
const assetCache = new Map();

function setupAssetCapture(page) {
  page.on('response', (response) => {
    const url = response.url();
    if (!url.includes('/assets/')) return;

    (async () => {
      try {
        const urlPath = new URL(url).pathname; // e.g. /assets/index-XyuNVFOR.js
        if (assetCache.has(urlPath)) return; // already cached this one
        const buffer = await response.body();
        assetCache.set(urlPath, buffer);
      } catch (err) {
        // redirects / already-consumed bodies / weird urls sometimes throw here, just skip them
      }
    })();
  });
}

// writes out everything currently sitting in the asset cache into this specific page's own
// assets/ folder - called every time we grab a screenshot, so each page folder ends up fully
// self-contained (png + html + assets all together) instead of one shared assets/ folder for
// the whole run______note: sid
async function saveAssetsFor(pageDir) {
  if (assetCache.size === 0) return;

  const assetsDir = path.join(pageDir, 'assets');
  await fs.promises.mkdir(assetsDir, { recursive: true });

  for (const [urlPath, buffer] of assetCache) {
    const filename = path.basename(urlPath);
    await fs.promises.writeFile(path.join(assetsDir, filename), buffer);
  }
}

// takes the screenshot like normal, but into its own folder named after the page (e.g. product-page/
// product-page.png + product-page.html), and also copies whatever's in the asset cache into that
// same folder's assets/ subfolder - so every single capture ends up fully self-contained, not
// sharing one assets/ folder across the whole run. the VLM needs the image, the raw dom, AND the
// actual js/css/images to have anything to load if it opens the html standalone______note: sid
// takes the screenshot like normal, but everything - the png, the html, AND the js/css/image
// assets - all go straight into this page's own assets/ folder together, not split across two
// levels. e.g. product-page/assets/product-page.png, product-page.html, index-XyuNVFOR.js, all
// sitting in the same folder______note: sid
async function captureSnapshot(page, screenshotsDir, filename) {
  const pageName = filename.replace('.png', '');
  const pageDir = path.join(screenshotsDir, pageName);
  const assetsDir = path.join(pageDir, 'assets');
  fs.mkdirSync(assetsDir, { recursive: true });

  await page.screenshot({ path: path.join(assetsDir, filename) });

  const html = await page.content();
  const htmlFilename = filename.replace('.png', '.html');
  fs.writeFileSync(path.join(assetsDir, htmlFilename), html);

  await saveAssetsFor(pageDir);
}

// runs the login -> add to cart -> checkout flow at whatever viewport size you give it,
// taking screenshots along the way. the extra "options" param lets us bend the same flow
// for different screenshot needs (login page, product detail, multiple items in cart, etc)
// instead of writing a whole separate function every time______note: sid
async function runCheckoutFlow(page, screenshotsDir, viewport, filenames, options = {}) {
  const {
    itemCount = 1,        // how many products to add to the cart
    captureLogin = false, // grab a screenshot of the login page before logging in
    captureDetail = false, // click into the first product's detail page and grab that too
    stopAtCart = false    // stop after the cart screenshot instead of going through checkout
  } = options;

  await page.setViewportSize(viewport);
  await page.goto('https://saucedemo.com');

  const title = await page.title();
  console.log(`Page title is: ${title}`);

  // we normally blow straight past the login page, so only grab it when asked to
  if (captureLogin) {
    await page.waitForSelector('#login-button');
    await captureSnapshot(page, screenshotsDir, filenames.login);
  }

  // login with the standard demo account
  // using type() with a small delay instead of fill() so you can actually see it happen , eg. 100 for slower and 30 for faster______note: sid
  await page.type('#user-name', 'standard_user', { delay: 60 });
  await page.type('#password', 'secret_sauce', { delay: 60 });
  await page.click('#login-button');

  // make sure we actually landed on the products page before doing anything else
  await page.waitForSelector('.inventory_list');
  console.log('logged in, products page loaded');

  // .inventory_list shows up before the product images actually finish loading, so wait for the network to settle first or the screenshot catches them half loaded____note: sid
  await page.waitForLoadState('networkidle');

  if (filenames.product) {
    await captureSnapshot(page, screenshotsDir, filenames.product);
  }

  // click into the first product's own page if we need the detail view, then head back to the list
  // (.inventory_item_name matches every product on the list, so grab all of them and click just the first)_______note: sid
  if (captureDetail) {
    const productLinks = await page.$$('.inventory_item_name');
    await productLinks[0].click();
    await page.waitForSelector('.inventory_details_name');
    await page.waitForLoadState('networkidle');
    await captureSnapshot(page, screenshotsDir, filenames.detail);

    await page.click('#back-to-products');
    await page.waitForSelector('.inventory_list');
  }

  // grab however many products we were told to add, first N on the list
  const addToCartButtons = await page.$$('.inventory_item .btn_inventory');
  for (let i = 0; i < itemCount; i++) {
    await addToCartButtons[i].click();
  }

  // cart icon should now show the item count
  const cartCount = await page.textContent('.shopping_cart_badge');
  console.log(`cart badge shows: ${cartCount}`);

  // head into the cart
  await page.waitForTimeout(500);
  await page.click('.shopping_cart_link');
  await page.waitForSelector('.cart_list');
  console.log('on cart page');

  await captureSnapshot(page, screenshotsDir, filenames.cart);

  // some runs just want the cart screenshot and nothing past it
  if (stopAtCart) {
    return;
  }

  await page.click('#checkout');

  // fill checkout info step one, (dummy data)
  await page.waitForSelector('#first-name');
  await page.type('#first-name', 'Peter', { delay: 60 });
  await page.type('#last-name', 'Parker', { delay: 60 });
  await page.type('#postal-code', '12345', { delay: 60 });
  await page.click('#continue');

  // step two is just the order overview, pause here so it's actually visible before finishing, eg. 2000 for slower and 500 for faster______note: sid
  await page.waitForSelector('#finish');
  await page.waitForTimeout(1500);
  await page.click('#finish');

  // should now be on the "thank you" confirmation page
  await page.waitForSelector('.complete-header');
  const confirmationMsg = await page.textContent('.complete-header');
  console.log(`confirmation message: ${confirmationMsg}`);

  await captureSnapshot(page, screenshotsDir, filenames.confirmation);
}

// deliberately breaks the UI on purpose so we've got a bad screenshot to test against too -
// pushes the first "add to cart" button way outside the desktop viewport with some junk css,
// injected straight into the page instead of touching the actual site.
//
// three ways to call this:
//   - default (applyBrokenCss: true)  -> injects our own broken css, this is the "before" bug shot
//   - applyBrokenCss: false           -> injects nothing, just the plain default page - this is
//                                        the reference shot, for turning the bug off manually
//   - customCss: '...'                -> injects whatever css string you give it instead, so this
//                                        isn't locked to just our one bug - anyone's fix/variation
//                                        can get run through the same flow and screenshotted_____note: sid
async function captureBrokenState(page, screenshotsDir, options = {}) {
  const {
    applyBrokenCss = true,
    customCss = null,     // pass a css string here to inject that instead of the built-in bug
    filename = 'broken-button-clip.png'
  } = options;

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('https://saucedemo.com');

  await page.type('#user-name', 'standard_user', { delay: 60 });
  await page.type('#password', 'secret_sauce', { delay: 60 });
  await page.click('#login-button');

  await page.waitForSelector('.inventory_list');
  await page.waitForLoadState('networkidle');

  if (customCss) {
    // some other css was handed to us, inject that instead of our own built-in bug
    await page.addStyleTag({ content: customCss });
    console.log('custom css injected, grabbing screenshot');
  } else if (applyBrokenCss) {
    // shove the button way past the right edge of the screen so it clips off entirely
    await page.addStyleTag({
      content: `
        .inventory_item:first-child .btn_inventory {
          width: 2200px !important;
          margin-left: 300px !important;
          white-space: nowrap !important;
        }
      `
    });
    console.log('broken state injected, grabbing screenshot');
  } else {
    // bug turned off, nothing injected - this is the plain reference shot
    console.log('css bug turned off, grabbing the reference screenshot');
  }

  await captureSnapshot(page, screenshotsDir, filename);
}

// generic re-run helper - takes whatever capture function you used the first time (runCheckoutFlow
// or captureBrokenState) plus the same args, and just calls it again. mainly for before/after
// comparisons: run the broken flow once, apply a fix, then re-run the same flow again pointed
// at a different folder to grab the "after" screenshot for the same page______note: sid
async function rerunFlowForComparison(flowFn, ...args) {
  console.log('re-running the flow for a before/after comparison');
  await flowFn(...args);
}

(async () => {

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome'
  });

  // make sure screenshots always land somewhere consistent, create the folders if they're not there yet.
  // split into clean/ and broken/ so ML can just point at one folder or the other and know what its getting____note: sid
  const screenshotsDir = path.join(__dirname, 'screenshots');
  const cleanDir = path.join(screenshotsDir, 'clean');
  const brokenDir = path.join(screenshotsDir, 'broken');
  const afterDir = path.join(screenshotsDir, 'after'); // for the fixed re-run, to diff against broken/
  const diffDir = path.join(screenshotsDir, 'diff');   // highlighted before/after diff images land here

  [screenshotsDir, cleanDir, brokenDir, afterDir, diffDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir);
    }
  });

  const page = await browser.newPage();
  setupAssetCapture(page);

  // desktop pass - the "main" run, now grabbing everything in one go: login page, product list,
  // product detail, a multi-item cart, and all the way through to confirmation.______note: sid
  await runCheckoutFlow(page, cleanDir, { width: 1920, height: 1080 }, {
    login: 'login-page.png',
    product: 'product-page.png',
    detail: 'product-detail.png',
    cart: 'cart-multi-item.png',
    confirmation: 'confirmation-page.png'
  }, {
    itemCount: 3,
    captureLogin: true,
    captureDetail: true
  });

  // one deliberately broken screenshot too, for testing against a known bad UI state - desktop viewport, grouped with the rest of the desktop stuff above____note: sid
  console.log('grabbing a broken UI screenshot on purpose');
  await captureBrokenState(page, brokenDir);

  // turn the bug off manually and grab the reference screenshot - this is what priya will
  // compare her actual fix against later, not a real fix itself______note: sid
  await rerunFlowForComparison(captureBrokenState, page, afterDir, {
    applyBrokenCss: false,
    filename: 'broken-button-reference.png'
  });

  // the actual verified fix from the ML side, run through the same flow to get a real "after"
  // screenshot - not the manual placeholder above______note: sid
  await captureBrokenState(page, afterDir, {
    customCss: `
      #page_wrapper .inventory_item:first-child .btn_inventory {
        width: auto;
        max-width: none;
        overflow: visible;
      }
    `,
    filename: 'broken-button-fixed.png'
  });

  // now diff the actual bug against the actual fix and highlight what changed - both images
  // ended up in their own nested folders from captureSnapshot, so build the exact paths here____note: sid
  console.log('generating visual diff between the bug and the fix');
  generateVisualDiff(
    path.join(brokenDir, 'broken-button-clip', 'assets', 'broken-button-clip.png'),
    path.join(afterDir, 'broken-button-fixed', 'assets', 'broken-button-fixed.png'),
    path.join(diffDir, 'broken-button-diff.png')
  );

  // mobile pass, roughly an iphone x/11 size, same flow just repeated at a smaller viewport
  console.log('switching to mobile viewport, redoing the flow for mobile screenshots');
  await runCheckoutFlow(page, cleanDir, { width: 375, height: 812 }, {
    product: 'mobile-product.png',
    cart: 'mobile-cart.png',
    confirmation: 'mobile-confirmation.png'
  });

  // close it out automatically once everything's captured, no reason to leave the browser sitting there____note: sid
  await page.waitForTimeout(2000);
  await browser.close();
})();



