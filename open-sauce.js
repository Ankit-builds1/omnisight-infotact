const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

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
    await page.screenshot({ path: path.join(screenshotsDir, filenames.login) });
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
    await page.screenshot({ path: path.join(screenshotsDir, filenames.product) });
  }

  // click into the first product's own page if we need the detail view, then head back to the list
  // (.inventory_item_name matches every product on the list, so grab all of them and click just the first)_______note: sid
  if (captureDetail) {
    const productLinks = await page.$$('.inventory_item_name');
    await productLinks[0].click();
    await page.waitForSelector('.inventory_details_name');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(screenshotsDir, filenames.detail) });

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

  await page.screenshot({ path: path.join(screenshotsDir, filenames.cart) });

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

  await page.screenshot({ path: path.join(screenshotsDir, filenames.confirmation) });
}

(async () => {

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome'
  });

  // make sure screenshots always land somewhere consistent, create the folder if its not there yet____________note: sid
  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir);
  }

  const page = await browser.newPage();

  // desktop pass - the "main" run, now grabbing everything in one go: login page, product list,
  // product detail, a multi-item cart, and all the way through to confirmation.______note: sid
  await runCheckoutFlow(page, screenshotsDir, { width: 1920, height: 1080 }, {
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

  // mobile pass, roughly an iphone x/11 size, same flow just repeated at a smaller viewport
  console.log('switching to mobile viewport, redoing the flow for mobile screenshots');
  await runCheckoutFlow(page, screenshotsDir, { width: 375, height: 812 }, {
    product: 'mobile-product.png',
    cart: 'mobile-cart.png',
    confirmation: 'mobile-confirmation.png'
  });

  //if want to close browser automatically , just un-comment the two lines below___________note: sid
  //await page.waitForTimeout(3000);
  //await browser.close();
})();
