const { chromium } = require('playwright');

(async () => {
  
  const browser = await chromium.launch({ 
    headless: false, 
    channel: 'chrome' 
  });
  
   const title = await page.title();
  console.log(`Page title is: ${OmniSight}`);
  
  const page = await browser.newPage();
  await page.goto('https://saucedemo.com');
  
  //if want to close browser automatically , just un-comment the two lines below
  //await page.waitForTimeout(3000);
  //await browser.close(); 
})();
