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

# GOV.UK 标题 → (中文名, 英文名)
UK_NAMES: dict[str, tuple[str, str]] = {
    "New Year's Day": ("新年", "New Year's Day"),
    "Good Friday": ("耶稣受难日", "Good Friday"),
    "Easter Monday": ("复活节星期一", "Easter Monday"),
    "Early May bank holiday": ("五月假日", "Early May Bank Holiday"),
    "Spring bank holiday": ("春季假日", "Spring Bank Holiday"),
    "Summer bank holiday": ("夏季假日", "Summer Bank Holiday"),
    "Christmas Day": ("圣诞节", "Christmas Day"),
    "Boxing Day": ("节礼日", "Boxing Day"),
}


def uk_name(title: str) -> tuple[str, str]:
    """按 GOV.UK 标题取中英文；未收录的一次性假日回退英文名。"""
    key = title.strip().replace("’", "'")
    if key in UK_NAMES:
        return UK_NAMES[key]
    print(f"  [WARN] 未知英国假日: {key}，使用英文回退", flush=True)
    return (key, key)


def last_monday(year: int, month: int) -> date:
    return common.nth_weekday(year, month, 1, -1)  # type: ignore[return-value]


def predict_year(year: int) -> dict[date, tuple[str, str]]:
    """2029-2030 预测：法定规则（Easter 由算法计算），返回日期 → 中英文名。"""
    days: dict[date, tuple[str, str]] = {}
    easter = common.easter_sunday(year)
    # New Year's Day：周末顺延到下个周一
    ny = date(year, 1, 1)
    if ny.isoweekday() <= 5:
        days[ny] = uk_name("New Year's Day")
    else:
        days[ny + timedelta(days=(8 - ny.isoweekday()))] = uk_name("New Year's Day")
    days[easter - timedelta(days=2)] = uk_name("Good Friday")
    days[easter + timedelta(days=1)] = uk_name("Easter Monday")
    days[common.nth_weekday(year, 5, 1, 1)] = uk_name("Early May bank holiday")
    days[last_monday(year, 5)] = uk_name("Spring bank holiday")
    days[last_monday(year, 8)] = uk_name("Summer bank holiday")
    # Christmas / Boxing Day（含周末顺延：优先平日实际假日，再按顺序补顺延）
    dec25 = date(year, 12, 25)
    dec26 = date(year, 12, 26)
    pending: list[tuple[date, str]] = []
    for d in (dec25, dec26):
        if d.isoweekday() <= 5:
            name = uk_name("Christmas Day" if d == dec25 else "Boxing Day")
            days[d] = name
        else:
            pending.append((d, "Christmas Day" if d == dec25 else "Boxing Day"))
    for d, title in pending:
        nxt = d + timedelta(days=1)
        while nxt in days or nxt.isoweekday() == 7:
            nxt += timedelta(days=1)
        days[nxt] = uk_name(title)
    return {d: n for d, n in days.items() if d.year == year}


def main() -> None:
    raw = common.http_text(API_URL)
    if raw is None:
        raise SystemExit("GOV.UK JSON 抓取失败")
    payload = json.loads(raw)
    events = payload[REGION]["events"]

    official: dict[date, tuple[str, str]] = {}
    official_years: set[int] = set()
    for ev in events:
        try:
            d = date.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            continue
        if d.year in common.TARGET_YEARS:
            official[d] = uk_name(ev.get("title", ""))
            official_years.add(d.year)

    predicted: dict[date, tuple[str, str]] = {}
    for year in common.TARGET_YEARS:
        if year not in official_years:
            predicted |= predict_year(year)

    combined: dict[date, tuple[str, str]] = dict(official)
    combined.update(predicted)
    days = {common.iso(d) for d in combined}
    holiday_names = {
        common.iso(d): {"zh": zh, "en": en}
        for d, (zh, en) in combined.items()
    }
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
        holidays=days,
        official_years=official_years,
        source="GOV.UK Bank Holidays API（HM Government）",
        source_urls=[API_URL],
        note=note,
        holiday_names=holiday_names,
    )


if __name__ == "__main__":
    main()
