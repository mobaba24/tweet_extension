document.getElementById("startScraping").addEventListener("click", () => {
    const scrollLimit = document.getElementById("scrollLimit").value;
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: scrapeTweets,
            args: [parseInt(scrollLimit)]
        });
    });
});

function scrapeTweets(scrollLimit) {
    const results = [];
    const seen = new Set();
    let scrolled = 0;

    // Turn an abbreviated/comma-formatted count string ("1,234", "1.2K", "3M")
    // into an integer. Returns 0 when no number is present (e.g. empty button).
    const parseCount = (str) => {
        if (!str) return 0;
        const match = String(str).replace(/[,\s]/g, "").match(/([\d.]+)([KMB])?/i);
        if (!match) return 0;
        let num = parseFloat(match[1]);
        if (isNaN(num)) return 0;
        const suffix = (match[2] || "").toUpperCase();
        if (suffix === "K") num *= 1e3;
        else if (suffix === "M") num *= 1e6;
        else if (suffix === "B") num *= 1e9;
        return Math.round(num);
    };

    // Read a single engagement metric for a tweet. data-testid values
    // (reply / retweet / like / unlike) are stable across UI languages, so we
    // select by those and then read the visible count text or its aria-label.
    const getMetric = (tweet, testids) => {
        for (const id of testids) {
            const btn = tweet.querySelector(`[data-testid="${id}"]`);
            if (!btn) continue;
            const fromText = parseCount(btn.innerText);
            if (fromText) return fromText;
            return parseCount(btn.getAttribute("aria-label"));
        }
        return 0;
    };

    // The engagement bar exposes a role="group" element whose aria-label holds
    // the exact (non-abbreviated) counts, e.g.
    // "12 replies, 5 reposts, 345 likes, 6 bookmarks, 78910 views".
    // We use it as the source of truth when available (English UI), falling
    // back to the per-button counts otherwise.
    const fromGroupLabel = (tweet, words) => {
        const label = tweet.querySelector('div[role="group"]')?.getAttribute("aria-label");
        if (!label) return 0;
        for (const word of words) {
            const m = label.match(new RegExp(`([\\d,.]+)\\s+${word}`, "i"));
            if (m) return parseCount(m[1]);
        }
        return 0;
    };

    const scrape = () => {
        document.querySelectorAll("article").forEach(tweet => {
            const text = tweet.querySelector("div[lang]")?.innerText;
            const username = tweet.querySelector("div span span")?.innerText;
            const date = tweet.querySelector("time")?.getAttribute("datetime");
            const imageUrl = tweet.querySelector("img[alt='Image']")?.getAttribute("src") || "none";

            // Engagement metrics: prefer the exact group aria-label counts,
            // fall back to the individual button counts.
            const comments = fromGroupLabel(tweet, ["repl", "comment"]) || getMetric(tweet, ["reply"]);
            const retweets = fromGroupLabel(tweet, ["repost", "retweet"]) || getMetric(tweet, ["retweet", "unretweet"]);
            const likes = fromGroupLabel(tweet, ["like"]) || getMetric(tweet, ["like", "unlike"]);
            const views = fromGroupLabel(tweet, ["view"]);

            if (text && username && date) {
                // Skip tweets we've already captured on a previous scroll.
                const key = `${username}|${date}|${text}`;
                if (seen.has(key)) return;
                seen.add(key);
                results.push({ text, username, date, imageUrl, likes, comments, retweets, views });
            }
        });

        scrolled++;
        if (scrolled < scrollLimit) {
            // Generate a random delay between 2 and 3 seconds
            const delay = Math.floor(Math.random() * 1000) + 2000; // Random value between 2000ms and 3000ms
            setTimeout(() => {
                window.scrollTo(0, document.body.scrollHeight);
                scrape();
            }, delay);
        } else {
            const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "tweets.json";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    };

    scrape();
}
