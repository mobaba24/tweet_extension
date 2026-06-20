# نصب افزونه Tweet_Extension

> **Fork note (v1.5):** Each scraped tweet now also includes engagement metrics
> and account info. Scraping produces **two downloads** — `tweets.json` (raw) and
> `tweets.csv` (spreadsheet-friendly, UTF‑8 BOM so Persian/emoji render in Excel).
> The popup has an **Image filter** dropdown: `All posts`, `Only posts with an
> image`, or **`Only images like the sample`** (solo female portraits). Each record
> looks like:
>
> ```json
> {
>   "username": "Display Name",
>   "handle": "@theaccount",
>   "gender": "male",
>   "date": "2024-01-01T00:00:00.000Z",
>   "likes": 345,
>   "comments": 12,
>   "retweets": 5,
>   "views": 78910,
>   "imageCount": 2,
>   "imageUrl": "https://pbs.twimg.com/media/...",
>   "images": ["https://pbs.twimg.com/media/...", "..."],
>   "faceCount": 1,
>   "faceGender": "female",
>   "faceProb": 0.97,
>   "text": "..."
> }
> ```
>
> Notes:
> - **Image filter.** `Only posts with an image` finds real photo attachments by
>   URL (`pbs.twimg.com/media/<id>`; avatars and link-card thumbs are excluded).
>   **`Only images like the sample`** analyses each photo's **content** with a
>   bundled **face + gender model** (`face-api.js` / TensorFlow.js, ~2 MB). It runs
>   in an **offscreen document** (the model needs DOM; the service worker doesn't
>   have it). A post is kept only when a photo is a **solo female portrait**:
>   exactly one face, classified `female` with probability ≥ `0.65`, and the face
>   spanning ≥ `7%` of the image width. This rejects landscapes / screenshots /
>   desks / collages / graphics (0 faces), group shots & news stills (>1 face),
>   and men. `faceCount` / `faceGender` / `faceProb` are written to each record so
>   you can inspect and re-threshold. Thresholds live in `background.js`
>   (`FACE.minGenderProb`, `FACE.minFaceWidthFrac`). If the model fails to load,
>   it falls back to a skin-tone heuristic so scraping still works. Needs the
>   `pbs.twimg.com` host permission to read image pixels. It is a statistical
>   model, not perfect identification.
> - `images` lists every photo on the tweet (X allows up to 4); `imageCount` is
>   how many; `imageUrl` is the first (or `"none"`).
> - **Counts** come from X's locale-stable `data-testid` buttons and the
>   engagement bar's `aria-label`; abbreviated values (`1.2K`, `3M`) are expanded
>   to integers.
> - **`handle`** is the `@username`, read from the User-Name block or the tweet
>   permalink.
> - **`gender`** is *inferred* from the first given name in the display name
>   (X exposes no gender field). It is tuned for **Persian/Iranian names**: the
>   dictionary holds both Persian-script forms and common Latin transliterations
>   (e.g. حسین / Hossein / Hosein / Hussein), names are normalised before lookup
>   (Arabic↔Persian yeh/kaf, diacritics, ZWNJ in compounds like علی‌رضا), and
>   leading honorifics (Dr, Eng, Seyed, Haj, دکتر، مهندس، سید، حاج …) are skipped.
>   Returns `male` / `female` / `unknown`; ambiguous/unknown names stay `unknown`.
>   Still best-effort — treat it as a heuristic, not ground truth.
> - Duplicate tweets across scrolls are de-duplicated, and `x.com` was added to
>   the host permissions alongside `twitter.com`.

## مراحل نصب افزونه

### 1. دانلود فایل‌های افزونه
ابتدا فایل‌های مورد نیاز افزونه را از منبع مورد نظر (یا گیت‌هاب) دانلود کنید. این فایل‌ها باید شامل موارد زیر باشند:
- `background.js`
- `content.js`
- `icon.png`
- `manifest.json`
- `popup.html`
- `popup.js`
- `offscreen.html`
- `offscreen.js`
- `faceapi.js`
- `models/` (پوشه‌ی مدل تشخیص چهره/جنسیت — شامل ۴ فایل)

سپس تمام این فایل‌ها را در یک فولدر به نام **Tweet_Extension** قرار دهید. این فولدر را برای نصب افزونه به مرورگر معرفی خواهید کرد.

---

### 2. نصب افزونه در مرورگر

#### **Google Chrome**
1. مرورگر Chrome را باز کنید.
2. به صفحه **Extensions** بروید:
   - روی آیکن سه نقطه در بالای سمت راست کلیک کنید.
   - به مسیر **More Tools > Extensions** بروید.
3. در صفحه Extensions، گزینه **Developer mode** را فعال کنید.
4. روی گزینه **Load unpacked** کلیک کنید.
5. به مسیر فولدر **Tweet_Extension** بروید و آن را انتخاب کنید.
6. افزونه با موفقیت به Chrome افزوده خواهد شد.

---

#### **Microsoft Edge**
1. مرورگر Edge را باز کنید.
2. به صفحه **Extensions** بروید:
   - روی آیکن سه نقطه در بالای سمت راست کلیک کنید.
   - به گزینه **Extensions** بروید.
3. در صفحه Extensions، گزینه **Developer mode** را فعال کنید.
4. روی گزینه **Load unpacked** کلیک کنید.
5. فولدر **Tweet_Extension** را انتخاب کنید.
6. افزونه با موفقیت به Edge افزوده خواهد شد.

---

موفق باشید! 🎉
