// Tweet Scraper — background service worker.
// The extension only scrapes/exports now; image classification (solo female
// portraits) lives in the standalone Python tool (see xtool/).
chrome.runtime.onInstalled.addListener(() => {
    console.log("Tweet Scraper Installed!");
});
