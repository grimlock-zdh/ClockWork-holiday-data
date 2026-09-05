#!/usr/bin/env python3
"""按国家生成 holiday-data-<country>.json（规则型国家）

规则来源：App 内置 StatutoryRule（ClockWork/Views/SharedCalendar.swift），
与 App 判断逻辑保持一致。每年生成日期列表，输出文件格式与 China 的
holiday-data.json 一致（holidays + extra_workdays + ranges + metadata）。

注意（重要）：这些是**规则推导**的简化数据：
- 不含基督教浮动假日（复活节/耶稣受难日/圣灵降临节等，英法德受影响）；
- 不含「逢周末顺延/补休」类规则（如日本振替休日、英美 observed day）；
- 仅作 v1 基线；上线/正式使用前请按各国官方口径核对补齐。

用法：python3 generate_statutory.py
输出：holiday-data-<country>.json
"""

import json
import calendar
from datetime import date, datetime, timezone

# 年份范围：与 App 远程数据 remoteYears 对齐
YEAR_START, YEAR_END = 2024, 2030

# 规则：month, day(=0 表示用第 N 个星期 X), weekday(1=周日..7=周六), ordinal
# （weekday/ordinal 语义与 App Calendar.current.component(.weekday) 一致）
RULES = {
    "japan": [
        (1, 1, None, None), (1, 0, 2, 2), (2, 11, None, None), (2, 23, None, None),
        (4, 29, None, None), (5, 3, None, None), (5, 4, None, None), (5, 5, None, None),
        (7, 0, 2, 3), (8, 11, None, None), (9, 0, 2, 3), (9, 23, None, None),
        (10, 0, 2, 2), (11, 3, None, None), (11, 23, None, None),
    ],
    "usa": [
        (1, 1, None, None), (1, 0, 2, 3), (2, 0, 2, 3), (5, 0, 2, -1),
        (6, 19, None, None), (7, 4, None, None), (9, 0, 2, 1), (10, 0, 2, 2),
        (11, 11, None, None), (11, 0, 5, 4), (12, 25, None, None),
    ],
    "uk": [
        (1, 1, None, None), (5, 0, 2, 1), (5, 0, 2, -1), (8, 0, 2, -1),
        (12, 25, None, None), (12, 26, None, None),
    ],
    "france": [
        (1, 1, None, None), (5, 1, None, None), (5, 8, None, None), (7, 14, None, None),
        (8, 15, None, None), (11, 1, None, None), (11, 11, None, None), (12, 25, None, None),
    ],
    "germany": [
        (1, 1, None, None), (1, 6, None, None), (5, 1, None, None), (10, 3, None, None),
        (12, 25, None, None), (12, 26, None, None),
    ],
}

COUNTRIES_ZH = {
    "japan": "日本", "usa": "美国", "uk": "英国",
    "france": "法国", "germany": "德国",
}


def nth_weekday(year, month, weekday, ordinal):
    """第 ordinal 个 weekday（ordinal<0 表示倒数）；weekday: 1=周日..7=周六"""
    days = [
        d for d in range(1, calendar.monthrange(year, month)[1] + 1)
        if date(year, month, d).isoweekday() % 7 + 1 == weekday  # isoweekday: 1=Mon
    ]
    if ordinal > 0:
        return days[ordinal - 1] if len(days) >= ordinal else None
    idx = len(days) + ordinal
    return days[idx] if 0 <= idx < len(days) else None


def holiday_dates_for_country(country):
    out = []
    for year in range(YEAR_START, YEAR_END + 1):
        for month, day, weekday, ordinal in RULES[country]:
            if weekday and ordinal:
                d = nth_weekday(year, month, weekday, ordinal)
                if d is None:
                    continue
            else:
                d = day
            out.append(f"{year:04d}-{month:02d}-{d:02d}")
    return sorted(set(out))


def main():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for country in RULES:
        holidays = holiday_dates_for_country(country)
        data = {
            "holidays": holidays,
            "extra_workdays": [],
            "ranges": [],
            "metadata": {
                "country": country,
                "countryName": COUNTRIES_ZH[country],
                "lastUpdate": generated_at[:10],
                "generatedAt": generated_at,
                "years": [YEAR_START, YEAR_END],
                "source": "App StatutoryRule 规则推导（v1 简化版）",
                "note": "规则型简化数据：不含基督教浮动假日与逢周末顺延/补休；正式使用前需按官方口径核对",
            },
        }
        fn = f"holiday-data-{country}.json"
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"{fn}: {len(holidays)} 天")


if __name__ == "__main__":
    main()
