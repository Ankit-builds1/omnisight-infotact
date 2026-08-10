const { chromium } = require('playwright');

(async () => {

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome'
  });

  const page = await browser.newPage();

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

  // just grab the first product and add it to the cart
  await page.click('.inventory_item .btn_inventory');

  // cart icon should now show "1"
  const cartCount = await page.textContent('.shopping_cart_badge');
  console.log(`cart badge shows: ${cartCount}`);

  //if want to close browser automatically , just un-comment the two lines below___________note: sid
  //await page.waitForTimeout(3000);
  //await browser.close();
})();
