"""GitHub Pages B1 ders paneline günlük yeni ders ekler.
Gereksinim: OPENAI_API_KEY ortam değişkeni.
"""

import base64
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


def create_lesson(date):
    prompt = f"""
Brezilya Portekizcesinde {date:%d/%m/%Y} tarihli
B1 seviyesinde günlük dil dersi için TAM bir HTML belgesi üret.

İÇERİK:
- Günlük hayattan özgün, 250-350 kelimelik Portekizce okuma metni.
- 10 okuduğunu anlama sorusu.
- 5 kelime bilgisi sorusu.
- 5 dil bilgisi sorusu.
- Toplam 20 soru.
- Her soruda 4 Portekizce seçenek ve tek doğru cevap.
- Soruların Türkçe açıklamaları.
- Türkçe açıklamalar dokununca açılabilsin.
- Cevapları kontrol eden çalışan JavaScript.
- 20 üzerinden başarı puanı.

KELİME ÇALIŞMASI:
- Metinden seçilmiş 10 önemli kelime.
- Türkçe solda, Portekizce sağda.
- Ortada ince dikey çizgi.
- Her kelime için Türkçe anlam.
- İki farklı Portekizce örnek cümle.
- Her örneğin Türkçe çevirisi.
- Kelimelere dokununca açıklama açılsın.
- Kelimeleri kaydetmek için localStorage kullan.

TASARIM:
- Nunito yazı tipi.
- Pastel krem ve açık yeşil renkler.
- Turuncu başlıklar.
- Hafif cam efekti.
- Yuvarlatılmış kartlar.
- Telefon ekranına uyumlu tasarım.
- Okunaklı ve düzenli yerleşim.

Tüm CSS ve JavaScript aynı HTML içinde olsun.
Harici JavaScript kütüphanesi kullanma.
Cevapları başlangıçta gösterme.

HTML çıktısı <!doctype html> ile başlasın.
Markdown kod bloğu kullanma.
"""

    payload = json.dumps({
        "model": MODEL,
        "input": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_output_tokens": 12000
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.load(response)

    text = "".join(
        c.get("text", "")
        for item in result.get("output", [])
        for c in item.get("content", [])
        if c.get("type") == "output_text"
    ).strip()

    text = re.sub(
        r"^```(?:html)?\s*|\s*```$",
        "",
        text,
        flags=re.I
    ).strip()

    if "<html" not in text.lower() or "</html>" not in text.lower():
        raise RuntimeError(
            "API geçerli bir HTML belgesi döndürmedi."
        )

    return text


def main():
    today = dt.datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).date()

    raw = INDEX.read_text(encoding="utf-8")

    dates_match = re.search(
        r"const lessonDates\s*=\s*(\[[^;]+\]);",
        raw
    )

    data_match = re.search(
        r'(<script id="lessonData" type="application/json">)(.*?)(</script>)',
        raw,
        re.S
    )

    if not dates_match or not data_match:
        raise RuntimeError(
            "index.html beklenen ders paneli yapısında değil."
        )

    dates = json.loads(
        dates_match.group(1).replace("'", '"')
    )

    lessons = json.loads(
        data_match.group(2)
    )

    if len(dates) != len(lessons):
        raise RuntimeError(
            "Ders tarihleri ile içerik sayısı eşleşmiyor."
        )

    day = today.isoformat()

    if day in dates:
        print(
            f"{day}: Ders zaten mevcut. "
            "Değişiklik yapılmadı."
        )
        return

    if dates and day < dates[-1]:
        raise RuntimeError(
            "Mevcut derslerin tarih sırası beklenenden farklı."
        )

    lesson = create_lesson(today)

    dates.append(day)

    lessons.append(
        base64.b64encode(
            lesson.encode("utf-8")
        ).decode("ascii")
    )

    raw = (
        raw[:data_match.start(2)]
        + json.dumps(
            lessons,
            ensure_ascii=True,
            separators=(",", ":")
        )
        + raw[data_match.end(2):]
    )

    raw = re.sub(
        r"const lessonDates\s*=\s*\[[^;]+\];",
        "const lessonDates="
        + json.dumps(dates, separators=(",", ":"))
        + ";",
        raw,
        count=1
    )

    INDEX.write_text(
        raw,
        encoding="utf-8"
    )

    print(
        f"{day}: Yeni ders eklendi. "
        f"Toplam {len(dates)} ders."
    )


if __name__ == "__main__":
    main()
