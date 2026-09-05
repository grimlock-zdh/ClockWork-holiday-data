#!/usr/bin/env python3
"""英国官方银行假日爬虫 — GOV.UK Bank Holidays JSON API。

数据源（官方）：
  https://www.gov.uk/bank-holidays.json
  （文档：https://www.api.gov.uk/gds/bank-holidays/）

采用 England and Wales 分区（苏格兰/北爱尔兰另有当地假日；
App 当前只提供「英国」单一口径，默认英格兰+威尔士）。
JSON 官方公布到 2028；2029-2030 按法定规则推算并标注为预测。

用法：python3 fetch_holiday_uk.py
输出：holiday-data-uk.json
"""

import json
from datetime import date, timedelta

import holiday_common as common

API_URL = "https://www.gov.uk/bank-holidays.json"
REGION = "england-and-wales"


def last_monday(year: int, month: int) -> date:
    return common.nth_weekday(year, month, 1, -1)  # type: ignore[return-value]


def predict_year(year: int) -> set[date]:
    """2029-2030 预测：法定规则（Easter 由算法计算）。"""
    days: set[date] = set()
    easter = common.easter_sunday(year)
    # New Year's Day：周末顺延到下个周一
    ny = date(year, 1, 1)
    if ny.isoweekday() <= 5:
        days.add(ny)
    else:
        days.add(ny + timedelta(days=(8 - ny.isoweekday())))
    days.add(easter - timedelta(days=2))      # Good Friday
    days.add(easter + timedelta(days=1))      # Easter Monday
    days.add(common.nth_weekday(year, 5, 1, 1))   # Early May BH
    days.add(last_monday(year, 5))                 # Spring BH
    days.add(last_monday(year, 8))                 # Summer BH
    # Christmas / Boxing Day（含周末顺延：优先平日实际假日，再按顺序补顺延）
    dec25 = date(year, 12, 25)
    dec26 = date(year, 12, 26)
    pending: list[date] = []
    for d in (dec25, dec26):
        if d.isoweekday() <= 5:
            days.add(d)
        else:
            pending.append(d)
    for d in pending:
        nxt = d + timedelta(days=1)
        while nxt in days or nxt.isoweekday() == 7:
            nxt += timedelta(days=1)
        days.add(nxt)
    return {d for d in days if d.year == year}


def main() -> None:
    raw = common.http_text(API_URL)
    if raw is None:
        raise SystemExit("GOV.UK JSON 抓取失败")
    payload = json.loads(raw)
    events = payload[REGION]["events"]

    official: set[date] = set()
    official_years: set[int] = set()
    for ev in events:
        try:
            d = date.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            continue
        if d.year in common.TARGET_YEARS:
            official.add(d)
            official_years.add(d.year)

    predicted: set[date] = set()
    for year in common.TARGET_YEARS:
        if year not in official_years:
            predicted |= predict_year(year)

    note = (
        "数据源：GOV.UK Bank Holidays 官方 JSON（England and Wales）。"
        "官方公布至 "
        f"{max(official_years) if official_years else 0}；"
        "其后按法定规则推算（Easter 算法），officialYears 不含预测年份。"
        "苏格兰/北爱尔兰另有当地假日，需分区支持时另行扩展。"
    )
    common.write_json(
        country="uk",
        country_name="英国",
        holidays=(common.iso(d) for d in official | predicted),
        official_years=official_years,
        source="GOV.UK Bank Holidays API（HM Government）",
        source_urls=[API_URL],
        note=note,
    )


if __name__ == "__main__":
    main()
