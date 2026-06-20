# نصب افزونه Tweet_Extension

> **Fork note (v1.1):** Each scraped tweet now also includes engagement metrics —
> **likes** and **comments** counts, plus **retweets** and **views** as a bonus.
> The exported `tweets.json` objects look like:
>
> ```json
> {
>   "text": "...",
>   "username": "...",
>   "date": "2024-01-01T00:00:00.000Z",
>   "imageUrl": "none",
>   "likes": 345,
>   "comments": 12,
>   "retweets": 5,
>   "views": 78910
> }
> ```
>
> Counts come from X's locale-stable `data-testid` buttons and the engagement
> bar's `aria-label`, with abbreviated values (`1.2K`, `3M`) expanded to integers.
> Duplicate tweets across scrolls are de-duplicated, and `x.com` was added to the
> host permissions alongside `twitter.com`.

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
