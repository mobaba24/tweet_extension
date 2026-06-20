"""Infer gender from an X display name's first given name.

Ported from the extension's popup.js <gender-subsystem> (same Persian-tuned
dictionary and normalisation). Returns "male" | "female" | "unknown".
"""
import re
import unicodedata
from gender_names_data import MALE_NAMES, FEMALE_NAMES, TITLE_WORDS


def _clean(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # strip accents/harakat
    s = s.replace("‌", "")           # ZWNJ -> join (علی‌رضا -> علیرضا)
    s = (s.replace("ي", "ی")    # Arabic yeh -> Persian yeh
           .replace("ى", "ی")   # alef maksura -> Persian yeh
           .replace("ك", "ک")   # Arabic kaf -> Persian keheh
           .replace("ة", "ه")   # teh marbuta -> heh
           .replace("ۀ", "ه"))  # heh with yeh -> heh
    return s.lower()


def _token(s: str) -> str:
    return "".join(ch for ch in _clean(s) if ch.isalpha())


MALE = {_token(x) for x in MALE_NAMES}
FEMALE = {_token(x) for x in FEMALE_NAMES}
TITLES = {_token(x) for x in TITLE_WORDS}
_overlap = MALE & FEMALE
MALE -= _overlap
FEMALE -= _overlap

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # runs of letters (incl. Persian)


def guess_gender(display_name: str) -> str:
    if not display_name:
        return "unknown"
    for tok in _TOKEN_RE.findall(_clean(display_name)):
        if tok in TITLES:
            continue                # skip Dr / Seyed / دکتر / سید ...
        if tok in MALE:
            return "male"
        if tok in FEMALE:
            return "female"
        return "unknown"           # first real given name decides
    return "unknown"


if __name__ == "__main__":
    tests = [
        ("محمدرضا کریمی", "male"), ("علی‌رضا احمدی", "male"),
        ("دکتر سعید محمدی", "male"), ("فاطمه زهرا", "female"),
        ("مهندس مریم رضایی", "female"), ("Reza Jahani", "male"),
        ("Nazanin", "female"), ("ميلاد", "male"), ("Acme Corp", "unknown"),
    ]
    ok = sum(guess_gender(n) == e for n, e in tests)
    for n, e in tests:
        print(f"{'OK' if guess_gender(n)==e else 'XX'}  {n!r:30s} -> {guess_gender(n)}")
    print(f"{ok}/{len(tests)} passed")
