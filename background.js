// Tweet Scraper — background service worker.
//
// Image content classifier for the popup's "Only images like the sample" mode.
// Primary path: a bundled face/gender model (face-api.js) running in an offscreen
// document — it counts people and reads each face's gender, so we can keep only
// SOLO FEMALE portraits/selfies and reject landscapes/desks/collages/graphics
// (0 faces), groups & news stills (>1 face), and men. If the model can't load,
// we fall back to the lightweight skin-tone heuristic so the extension still runs.

chrome.runtime.onInstalled.addListener(() => {
    console.log("Tweet Scraper Installed!");
});

// ===== Decision thresholds (tune live if needed) ==========================
const FACE = {
    minGenderProb: 0.65,    // confidence required to call a face "female"
    minFaceWidthFrac: 0.07  // face must span >=7% of image width (portrait, not a tiny bg person)
};

function decideFromFaces(faces) {
    if (!Array.isArray(faces) || faces.length === 0) return { match: false, reason: "no-face", faceCount: 0 };
    if (faces.length > 1) return { match: false, reason: "group", faceCount: faces.length };
    const f = faces[0];
    const isFemale = f.gender === "female" && f.genderProbability >= FACE.minGenderProb;
    const bigEnough = f.wFrac >= FACE.minFaceWidthFrac;
    const match = isFemale && bigEnough;
    return {
        match,
        reason: match ? "solo-female" : (!isFemale ? "not-female" : "face-too-small"),
        faceCount: 1,
        faceGender: f.gender,
        faceProb: +Number(f.genderProbability).toFixed(3)
    };
}

// ---- Offscreen document management ---------------------------------------
let creating = null;
async function ensureOffscreen() {
    const has = chrome.offscreen.hasDocument && await chrome.offscreen.hasDocument();
    if (has) return;
    if (!creating) {
        creating = chrome.offscreen.createDocument({
            url: "offscreen.html",
            reasons: ["DOM_SCRAPING"],
            justification: "Run a local face/gender model on tweet images to filter posts."
        }).catch(() => {}); // ignore "already exists" races
    }
    await creating;
    creating = null;
}

// ---- Fallback skin-tone heuristic (v1.4 model) ---------------------------
const MODEL = { mean: [0.37119, 0.44829, 0.25378, 0.11622], std: [0.20515, 0.13114, 0.094, 0.04355], skinMin: 0.12, distMax: 2.9174 };
const S = 32;

function skinFeatures(data) {
    const n = S * S;
    let skin = 0, lumaSum = 0, satSum = 0;
    const rg = new Float64Array(n), yb = new Float64Array(n);
    for (let i = 0, p = 0; i < n; i++, p += 4) {
        const r = data[p], g = data[p + 1], b = data[p + 2];
        const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
        const y = 0.299 * r + 0.587 * g + 0.114 * b;
        const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
        const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;
        const rgbRule = r > 95 && g > 40 && b > 20 && (mx - mn) > 15 && Math.abs(r - g) > 15 && r > g && r > b;
        const yccRule = cr >= 135 && cr <= 180 && cb >= 85 && cb <= 135 && y >= 80;
        if (rgbRule || yccRule) skin++;
        lumaSum += y / 255;
        satSum += (mx - mn) / (mx + 1e-6);
        rg[i] = Math.abs(r - g);
        yb[i] = Math.abs(0.5 * (r + g) - b);
    }
    const stat = (arr) => {
        let m = 0; for (let i = 0; i < arr.length; i++) m += arr[i]; m /= arr.length;
        let s = 0; for (let i = 0; i < arr.length; i++) s += (arr[i] - m) * (arr[i] - m);
        return { mean: m, std: Math.sqrt(s / arr.length) };
    };
    const a = stat(rg), c = stat(yb);
    const colorful = (Math.sqrt(a.std * a.std + c.std * c.std) + 0.3 * Math.sqrt(a.mean * a.mean + c.mean * c.mean)) / 255;
    return [skin / n, lumaSum / n, satSum / n, colorful];
}

async function skinClassify(url) {
    const resp = await fetch(url);
    const blob = await resp.blob();
    const bmp = await createImageBitmap(blob);
    const canvas = new OffscreenCanvas(S, S);
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(bmp, 0, 0, S, S);
    const feat = skinFeatures(ctx.getImageData(0, 0, S, S).data);
    let d = 0;
    for (let i = 0; i < feat.length; i++) { const z = (feat[i] - MODEL.mean[i]) / MODEL.std[i]; d += z * z; }
    const dist = Math.sqrt(d);
    return { method: "skin", match: feat[0] >= MODEL.skinMin && dist <= MODEL.distMax, skin: +feat[0].toFixed(3) };
}

// ---- Public entry point --------------------------------------------------
const cache = new Map(); // url -> result
async function classifyImage(url) {
    if (cache.has(url)) return cache.get(url);
    let out;
    try {
        await ensureOffscreen();
        const faces = await chrome.runtime.sendMessage({ target: "offscreen", type: "analyzeImage", url });
        if (faces && faces.error) throw new Error(faces.error);
        out = { method: "face", ...decideFromFaces(faces) };
    } catch (e) {
        // Model unavailable — degrade to the skin heuristic so scraping still works.
        try { out = { ...(await skinClassify(url)), note: "face-model-failed: " + e }; }
        catch (e2) { out = { match: false, error: String(e2) }; }
    }
    cache.set(url, out);
    return out;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.type === "classifyImage") {
        classifyImage(msg.url).then(sendResponse);
        return true; // keep the channel open for the async response
    }
});
