#!/usr/bin/env python3
"""法国官方节假日爬虫 — data.gouv / Etalab jours fériés API。

数据源（法国政府开放数据）：
  https://calendrier.api.gouv.fr/jours-feries/metropole.json
  （dataset: https://www.data.gouv.fr/fr/datasets/jours-feries-en-france/）

取法国本土（métropole）口径（不含阿尔萨斯-摩泽尔省额外的耶稣受难日与
12/26）。官方数据覆盖当前年份前后 5 年（当前到 2031），全部年份均为官方。

用法：python3 fetch_holiday_france.py
输出：holiday-data-france.json
"""

import json
from datetime import date

import holiday_common as common

API_URL = "https://calendrier.api.gouv.fr/jours-feries/metropole.json"
DATASET_URL = "https://www.data.gouv.fr/fr/datasets/jours-feries-en-france/"

# API 节日名（法文）→ (中文名, 英文名)
FR_NAMES: dict[str, tuple[str, str]] = {
    "Jour de l'an": ("元旦", "New Year's Day"),
    "1er janvier": ("元旦", "New Year's Day"),
    "Lundi de Pâques": ("复活节星期一", "Easter Monday"),
    "Fête du Travail": ("劳动节", "Labour Day"),
    "1er mai": ("劳动节", "Labour Day"),
    "Victoire 1945": ("胜利日", "Victory in Europe Day"),
    "8 mai": ("胜利日", "Victory in Europe Day"),
    "Ascension": ("耶稣升天节", "Ascension Day"),
    "Lundi de Pentecôte": ("圣灵降临节", "Whit Monday"),
    "Fête nationale": ("国庆日", "Bastille Day"),
    "14 juillet": ("国庆日", "Bastille Day"),
    "Assomption": ("圣母升天", "Assumption Day"),
    "Toussaint": ("诸圣节", "All Saints' Day"),
    "Armistice 1918": ("停战日", "Armistice Day"),
    "11 novembre": ("停战日", "Armistice Day"),
    "Noël": ("圣诞节", "Christmas Day"),
    "Jour de Noël": ("圣诞节", "Christmas Day"),
}


def fr_name(raw: str) -> tuple[str, str]:
    """按 API 法文名取中英文；未知名称回退英文名。"""
    name = raw.strip()
    if name in FR_NAMES:
        return FR_NAMES[name]
    print(f"  [WARN] 未知法国假日名: {name}，使用英文回退", flush=True)
    return (name, name)


def main() -> None:
    raw = common.http_text(API_URL)
    if raw is None:
        raise SystemExit("calendrier.api.gouv.fr 抓取失败")
    payload = json.loads(raw)  # {"YYYY-MM-DD": "节日名", ...}

    days: set[str] = set()
    holiday_names: dict[str, dict[str, str]] = {}
    official_years: set[int] = set()
    for day_str, fr in payload.items():
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            continue
        if d.year in common.TARGET_YEARS:
            days.add(common.iso(d))
            official_years.add(d.year)
            zh, en = fr_name(fr)
            holiday_names[common.iso(d)] = {"zh": zh, "en": en}

    note = (
        "数据源：法国政府开放数据平台 jours fériés（法国本土 métropole，"
        "code du travail 口径）。不含阿尔萨斯-摩泽尔省额外假日（耶稣受难日、"
        "12/26）与海外省/大区当地假日；如需这些区域需另行分区文件。"
    )
    common.write_json(
        country="france",
        country_name="法国",
        holidays=days,
        official_years=official_years,
        source="data.gouv.fr / Etalab jours fériés（官方开放数据）",
        source_urls=[API_URL, DATASET_URL],
        note=note,
        holiday_names=holiday_names,
    )


if __name__ == "__main__":
    main()
