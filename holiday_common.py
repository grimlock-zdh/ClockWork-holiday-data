#!/usr/bin/env python3
"""共享工具：HTTP 抓取、日期工具、统一 JSON 输出。

供各国官方数据爬虫使用（fetch_holiday_<country>.py），只依赖标准库。
输出 schema 与 App 端 CloudHolidayData 对齐：
{ "holidays": [...], "extra_workdays": [], "ranges": [], "metadata": {...} }
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List, Optional

# App 远程数据覆盖年份（HolidayService.remoteYears）
TARGET_YEARS = range(2024, 2031)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en,zh-CN;q=0.8,zh;q=0.6,ja;q=0.4,de;q=0.4,fr;q=0.4",
}


def http_bytes(url: str, timeout: int = 30) -> Optional[bytes]:
    """抓取 URL 原始字节；失败打印警告并返回 None。"""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:  # noqa: BLE001 - 爬虫需兼容各类网络错误
        print(f"  [WARN] 获取 {url} 失败: {e}", file=sys.stderr)
        return None


def http_text(url: str, encoding: str = "utf-8") -> Optional[str]:
    raw = http_bytes(url)
    if raw is None:
        return None
    return raw.decode(encoding, errors="replace")


def iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def easter_sunday(year: int) -> date:
    """复活节（Meeus/Jones/Butcher 算法，与 App/挂件端一致）。"""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def nth_weekday(year: int, month: int, weekday: int, ordinal: int) -> Optional[date]:
    """第 ordinal 个 weekday（1=周一..7=周日；ordinal<0 表示倒数）。"""
    if month < 1 or month > 12:
        return None
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    dim = (nxt - date(year, month, 1)).days
    days = [
        date(year, month, d)
        for d in range(1, dim + 1)
        if date(year, month, d).isoweekday() == weekday
    ]
    if not days:
        return None
    if ordinal > 0:
        return days[ordinal - 1] if len(days) >= ordinal else None
    idx = len(days) + ordinal
    return days[idx] if 0 <= idx < len(days) else None


def write_json(
    country: str,
    country_name: str,
    holidays: Iterable[str],
    official_years: Iterable[int],
    source: str,
    source_urls: List[str],
    note: str,
) -> None:
    """按统一 schema 写 holiday-data-<country>.json。"""
    years = sorted(TARGET_YEARS)
    data = {
        "holidays": sorted(set(holidays)),
        "extra_workdays": [],
        "ranges": [],
        "metadata": {
            "country": country,
            "countryName": country_name,
            "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "years": [years[0], years[-1]],
            "officialYears": sorted(set(official_years) & set(years)),
            "source": source,
            "sourceUrls": source_urls,
            "note": note,
        },
    }
    path = f"holiday-data-{country}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"✔ 已生成 {path}（{len(data['holidays'])} 天，"
          f"官方年份 {data['metadata']['officialYears']}）")


def add_days(d: date, delta: int) -> date:
    from datetime import timedelta
    return d + timedelta(days=delta)


def year_of(s: str) -> int:
    return int(s[:4])


def filter_years(days: Iterable[str]) -> List[str]:
    return sorted(d for d in days if year_of(d) in TARGET_YEARS)
