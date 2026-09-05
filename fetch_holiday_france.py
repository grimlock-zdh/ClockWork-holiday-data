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


def main() -> None:
    raw = common.http_text(API_URL)
    if raw is None:
        raise SystemExit("calendrier.api.gouv.fr 抓取失败")
    payload = json.loads(raw)  # {"YYYY-MM-DD": "节日名", ...}

    days: set[str] = set()
    official_years: set[int] = set()
    for day_str in payload:
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            continue
        if d.year in common.TARGET_YEARS:
            days.add(common.iso(d))
            official_years.add(d.year)

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
    )


if __name__ == "__main__":
    main()
