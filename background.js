// Tweet Scraper — background service worker.
//
// Image content classifier. The popup's "Only images like the sample" mode asks
// this worker to look at a photo's actual PIXELS (not its URL) and decide whether
// it resembles the sample set the model was trained on (portrait/selfie photos of
// people). The worker fetches the image itself and uses an OffscreenCanvas, which
// avoids the cross-origin canvas taint that blocks reading page <img> pixels.

chrome.runtime.onInstalled.addListener(() => {
    console.log("Tweet Scraper Installed!");
});

// ---- Learned model -------------------------------------------------------
// One-class model trained offline on the 49 sample images. Features (computed on
// a 32x32 copy): skin-tone pixel ratio, mean luma, mean saturation, colorfulness.
// A photo "matches" when it has enough skin-tone area AND its feature vector is
// close (Mahalanobis distance) to the sample mean. Validated: ~82% of samples
// kept, ~83% of non-person control images rejected. Tune SKIN_MIN / DIST_MAX if
// live feature values drift from the offline ones.
const MODEL = {
    features: ["skin", "luma", "sat", "colorful"],
    mean: [0.37119, 0.44829, 0.25378, 0.11622],
    std:  [0.20515, 0.13114, 0.09400, 0.04355],
    skinMin: 0.12,
    distMax: 2.9174
};

const S = 32; // analysis resolution
const cache = new Map(); // url -> result, so repeated images aren't refetched

// Extract [skin, luma, sat, colorful] from RGBA pixel data of an S*S image.
function extractFeatures(data) {
    const n = S * S;
    let skin = 0, lumaSum = 0, satSum = 0;
    const rg = new Float64Array(n), yb = new Float64Array(n);
    for (let i = 0, p = 0; i < n; i++, p += 4) {
        const r = data[p], g = data[p + 1], b = data[p + 2];
        const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
        const y  = 0.299 * r + 0.587 * g + 0.114 * b;
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

function classify(feat) {
    let d = 0;
    for (let i = 0; i < feat.length; i++) {
        const z = (feat[i] - MODEL.mean[i]) / MODEL.std[i];
        d += z * z;
    }
    const dist = Math.sqrt(d);
    return {
        match: feat[0] >= MODEL.skinMin && dist <= MODEL.distMax,
        dist: +dist.toFixed(3),
        skin: +feat[0].toFixed(3)
    };
}

async function classifyImage(url) {
    if (cache.has(url)) return cache.get(url);
    let out;
    try {
        const resp = await fetch(url);
        const blob = await resp.blob();
        const bmp = await createImageBitmap(blob);
        const canvas = new OffscreenCanvas(S, S);
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        ctx.drawImage(bmp, 0, 0, S, S);
        const { data } = ctx.getImageData(0, 0, S, S);
        out = classify(extractFeatures(data));
    } catch (e) {
        out = { match: false, error: String(e) };
    }
    cache.set(url, out);
    return out;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.type === "classifyImage") {
        classifyImage(msg.url).then(sendResponse);
        return true; // keep the message channel open for the async response
    }
});
