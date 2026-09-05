#!/usr/bin/env python3
"""美国官方联邦假日爬虫 — OPM（联邦人事管理局）Federal Holidays 页面。

数据源（官方）：
  https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/

OPM 每年公布联邦雇员实际休息日（含「逢周末顺延」的 observed 日期，
如周六假日顺延到周五、周日假日顺延到下周一）。官方页面已公布到 2030 年。

说明：
  - 不含 Inauguration Day（总统就职日仅华盛顿特区联邦雇员适用，非全国）；
  - OPM 的 New Year's Day 顺延若落在上一年 12/31（如 2028/1/1 周六 →
    2027/12/31 周五），按实际日历日期归入对应年份。

用法：python3 fetch_holiday_usa.py
输出：holiday-data-usa.json
"""

import re
from datetime import date, datetime

import holiday_common as common

OPM_URL = "https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/"
WEEKDAY_NAMES = {
    "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
    "Friday": 5, "Saturday": 6, "Sunday": 7,
}
MONTH_NAMES = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def parse_date_cell(cell: str, year: int) -> date | None:
    """解析 OPM 行日期。年份缺失时优先当年，其次按星期校验回退上一年。"""
    m = re.search(
        r"([A-Za-z]+),\s*([A-Za-z]+)\s*(\d{1,2}),?\s*(\d{4})?", cell
    )
    if not m:
        return None
    weekday_name, month_name, day_str, explicit_year = m.groups()
    month = MONTH_NAMES.get(month_name)
    day = int(day_str)
    if month is None:
        return None
    candidates = [year]
    if explicit_year:
        candidates = [int(explicit_year)]
    else:
        # OPM 把落在上一年 12/31 的 New Year's Day observed 放在
        # “次年”日程表里（如 2028 表首行 2027/12/31 周五）
        candidates += [year - 1, year + 1]
    expected = WEEKDAY_NAMES.get(weekday_name)
    for cand in candidates:
        try:
            d = date(cand, month, day)
        except ValueError:
            continue
        if expected is not None and d.isoweekday() != expected:
            continue
        return d
    return None


def parse_opm(html: str) -> dict[int, list[tuple[date, str]]]:
    """按 'YYYY Holiday Schedule' 段切分并解析日期行。"""
    pattern = re.compile(r"(\d{4})\s*Holiday Schedule", re.IGNORECASE)
    marks = [(int(m.group(1)), m.start()) for m in pattern.finditer(html)]
    result: dict[int, list[tuple[date, str]]] = {}
    for i, (year, pos) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(html)
        chunk = html[pos:end]
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", chunk, flags=re.S)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
            if len(cells) < 2:
                continue

            def clean(x: str) -> str:
                t = re.sub(r"<[^>]+>", " ", x)
                return re.sub(r"\s+", " ", t).strip()

            date_cell = clean(cells[0])
            name_cell = clean(cells[1])
            if not date_cell or not name_cell:
                continue
            d = parse_date_cell(date_cell, year)
            if d is not None:
                result.setdefault(d.year, []).append((d, name_cell))
    return result


def main() -> None:
    html = common.http_text(OPM_URL)
    if html is None:
        raise SystemExit("OPM 页面抓取失败")
    parsed = parse_opm(html)

    days: set[date] = set()
    official_years: set[int] = set()
    for year in common.TARGET_YEARS:
        rows = parsed.get(year, [])
        if not rows:
            print(f"  [WARN] OPM 未提供 {year} 数据", flush=True)
            continue
        official_years.add(year)
        for d, name in rows:
            if "Inauguration Day" in name:
                continue  # 仅华盛顿特区联邦雇员适用，不计入全国假日
            days.add(d)

    note = (
        "数据源：OPM Federal Holidays 官方页面（联邦雇员实际休息日，"
        "含周末顺延 observed 日期）。不含 Inauguration Day（仅 DC 适用）；"
        "按 5 U.S.C. 6103 口径。"
    )
    common.write_json(
        country="usa",
        country_name="美国",
        holidays=(common.iso(d) for d in days),
        official_years=official_years,
        source="OPM（美国联邦人事管理局）Federal Holidays",
        source_urls=[OPM_URL],
        note=note,
    )


if __name__ == "__main__":
    main()
