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

  // head into the cart to start checkout
  await page.waitForTimeout(500);
  await page.click('.shopping_cart_link');
  await page.waitForSelector('.cart_list');
  console.log('on cart page');

  await page.click('#checkout');

  // fill checkout info step one, dummy data is fine for saucedemo
  await page.waitForSelector('#first-name');
  await page.type('#first-name', 'John', { delay: 60 });
  await page.type('#last-name', 'Doe', { delay: 60 });
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

  //if want to close browser automatically , just un-comment the two lines below___________note: sid
  //await page.waitForTimeout(3000);
  //await browser.close();
})();
