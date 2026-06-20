// Offscreen document: runs the bundled face-api.js (TensorFlow.js) models on
// tweet images. The service worker forwards each image URL here; we detect
// faces + gender and return a compact summary. background.js makes the final
// keep/skip decision.

let ready = null;
function init() {
    if (ready) return ready;
    ready = (async () => {
        const base = chrome.runtime.getURL("models");
        await faceapi.nets.tinyFaceDetector.loadFromUri(base);
        await faceapi.nets.ageGenderNet.loadFromUri(base);
    })();
    return ready;
}

const detectorOptions = new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 });

async function analyze(url) {
    await init();
    const resp = await fetch(url);
    const blob = await resp.blob();
    const bmp = await createImageBitmap(blob);

    const canvas = document.createElement("canvas");
    canvas.width = bmp.width;
    canvas.height = bmp.height;
    canvas.getContext("2d").drawImage(bmp, 0, 0);

    const results = await faceapi.detectAllFaces(canvas, detectorOptions).withAgeAndGender();
    const area = bmp.width * bmp.height || 1;
    return results.map(r => ({
        gender: r.gender,                                   // "male" | "female"
        genderProbability: r.genderProbability,
        age: Math.round(r.age),
        wFrac: r.detection.box.width / bmp.width,           // face width / image width
        boxFrac: (r.detection.box.width * r.detection.box.height) / area
    }));
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.target === "offscreen" && msg.type === "analyzeImage") {
        analyze(msg.url).then(sendResponse).catch(e => sendResponse({ error: String(e) }));
        return true; // async response
    }
});
