#!/usr/bin/env python3
"""德国法定节假日数据 — 官方法定口径 + 官方页面核对。

背景：德国节假日由各州立法（Länderhoheit），联邦层面没有统一的逐年
发布日期表。全德 16 州都一致的全国性法定假日共 9 天（联邦内政部 BMI
口径）：Neujahr、Karfreitag、Ostermontag、1. Mai、Christi Himmelfahrt、
Pfingstmontag、3. Oktober（Tag der Deutschen Einheit）、25./26. Dezember。

实现：
  1. 按各州 Feiertagsgesetz 的统一法定规则计算 2024-2030 日期
     （复活节系假日由复活节算法得出，与官方日历一致）；
  2. 爬取柏林官方页面（berlin.de）已公布的 2026/2027 日期表核对：
     计算的 9 个全国性假日必须全部出现（柏林含这些全国假日）。

不含各州特有假日（如 1/6 三圣节仅巴符/拜仁/萨安等州、Fronleichnam、
Allerheiligen 等）——App 未提供州级选择前不纳入「德国」通用口径。

用法：python3 fetch_holiday_germany.py
输出：holiday-data-germany.json
"""

import re
from datetime import date, timedelta

import holiday_common as common

BERLIN_URL = (
    "https://www.berlin.de/tourismus/infos/"
    "1887651-1721039-feiertage-schulferien.html"
)

# 全国 9 天（与各州法律一致的法定规则）
def national_days(year: int) -> set[date]:
    easter = common.easter_sunday(year)
    days = {
        date(year, 1, 1),                                    # Neujahr
        easter - timedelta(days=2),                          # Karfreitag
        easter + timedelta(days=1),                          # Ostermontag
        date(year, 5, 1),                                    # Tag der Arbeit
        easter + timedelta(days=39),                         # Christi Himmelfahrt
        easter + timedelta(days=50),                         # Pfingstmontag
        date(year, 10, 3),                                   # Tag der Deutschen Einheit
        date(year, 12, 25),                                  # 1. Weihnachtstag
        date(year, 12, 26),                                  # 2. Weihnachtstag
    }
    return days


def parse_berlin_dates(html: str) -> dict[int, set[date]]:
    """解析柏林官方页：`dd.mm.yyyy (Weekday): Name` 行，按年分组。"""
    out: dict[int, set[date]] = {}
    pat = re.compile(
        r"(\d{2})\.(\d{2})\.(\d{4})\s*\([^)]*\)\s*:\s*([^<]+)"
    )
    for m in pat.finditer(html):
        day, month, year, _name = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        out.setdefault(year, set()).add(d)
    return out


def main() -> None:
    all_days: set[date] = set()
    official_years = set(common.TARGET_YEARS)
    for year in common.TARGET_YEARS:
        all_days |= national_days(year)

    # 官方页面核对（柏林公布 2026/2027；必须包含全部 9 个全国性假日）
    html = common.http_text(BERLIN_URL)
    checked_years: set[int] = set()
    if html is not None:
        berlin = parse_berlin_dates(html)
        for year in sorted(set(common.TARGET_YEARS) & set(berlin)):
            national = national_days(year)
            missing = national - berlin[year]
            if missing:
                raise SystemExit(
                    f"核对失败：柏林官方 {year} 页缺少全国性假日 "
                    + ", ".join(sorted(common.iso(d) for d in missing))
                )
            checked_years.add(year)
            print(f"✔ 柏林官方页面已核对 {year}：9 个全国性假日全部命中")
    else:
        print("  [WARN] 柏林官方页面抓取失败，跳过核对（数据仍按法定规则生成）",
              flush=True)

    note = (
        "口径：全德 16 州一致的 9 个全国性法定假日（Karfreitag 等复活节系"
        "假日按各州 Feiertagsgesetz 统一规则 + 复活节算法计算）。"
        "不含各州特有假日（1/6、Fronleichnam、Allerheiligen 等需州级选择）。"
        + (f"已与柏林官方页面核对年份：{sorted(checked_years)}。" if checked_years
           else "本次未完成官方页面核对。")
    )
    common.write_json(
        country="germany",
        country_name="德国",
        holidays=(common.iso(d) for d in all_days),
        official_years=official_years,
        source="各州 Sonn- und Feiertagsgesetz 统一法定口径 + Berlin.de 官方核对",
        source_urls=[BERLIN_URL],
        note=note,
    )


if __name__ == "__main__":
    main()
