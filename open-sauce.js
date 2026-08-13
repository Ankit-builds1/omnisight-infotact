const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

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

  // standard desktop size so screenshots look consistent, not whatever random size the window opens at
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 }
  });

  await page.goto('https://saucedemo.com');

  const title = await page.title();
  console.log(`Page title is: ${title}`);

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

  await page.screenshot({ path: path.join(screenshotsDir, 'product-page.png') });

  // just grab the first product and add it to the cart
  await page.click('.inventory_item .btn_inventory');

  // cart icon should now show "1"
  const cartCount = await page.textContent('.shopping_cart_badge');
  console.log(`cart badge shows: ${cartCount}`);

  // head into the cart to start checkout
  await page.waitForTimeout(500);
  await page.click('.shopping_cart_link');
  await page.waitForSelector('.cart_list');
  console.log('on cart page');

  await page.screenshot({ path: path.join(screenshotsDir, 'cart-page.png') });

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

  await page.screenshot({ path: path.join(screenshotsDir, 'confirmation-page.png') });

  // now do it all again but at mobile size, to grab the same key screenshots on a phone-sized viewport
  console.log('switching to mobile viewport, redoing the flow for mobile screenshots');
  await page.setViewportSize({ width: 375, height: 812 }); // roughly an iphone x/11 size

  await page.goto('https://saucedemo.com');

  await page.type('#user-name', 'standard_user', { delay: 60 });
  await page.type('#password', 'secret_sauce', { delay: 60 });
  await page.click('#login-button');

  await page.waitForSelector('.inventory_list');
  await page.waitForLoadState('networkidle');
  console.log('mobile: products page loaded');
  await page.screenshot({ path: path.join(screenshotsDir, 'mobile-product.png') });

  await page.click('.inventory_item .btn_inventory');

  await page.waitForTimeout(500);
  await page.click('.shopping_cart_link');
  await page.waitForSelector('.cart_list');
  console.log('mobile: on cart page');
  await page.screenshot({ path: path.join(screenshotsDir, 'mobile-cart.png') });

  await page.click('#checkout');

  await page.waitForSelector('#first-name');
  await page.type('#first-name', 'Peter', { delay: 60 });
  await page.type('#last-name', 'Parker', { delay: 60 });
  await page.type('#postal-code', '12345', { delay: 60 });
  await page.click('#continue');

  await page.waitForSelector('#finish');
  await page.waitForTimeout(1500);
  await page.click('#finish');

  await page.waitForSelector('.complete-header');
  console.log('mobile: on confirmation page');
  await page.screenshot({ path: path.join(screenshotsDir, 'mobile-confirmation.png') });

  //if want to close browser automatically , just un-comment the two lines below___________note: sid
  //await page.waitForTimeout(3000);
  //await browser.close();
})();
