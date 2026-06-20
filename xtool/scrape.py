"""Playwright scraper for X timelines.

Drives a real Chromium with a persistent profile (so you log into X once). The
per-tweet extraction selectors are ported from the proven extension popup.js.
"""
import random
from playwright.sync_api import sync_playwright
import config

# Extraction runs in the page; mirrors popup.js (handle, images, engagement).
JS_EXTRACT = r"""
() => {
  const MEDIA_RE = /^https?:\/\/pbs\.twimg\.com\/media\/[A-Za-z0-9_-]+/i;
  const parseCount = (s) => {
    if (!s) return 0;
    const m = String(s).replace(/[,\s]/g, "").match(/([\d.]+)([KMB])?/i);
    if (!m) return 0;
    let n = parseFloat(m[1]); if (isNaN(n)) return 0;
    const u = (m[2] || "").toUpperCase();
    if (u === "K") n *= 1e3; else if (u === "M") n *= 1e6; else if (u === "B") n *= 1e9;
    return Math.round(n);
  };
  const metric = (t, ids) => {
    for (const id of ids) { const b = t.querySelector(`[data-testid="${id}"]`);
      if (b) { return parseCount(b.innerText) || parseCount(b.getAttribute("aria-label")); } }
    return 0;
  };
  const fromGroup = (t, words) => {
    const l = t.querySelector('div[role="group"]')?.getAttribute("aria-label"); if (!l) return 0;
    for (const w of words) { const m = l.match(new RegExp(`([\\d,.]+)\\s+${w}`, "i")); if (m) return parseCount(m[1]); }
    return 0;
  };
  const out = [];
  document.querySelectorAll("article").forEach(t => {
    const text = t.querySelector("div[lang]")?.innerText;
    const username = t.querySelector("div span span")?.innerText;
    const date = t.querySelector("time")?.getAttribute("datetime");
    if (!(text && username && date)) return;
    const link = t.querySelector('a[href*="/status/"]')?.getAttribute("href") || "";
    const parts = link.split("/");
    const handle = parts[1] && parts[1] !== "i" ? "@" + parts[1] : "";
    const id = parts.includes("status") ? parts[parts.indexOf("status") + 1] : (username + "|" + date);
    const images = [];
    t.querySelectorAll('[data-testid="tweetPhoto"] img, img[src*="pbs.twimg.com/media/"]').forEach(im => {
      const s = im.getAttribute("src") || ""; if (MEDIA_RE.test(s) && !images.includes(s)) images.push(s);
    });
    out.push({
      id, username, handle, date, text,
      comments: fromGroup(t, ["repl", "comment"]) || metric(t, ["reply"]),
      retweets: fromGroup(t, ["repost", "retweet"]) || metric(t, ["retweet", "unretweet"]),
      likes: fromGroup(t, ["like"]) || metric(t, ["like", "unlike"]),
      views: fromGroup(t, ["view"]),
      images,
    });
  });
  return out;
}
"""


def scrape(target_url, scrolls=config.SCROLLS):
    tweets, seen = [], set()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(config.PROFILE_DIR),
            headless=config.HEADLESS,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for i in range(scrolls):
            for t in page.evaluate(JS_EXTRACT):
                if t["id"] in seen:
                    continue
                seen.add(t["id"])
                tweets.append(t)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            lo, hi = config.SCROLL_DELAY
            page.wait_for_timeout(int(random.uniform(lo, hi) * 1000))
        ctx.close()
    return tweets


if __name__ == "__main__":
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else "https://x.com/home"
    data = scrape(url, int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    print(json.dumps(data, ensure_ascii=False, indent=2))
