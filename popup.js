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

    // ---- First-name -> gender dictionaries (offline, best-effort) ----------
    // X profiles do not expose a gender field, so we infer it from the first
    // token of the display name. Covers common Western + Persian/Arabic names;
    // anything unrecognised becomes "unknown".
    const MALE = new Set(["james","john","robert","michael","william","david","richard","joseph","thomas","charles","christopher","daniel","matthew","anthony","mark","donald","steven","paul","andrew","joshua","kenneth","kevin","brian","george","edward","ronald","timothy","jason","jeffrey","ryan","jacob","gary","nicholas","eric","jonathan","stephen","larry","justin","scott","brandon","benjamin","samuel","gregory","alexander","frank","patrick","raymond","jack","dennis","jerry","tyler","aaron","jose","henry","adam","douglas","nathan","peter","zachary","kyle","walter","ethan","jeremy","harold","carl","keith","roger","gerald","sean","austin","christian","jordan","jesse","bryan","billy","bruce","gabriel","joe","logan","alan","juan","albert","elijah","wayne","randy","vincent","mason","roy","ralph","bobby","russell","philip","eugene","louis","luke","oliver","liam","noah","lucas","leo","max","mohammad","mohammed","muhammad","ahmad","ahmed","ali","hassan","hossein","hussein","reza","mehdi","omar","ibrahim","mustafa","mahmoud","karim","hamid","saeed","javad","abbas","kamran","behzad","farhad","arash","amir","navid","pouya","sina","kourosh","dariush","bijan","parsa","kian","babak","ramin","shahin","vahid","milad","yousef","yusuf","khaled","tariq","bilal","hadi","majid","kaveh","payam","soroush","ehsan","mojtaba","morteza","nima","peyman","saman","shayan"]);
    const FEMALE = new Set(["mary","patricia","jennifer","linda","elizabeth","barbara","susan","jessica","sarah","karen","nancy","lisa","betty","margaret","sandra","ashley","kimberly","emily","donna","michelle","carol","amanda","dorothy","melissa","deborah","stephanie","rebecca","sharon","laura","cynthia","kathleen","amy","angela","shirley","anna","brenda","pamela","emma","nicole","helen","samantha","katherine","christine","rachel","carolyn","janet","maria","catherine","heather","diane","olivia","julie","joyce","victoria","ruth","virginia","lauren","kelly","christina","joan","evelyn","judith","megan","andrea","cheryl","hannah","jacqueline","martha","gloria","teresa","sara","madison","frances","kathryn","jean","abigail","alice","julia","sophia","grace","denise","amber","marilyn","danielle","beverly","isabella","diana","natalie","brittany","charlotte","marie","kayla","alexis","mia","ava","chloe","zoe","fatima","fatemeh","zahra","maryam","leila","layla","laleh","nasrin","mahsa","niloofar","shirin","parisa","neda","yasmin","yasaman","narges","samira","nazanin","elnaz","golnaz","roya","azadeh","mona","donya","setareh","hana","dina","aisha","amina","khadija","mina","sahar","banafsheh","tara","sana","rana","negar","shaghayegh","mahnaz","forough","pegah"]);

    const guessGender = (displayName) => {
        if (!displayName) return "unknown";
        // Drop emoji/punctuation, keep letters, take the first token.
        const cleaned = displayName.normalize("NFD").replace(/[^\p{L}\s]/gu, " ").trim();
        const first = cleaned.split(/\s+/)[0]?.toLowerCase();
        if (!first) return "unknown";
        if (MALE.has(first)) return "male";
        if (FEMALE.has(first)) return "female";
        return "unknown";
    };

    // ---- Engagement-count helpers -----------------------------------------
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
    // (reply / retweet / like / unlike) are stable across UI languages.
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

    // The engagement bar's role="group" aria-label holds the exact counts, e.g.
    // "12 replies, 5 reposts, 345 likes, 6 bookmarks, 78910 views".
    const fromGroupLabel = (tweet, words) => {
        const label = tweet.querySelector('div[role="group"]')?.getAttribute("aria-label");
        if (!label) return 0;
        for (const word of words) {
            const m = label.match(new RegExp(`([\\d,.]+)\\s+${word}`, "i"));
            if (m) return parseCount(m[1]);
        }
        return 0;
    };

    // The @handle: prefer an "@"-prefixed span in the User-Name block, else
    // parse it out of the tweet permalink (/<handle>/status/<id>).
    const getHandle = (tweet) => {
        const nameBlock = tweet.querySelector('[data-testid="User-Name"]');
        if (nameBlock) {
            for (const span of nameBlock.querySelectorAll("span")) {
                const t = span.innerText?.trim();
                if (t && t.startsWith("@")) return t;
            }
        }
        const link = tweet.querySelector('a[href*="/status/"]')?.getAttribute("href");
        if (link) {
            const handle = link.split("/")[1];
            if (handle && handle !== "i") return "@" + handle;
        }
        return "";
    };

    // ---- CSV export --------------------------------------------------------
    const toCsv = (rows) => {
        const headers = ["username", "handle", "gender", "date", "likes", "comments", "retweets", "views", "imageUrl", "text"];
        const esc = (v) => '"' + String(v ?? "").replace(/"/g, '""').replace(/\r?\n/g, " ") + '"';
        const lines = [headers.join(",")];
        rows.forEach(r => lines.push(headers.map(h => esc(r[h])).join(",")));
        return lines.join("\r\n");
    };

    const download = (data, filename, type) => {
        const blob = new Blob([data], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    };

    const scrape = () => {
        document.querySelectorAll("article").forEach(tweet => {
            const text = tweet.querySelector("div[lang]")?.innerText;
            const username = tweet.querySelector("div span span")?.innerText;
            const date = tweet.querySelector("time")?.getAttribute("datetime");
            const imageUrl = tweet.querySelector("img[alt='Image']")?.getAttribute("src") || "none";

            const handle = getHandle(tweet);
            const gender = guessGender(username);

            const comments = fromGroupLabel(tweet, ["repl", "comment"]) || getMetric(tweet, ["reply"]);
            const retweets = fromGroupLabel(tweet, ["repost", "retweet"]) || getMetric(tweet, ["retweet", "unretweet"]);
            const likes = fromGroupLabel(tweet, ["like"]) || getMetric(tweet, ["like", "unlike"]);
            const views = fromGroupLabel(tweet, ["view"]);

            if (text && username && date) {
                // Skip tweets already captured on a previous scroll.
                const key = `${handle || username}|${date}|${text}`;
                if (seen.has(key)) return;
                seen.add(key);
                results.push({ username, handle, gender, date, likes, comments, retweets, views, imageUrl, text });
            }
        });

        scrolled++;
        if (scrolled < scrollLimit) {
            // Random delay between 2 and 3 seconds.
            const delay = Math.floor(Math.random() * 1000) + 2000;
            setTimeout(() => {
                window.scrollTo(0, document.body.scrollHeight);
                scrape();
            }, delay);
        } else {
            // Two exports: JSON (raw) + CSV (spreadsheet-friendly, BOM for Excel).
            download(JSON.stringify(results, null, 2), "tweets.json", "application/json");
            download("\uFEFF" + toCsv(results), "tweets.csv", "text/csv;charset=utf-8;");
        }
    };

    scrape();
}
