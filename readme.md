# نصب افزونه Tweet_Extension

> **Fork note (v1.3):** Each scraped tweet now also includes engagement metrics
> and account info. Scraping produces **two downloads** — `tweets.json` (raw) and
> `tweets.csv` (spreadsheet-friendly, UTF‑8 BOM so Persian/emoji render in Excel).
> The popup also has an **"Only posts with an image"** checkbox to gather just
> media posts. Each record looks like:
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
>   "text": "..."
> }
> ```
>
> Notes:
> - **"Only posts with an image"** filters out text-only tweets. A "post with an
>   image" is detected by a rule *learned from a sample URL set*: real photo
>   attachments are served from `pbs.twimg.com/media/<id>` (100% of the samples),
>   whereas avatars (`/profile_images/`) and link-card thumbnails (`/card_img/`)
>   are excluded. `images` lists every photo on the tweet (X allows up to 4);
>   `imageCount` is how many; `imageUrl` is the first (or `"none"`).
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
