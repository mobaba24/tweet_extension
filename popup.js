document.getElementById("startScraping").addEventListener("click", () => {
    const scrollLimit = document.getElementById("scrollLimit").value;
    const imagesOnly = document.getElementById("imagesOnly").checked;
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: scrapeTweets,
            args: [parseInt(scrollLimit), imagesOnly]
        });
    });
});

function scrapeTweets(scrollLimit, imagesOnly) {
    const results = [];
    const seen = new Set();
    let scrolled = 0;

    // <gender-subsystem>
    // ---- Gender inference from the display name ---------------------------
    // X exposes no gender field, so gender is INFERRED from the first given
    // name in the display name. Tuned for Persian/Iranian names: the dictionary
    // carries both Persian-script forms and common Latin transliterations, and
    // names are normalised before lookup (Arabic vs Persian yeh/kaf, diacritics,
    // ZWNJ, alef/hamza variants). Leading honorifics are skipped. Best-effort:
    // unrecognised or ambiguous names return "unknown".
    const clean = (s) => (s || "")
        .normalize("NFKD").replace(/\p{M}/gu, "")    // strip Latin accents + Arabic harakat
        .replace(/‌/g, "")                       // ZWNJ -> join (علی‌رضا -> علیرضا)
        .replace(/[يى]/g, "ی")         // Arabic yeh / alef-maksura -> Persian yeh
        .replace(/ك/g, "ک")                 // Arabic kaf -> Persian keheh
        .replace(/[ةۀ]/g, "ه")         // teh-marbuta / heh-yeh -> heh
        .toLowerCase();
    const token = (s) => clean(s).replace(/[^\p{L}]/gu, "");

    const MALE_NAMES = [
        // Western
        "james","john","robert","michael","william","david","richard","joseph","thomas","charles",
        "christopher","daniel","matthew","anthony","mark","donald","steven","paul","andrew","joshua",
        "kenneth","kevin","brian","george","edward","ronald","timothy","jason","jeffrey","ryan",
        "jacob","gary","nicholas","eric","jonathan","stephen","justin","scott","brandon","benjamin",
        "samuel","gregory","alexander","frank","patrick","raymond","jack","dennis","jerry","tyler",
        "aaron","jose","henry","adam","douglas","nathan","peter","zachary","kyle","ethan","jeremy",
        "carl","keith","roger","sean","austin","christian","jordan","jesse","bryan","gabriel","joe",
        "logan","alan","juan","albert","elijah","vincent","mason","roy","russell","philip","louis",
        "luke","oliver","liam","noah","lucas","leo","max",
        // Persian / Iranian — script + transliterations
        "محمد","mohammad","mohammed","muhammad","mohamad","mohamed",
        "احمد","ahmad","ahmed",
        "محمود","mahmoud","mahmood","mahmud",
        "علی","ali",
        "رضا","reza",
        "حسین","hossein","hosein","hussein","hosseyn","huseyn",
        "حسن","hassan","hasan",
        "مهدی","mehdi","mahdi",
        "امیر","amir","ameer",
        "عباس","abbas","abas",
        "جواد","javad",
        "سعید","saeed","saied","said","saeid",
        "مجید","majid","madjid",
        "مسعود","masoud","masood","masud",
        "ابراهیم","ebrahim","ibrahim",
        "اسماعیل","esmail","esmaeil","ismail","ismael",
        "یوسف","yousef","yusuf","yousof","yousuf","yoosef",
        "موسی","musa","mousa","moosa",
        "داوود","davood","davoud","davud","davod",
        "یعقوب","yaghoub","yaqoub","yaghub",
        "یحیی","yahya",
        "زکریا","zakaria","zakariya","zakaryah",
        "سلیمان","soleyman","soleiman","suleiman","soleyman",
        "ادریس","edris","idris",
        "طاها","taha","taaha",
        "طه",
        "سجاد","sajjad","sajad",
        "صادق","sadegh","sadeq","sadek",
        "صالح","saleh",
        "طاهر","taher",
        "عادل","adel",
        "عارف","aref","arif",
        "عرفان","erfan","irfan",
        "عماد","emad","imad",
        "فؤاد","foad","fouad","fuad",
        "قاسم","ghasem","qasem","ghassem",
        "کمال","kamal",
        "مالک","malek","malik",
        "مبین","mobin","mubin",
        "متین","matin",
        "میثم","meysam","maysam",
        "نوید","navid",
        "یونس","younes","younos","yunus","yoones",
        "بهرام","bahram",
        "کیوان","keyvan","kayvan","keivan",
        "کاوه","kaveh","kaweh",
        "آرش","arash","aarash",
        "بابک","babak",
        "بیژن","bijan","bizhan",
        "فرهاد","farhad",
        "فرید","farid","fareed",
        "فریدون","fereydoun","fereidoon","fereydon",
        "بهروز","behrouz","behrooz","behruz",
        "بهزاد","behzad",
        "پرویز","parviz","parwiz",
        "خسرو","khosro","khosrow","khosrov",
        "داریوش","dariush","daryoosh","darioush","daryush",
        "جمشید","jamshid",
        "سهراب","sohrab",
        "سیامک","siamak","siyamak",
        "شاهین","shahin",
        "شهرام","shahram",
        "شهریار","shahriar","shahryar",
        "کامران","kamran",
        "کیان","kian","kiyan",
        "کوروش","kourosh","koroush","cyrus","kuroosh",
        "مانی","mani",
        "مازیار","maziar","mazyar",
        "مهران","mehran",
        "مهرداد","mehrdad",
        "میلاد","milad",
        "نادر","nader",
        "نیما","nima",
        "پارسا","parsa",
        "پویا","pouya","pooya",
        "پدرام","pedram",
        "رامین","ramin",
        "رستم","rostam","rustam",
        "سامان","saman",
        "سینا","sina",
        "سروش","soroush","soroosh",
        "وحید","vahid",
        "یاسر","yaser","yasser",
        "ناصر","naser","nasser",
        "منصور","mansour","mansoor","mansur",
        "مرتضی","morteza","mortaza",
        "مصطفی","mostafa","mustafa","mustapha",
        "مجتبی","mojtaba",
        "هادی","hadi",
        "هومن","houman","hooman",
        "هوشنگ","houshang","hooshang",
        "ایرج","iraj",
        "اردشیر","ardeshir",
        "اشکان","ashkan",
        "آرمان","arman","aarman",
        "آرمین","armin",
        "امین","amin","ameen",
        "احسان","ehsan","ehssan",
        "علیرضا","alireza",
        "محمدرضا","mohammadreza","mohamadreza",
        "امیرحسین","amirhossein","amirhosein",
        "امیرعلی","amirali",
        "امیرمحمد","amirmohammad",
        "محمدعلی","mohammadali",
        "محمدجواد","mohammadjavad",
        "محمدحسین","mohammadhossein",
        "محمدامین","mohammadamin",
        "محمدمهدی","mohammadmehdi",
        "حمید","hamid","hameed",
        "حمیدرضا","hamidreza",
        "غلامرضا","gholamreza",
        "علی‌اکبر","aliakbar",
        "فرشاد","farshad",
        "فرزاد","farzad",
        "فرزین","farzin",
        "کیارش","kiarash",
        "کسری","kasra",
        "آریا","arya","aria",
        "آرین","arian","aryan",
        "بردیا","bardia","bardya",
        "برنا","borna",
        "دانیال","danial","daniyal",
        "یاشار","yashar",
        "یزدان","yazdan",
        "پاشا","pasha",
        "سلمان","salman",
        "حامد","hamed",
        "کیومرث","kioumars","kayoumars",
        "منوچهر","manouchehr","manoochehr",
        "فریبرز","fariborz",
        "بهمن","bahman",
        "اسفندیار","esfandiar","esfandyar",
        "فرامرز","faramarz",
        "نریمان","nariman",
        "شایان","shayan","shaian",
        "شاهرخ","shahrokh",
        "شروین","shervin","sherwin",
        "سپهر","sepehr",
        "رایان","rayan",
        "آبتین","abtin",
        "آرتین","artin",
        "آرشام","arsham",
        "بنیامین","benyamin",
        "ماهان","mahan",
        "هیراد","hirad",
        "یاسین","yasin","yassin",
        "کیانوش","kianoosh","kianush",
        "نیکان","nikan",
        "رادین","radin",
        "هیربد","hirbod"
    ];

    const FEMALE_NAMES = [
        // Western
        "mary","patricia","jennifer","linda","elizabeth","barbara","susan","jessica","karen","nancy",
        "lisa","betty","margaret","sandra","ashley","kimberly","emily","donna","michelle","carol",
        "amanda","dorothy","melissa","deborah","stephanie","rebecca","sharon","laura","cynthia",
        "kathleen","amy","angela","shirley","anna","brenda","pamela","emma","nicole","helen",
        "samantha","katherine","christine","rachel","carolyn","janet","catherine","heather","diane",
        "olivia","julie","joyce","victoria","ruth","virginia","lauren","kelly","christina","joan",
        "evelyn","judith","megan","andrea","cheryl","hannah","jacqueline","martha","gloria","teresa",
        "madison","frances","kathryn","jean","abigail","alice","julia","sophia","grace","denise",
        "amber","marilyn","danielle","beverly","isabella","diana","natalie","brittany","charlotte",
        "marie","kayla","alexis","mia","ava","chloe","zoe",
        // Persian / Iranian — script + transliterations
        "فاطمه","fatemeh","fatima","fateme","fatemah",
        "زهرا","zahra","zara","zahraa",
        "مریم","maryam","mariam",
        "زینب","zeynab","zaynab","zeinab",
        "معصومه","masoumeh","masumeh","masoomeh",
        "نرگس","narges","nargess",
        "لیلا","leila","leyla","laila","layla",
        "مینا","mina",
        "مهسا","mahsa",
        "مهناز","mahnaz",
        "مژگان","mojgan","mozhgan",
        "شیرین","shirin","shireen",
        "شهلا","shahla",
        "شیما","shima","sheema",
        "سارا","sara","sarah",
        "سحر","sahar",
        "ساناز","sanaz",
        "سمیرا","samira","sameera",
        "سمیه","somayeh","somaye","somayyeh",
        "سپیده","sepideh","sepide",
        "ستاره","setareh","setare",
        "نازنین","nazanin","nazaneen",
        "نگار","negar",
        "نسرین","nasrin","nasreen",
        "نسیم","nasim","naseem",
        "نیلوفر","niloofar","nilufar","niloufar","nilofar",
        "نوشین","nooshin","nushin",
        "پریسا","parisa",
        "پریا","paria","parya",
        "پگاه","pegah",
        "پرنیان","parnian",
        "رویا","roya","roia",
        "ریحانه","reyhaneh","reihaneh","rayhaneh",
        "راضیه","razieh","raziyeh",
        "زیبا","ziba",
        "ژاله","zhaleh","jaleh",
        "سودابه","soodabeh","sudabeh",
        "سوسن","sousan","soosan",
        "شقایق","shaghayegh",
        "شکوفه","shokoufeh","shokufeh",
        "صبا","saba",
        "طاهره","tahereh",
        "عاطفه","atefeh","atefe",
        "غزل","ghazal","qazal",
        "غزاله","ghazaleh","ghazale",
        "فرانک","faranak",
        "فرزانه","farzaneh",
        "فرشته","fereshteh","fereshte",
        "فریبا","fariba",
        "فرحناز","farahnaz",
        "فروغ","forough","forugh","foroogh",
        "فیروزه","firouzeh","firoozeh",
        "کتایون","katayoun","katayon",
        "کیمیا","kimia","kimiya",
        "گلاره","gelareh","golareh",
        "گلنار","golnar",
        "گلناز","golnaz",
        "لادن","ladan","laden",
        "لاله","laleh",
        "مرجان","marjan",
        "محبوبه","mahboubeh","mahbubeh",
        "ملیحه","maliheh",
        "منیر","monir",
        "مهتاب","mahtab",
        "مهرناز","mehrnaz",
        "مهری","mehri",
        "مهسان","mahsan",
        "مونا","mona","muna",
        "نازیلا","nazila",
        "ندا","neda",
        "هانیه","haniyeh","haniye",
        "هدیه","hediyeh","hedye",
        "هلیا","helia","heliya",
        "یاسمن","yasaman","yasmin","yasamin",
        "آرزو","arezou","arezoo","arzu",
        "آزاده","azadeh",
        "آناهیتا","anahita","anahid",
        "الناز","elnaz",
        "الهام","elham",
        "الهه","elahe","elaheh",
        "آیدا","aida","ayda",
        "بهاره","bahareh","bahare",
        "بهناز","behnaz",
        "بنفشه","banafsheh","banafshe",
        "تارا","tara",
        "ترانه","taraneh",
        "تهمینه","tahmineh",
        "ثریا","soraya","sorayya",
        "حدیث","hadis","hadith",
        "حنانه","hananeh",
        "خاطره","khatereh",
        "دریا","darya","daria",
        "دنیا","donya","donia",
        "راحله","raheleh",
        "رعنا","rana",
        "رها","raha",
        "زری","zari",
        "ساغر","saghar",
        "سایه","sayeh","saye",
        "سلما","salma",
        "سمانه","samaneh",
        "سونیا","sonia","sonya",
        "شادی","shadi",
        "شبنم","shabnam",
        "شراره","sharareh",
        "شهرزاد","shahrzad",
        "شهره","shohreh",
        "شیدا","sheyda","shida","sheida",
        "عسل","asal",
        "مرضیه","marziyeh","marzieh",
        "مژده","mozhdeh","mojdeh",
        "مهدیه","mahdiyeh","mahdieh",
        "میترا","mitra",
        "نجمه","najmeh","najme",
        "نیایش","niayesh",
        "نیوشا","niousha","newsha",
        "هستی","hasti",
        "یکتا","yekta",
        "آتنا","atena",
        "آتوسا","atoosa","atousa",
        "بیتا","bita",
        "پانیذ","paniz",
        "پرستو","parastoo","parastou",
        "پریناز","parinaz",
        "حورا","hoora","hura",
        "درسا","dorsa",
        "دلارام","delaram",
        "رکسانا","roxana","roksana",
        "ژینا","zhina","jina",
        "سوگند","sogand","sougand",
        "شمیم","shamim",
        "طناز","tannaz","tanaz",
        "عطیه","atiyeh","atieh",
        "فرنوش","farnoush","farnush",
        "کوثر","kowsar","kosar",
        "گلسا","golsa",
        "لیلی","leyli","leili",
        "مائده","maedeh","maede",
        "مبینا","mobina",
        "محیا","mahya",
        "مهدیس","mahdis",
        "ملیکا","melika",
        "ملینا","melina",
        "مهلا","mahla",
        "ناهید","nahid","naheed",
        "نسترن","nastaran",
        "نفیسه","nafiseh",
        "هیلا","hila",
        "ویدا","vida",
        "سمین","samin",
        "ثنا","sana",
        "هانا","hana",
        "آرمیتا","armita",
        "ارغوان","arghavan",
        "کیانا","kiana",
        "مهین","mahin"
    ];

    const TITLE_WORDS = [
        "dr","doctor","eng","engineer","prof","professor","mr","mrs","ms","sir",
        "seyed","seyyed","sayed","sayyed","seyd","haj","haji","hajj","ostad","ustad",
        "sheikh","shaikh","imam","emam","agha","aqa","khanom","khanoom","mohandes","hazrat","mirza",
        "دکتر","مهندس","استاد","سید","سیده","حاج","حاجی","آقا","آقای","خانم",
        "شیخ","امام","علامه","مولانا","پروفسور","حضرت","ملا","میرزا"
    ];

    const MALE = new Set(MALE_NAMES.map(token));
    const FEMALE = new Set(FEMALE_NAMES.map(token));
    const TITLES = new Set(TITLE_WORDS.map(token));
    // Safety: any name that landed in both buckets is ambiguous -> unknown.
    for (const t of [...MALE]) if (FEMALE.has(t)) { MALE.delete(t); FEMALE.delete(t); }

    const guessGender = (displayName) => {
        if (!displayName) return "unknown";
        const tokens = clean(displayName).split(/[^\p{L}]+/u).filter(Boolean);
        for (const t of tokens) {
            if (TITLES.has(t)) continue;        // skip Dr / Seyed / دکتر / سید ...
            if (MALE.has(t)) return "male";
            if (FEMALE.has(t)) return "female";
            return "unknown";                   // first real given name decides
        }
        return "unknown";
    };
    // </gender-subsystem>

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

    // ---- Image detection (learned from the sample URL set) -----------------
    // "Posts with an image" = posts carrying a real photo attachment. Every URL
    // in the sample set is served from pbs.twimg.com/media/<id> with an id made
    // of [A-Za-z0-9_-] (100% coverage of the 51 samples). Avatars
    // (/profile_images/) and link-card thumbnails (/card_img/) deliberately do
    // NOT match, so only genuine post photos count.
    const MEDIA_RE = /^https?:\/\/pbs\.twimg\.com\/media\/[A-Za-z0-9_-]+/i;
    const getImages = (tweet) => {
        const urls = [];
        tweet.querySelectorAll('[data-testid="tweetPhoto"] img, img[src*="pbs.twimg.com/media/"]').forEach(img => {
            const src = img.getAttribute("src") || "";
            if (MEDIA_RE.test(src) && !urls.includes(src)) urls.push(src);
        });
        return urls;
    };

    // ---- CSV export --------------------------------------------------------
    const toCsv = (rows) => {
        const headers = ["username", "handle", "gender", "date", "likes", "comments", "retweets", "views", "imageCount", "imageUrl", "images", "text"];
        const esc = (v) => {
            if (Array.isArray(v)) v = v.join(" | ");
            return '"' + String(v ?? "").replace(/"/g, '""').replace(/\r?\n/g, " ") + '"';
        };
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

            const images = getImages(tweet);
            const imageCount = images.length;
            const imageUrl = images[0] || "none";

            const handle = getHandle(tweet);
            const gender = guessGender(username);

            const comments = fromGroupLabel(tweet, ["repl", "comment"]) || getMetric(tweet, ["reply"]);
            const retweets = fromGroupLabel(tweet, ["repost", "retweet"]) || getMetric(tweet, ["retweet", "unretweet"]);
            const likes = fromGroupLabel(tweet, ["like"]) || getMetric(tweet, ["like", "unlike"]);
            const views = fromGroupLabel(tweet, ["view"]);

            if (text && username && date) {
                // "Only posts with an image" option: skip text-only tweets.
                if (imagesOnly && imageCount === 0) return;
                // Skip tweets already captured on a previous scroll.
                const key = `${handle || username}|${date}|${text}`;
                if (seen.has(key)) return;
                seen.add(key);
                results.push({ username, handle, gender, date, likes, comments, retweets, views, imageCount, imageUrl, images, text });
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
