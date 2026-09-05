#!/usr/bin/env python3
"""日本官方节假日爬虫 — 内閣府「国民の祝日について」CSV。

数据源（官方）：
  https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv

CSV 为 Shift-JIS，1955 年起，包含：
  - 国民の祝日（固定日 + 第 N 个星期一等）
  - 振替休日（周日祝日的顺延）
  - 国民の休日（夹在两个祝日之间的工作日）

官方公布到当年 +1 年（当前 CSV 到 2027）。未公布的年份（2028-2030）
按法定规则推算并标注为预测（不含在 officialYears）。

用法：python3 fetch_holiday_japan.py
输出：holiday-data-japan.json
"""

import csv
import io
import math
from datetime import date, datetime, timedelta

import holiday_common as common

CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"


# ---------- 春分 / 秋分（天文计算，用于预测未公布年份） ----------

def _solar_longitude_deg(jd: float) -> float:
    """太阳视黄经（J2000 简化式，与 App 端 CalendarView 算法一致）。"""
    t = jd - 2451545.0
    l_deg = 280.460 + 0.9856474 * t
    g_rad = math.radians(357.528 + 0.9856003 * t)
    lam = l_deg + 1.915 * math.sin(g_rad) + 0.020 * math.sin(2 * g_rad)
    lam %= 360.0
    if lam < 0:
        lam += 360.0
    return lam


def _julian_day(y: int, m: int, d: int) -> float:
    """UTC 0 点儒略日（公历）。"""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return (
        d + (153 * mm + 2) // 5 + 365 * yy + yy // 4
        - yy // 100 + yy // 400 - 32045
    )


def equinox_day(year: int, target_deg: float, month_guess: int) -> date:
    """返回日本标准时（UTC+9）当天春分/秋分日期（预测用）。

    按小时扫太阳黄经，找黄经跨过目标角的时刻（前后样本 v 变号），
    再换算成日本本地日历日。
    """
    def v_of(jd: float) -> float:
        lam = _solar_longitude_deg(jd)
        return (lam - target_deg + 540.0) % 360.0 - 180.0

    prev_v: float | None = None
    dim = 31 if month_guess in (3, 10, 12) else 30
    for day in range(1, dim + 1):
        for hour in range(24):
            jd = _julian_day(year, month_guess, day) + hour / 24.0
            v = v_of(jd)
            if prev_v is not None and prev_v < 0.0 <= v:
                # 交点在本小时与上一小时之间；取本小时 +9h 的 JST 日期
                jst_jd = jd + 9.0 / 24.0
                y2, m2, d2 = _jd_to_utc_date(jst_jd)
                return date(y2, m2, d2)
            prev_v = v
    raise ValueError(f"未找到 {year} 年黄经 {target_deg}° 交点")


def _jd_to_utc_date(jd: float) -> tuple[int, int, int]:
    """儒略日 → (年, 月, 日)（公历，UTC 日期）。"""
    z = int(jd + 0.5)
    f = jd + 0.5 - z
    a = z
    if z >= 2299161:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    if f < 0.0:
        day -= 1
    month = e - 1 if e < 14 else e - 13
    yy = c - 4716 if month > 2 else c - 4715
    return yy, month, day


# ---------- 预测（法定规则） ----------

def predict_base_days(year: int) -> set[date]:
    """按现行法律推算 2028-2030 基准祝日（春分/秋分为天文预测）。"""
    days: set[date] = {
        date(year, 1, 1),                     # 元日
        date(year, 2, 11),                    # 建国記念の日
        date(year, 2, 23),                    # 天皇誕生日
        date(year, 4, 29),                    # 昭和の日
        date(year, 5, 3),                     # 憲法記念日
        date(year, 5, 4),                     # みどりの日
        date(year, 5, 5),                     # こどもの日
        date(year, 8, 11),                    # 山の日
        date(year, 11, 3),                    # 文化の日
        date(year, 11, 23),                   # 勤労感謝の日
    }
    adult = common.nth_weekday(year, 1, 1, 2)      # 成人の日（第2月曜）
    marine = common.nth_weekday(year, 7, 1, 3)     # 海の日（第3月曜）
    aged = common.nth_weekday(year, 9, 1, 3)       # 敬老の日（第3月曜）
    sports = common.nth_weekday(year, 10, 1, 2)    # スポーツの日（第2月曜）
    for d in (adult, marine, aged, sports):
        if d is not None:
            days.add(d)
    days.add(equinox_day(year, 0.0, 3))   # 春分の日
    days.add(equinox_day(year, 180.0, 9)) # 秋分の日
    return days


def apply_holiday_rules(base: set[date], year: int) -> set[date]:
    """叠加振替休日与国民の休日（预测年份使用）。"""
    out = set(base)
    # 振替休日：祝日在周日 → 下一个非祝日工作日休息
    for d in sorted(base):
        if d.isoweekday() == 7:
            nxt = d + timedelta(days=1)
            while nxt in out:
                nxt += timedelta(days=1)
            out.add(nxt)
    # 国民の休日：前一日与次日都是祝日（且本身不是周日）→ 休息
    start, end = date(year, 1, 1), date(year, 12, 31)
    d = start
    while d <= end:
        if d.isoweekday() != 7 and d not in out:
            prev = d - timedelta(days=1)
            nxt = d + timedelta(days=1)
            if prev in out and nxt in out:
                out.add(d)
        d += timedelta(days=1)
    return out


# ---------- 主流程 ----------

def main() -> None:
    text = common.http_text(CSV_URL, encoding="shift_jis")
    if text is None:
        raise SystemExit("日本 CSV 抓取失败")
    reader = csv.reader(io.StringIO(text))
    rows = [(r[0].strip(), r[1].strip()) for r in reader if len(r) >= 2 and "/" in r[0]]

    official: set[date] = set()
    official_years: set[int] = set()
    for raw_date, _name in rows:
        y, m, d = (int(x) for x in raw_date.split("/"))
        day = date(y, m, d)
        if y in common.TARGET_YEARS:
            official.add(day)
            official_years.add(y)

    # 预测未公布年份（官方 CSV 之外）
    predicted: set[date] = set()
    for y in common.TARGET_YEARS:
        if y not in official_years:
            predicted |= apply_holiday_rules(predict_base_days(y), y)

    days = {common.iso(d) for d in official | predicted}
    note = (
        "数据源：内閣府「国民の祝日について」CSV（含振替休日/国民の休日）。"
        f"官方公布至 {max(official_years) if official_years else 0}；"
        "其后年份按现行法定规则推算（春分/秋分按天文预测），officialYears 不含预测年份。"
    )
    common.write_json(
        country="japan",
        country_name="日本",
        holidays=days,
        official_years=official_years,
        source="内閣府 国民の祝日について（公式 CSV）",
        source_urls=[CSV_URL],
        note=note,
    )


if __name__ == "__main__":
    main()
