#!/usr/bin/env python3
"""印度官方节假日爬虫 — DoPT（人事与培训部）中央政府在德里放假名单。

口径：印度节假日由各邦立法/通知决定，没有单一“全国法定假日”官方列表；
本文件采用**中央政府行政办公室（Delhi/New Delhi）名单**（DoPT 每年 7 月
Office Memorandum 公布，含共和国日等固定假日与按印度历/回历公布的节日），
作为 App「印度」通用口径（类似英国取英格兰+威尔士、德国取全德 9 天）。

官方原始文件是**扫描版 PDF**（documents.doptcirculars.nic.in，无文本层），
无法仅用标准库可靠抽取。因此脚本内嵌经官方 OM 文本逐条核对的日期表
（每条 = (日期, 英文名, 中文名)；sourceUrls/OM 号见下方 OFFICIAL_YEARS），
每次运行：
  1. 尝试连通官方 PDF 服务器（可访问时打印校验信息）；
  2. 用内嵌官方表生成 holiday-data-india.json（含 holiday_names 中英文名）；
  3. 逐年断言：固定假日必须存在、数量 >= 16、日期均落在当年。

DoPT 每年 7 月公布次年名单；公布后需把新一年加入 OFFICIAL_YEARS
（每行日期带官方英文名 + 中文翻译），脚本即可覆盖新年度。

用法：python3 fetch_holiday_india.py
输出：holiday-data-india.json
"""

import urllib.request

import holiday_common as common


def _pdf_reachable(url: str, timeout: int = 8) -> bool:
    """仅探测官方 PDF 是否可达（HEAD），不下载扫描件全文。"""
    req = urllib.request.Request(url, method="HEAD", headers=common.HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001 - 探测失败不阻断生成
        return False


# 每年官方名单（DoPT OM Annexure-I，Delhi/New Delhi 行政办公室）
# 格式：年份 -> (OM 日期文本, 官方文件 URL, [(日期, 英文名, 中文名), ...])
OFFICIAL_YEARS: dict[int, tuple[str, str, list[tuple[str, str, str]]]] = {
    2024: (
        "DoPT O.M. F.No.12/2/2023-JCA dated 03.07.2023",
        "https://documents.doptcirculars.nic.in/D2/D02est/Holiday%20to%20be%20observed%20in%20Central%20government%20offices%20during%20the%20year%202024kFtwz.PDF",
        [
            ("2024-01-26", "Republic Day", "共和国日"),
            ("2024-03-25", "Holi", "洒红节"),
            ("2024-03-29", "Good Friday", "耶稣受难日"),
            ("2024-04-11", "Id-ul-Fitr", "开斋节"),
            ("2024-04-17", "Ram Navami", "罗摩诞辰"),
            ("2024-04-21", "Mahavir Jayanti", "大雄节"),
            ("2024-05-23", "Buddha Purnima", "佛诞节"),
            ("2024-06-17", "Id-ul-Zuha (Bakrid)", "宰牲节"),
            ("2024-07-17", "Muharram", "穆哈兰姆节"),
            ("2024-08-15", "Independence Day", "独立日"),
            ("2024-08-26", "Janmashtami (Vaishnava)", "黑天诞辰节"),
            ("2024-09-16", "Milad-un-Nabi / Id-e-Milad", "圣纪节"),
            ("2024-10-02", "Mahatma Gandhi's Birthday", "甘地诞辰"),
            ("2024-10-12", "Dussehra", "十胜节"),
            ("2024-10-31", "Diwali (Deepavali)", "排灯节"),
            ("2024-11-15", "Guru Nanak's Birthday", "那纳克祖师诞辰"),
            ("2024-12-25", "Christmas Day", "圣诞节"),
        ],
    ),
    2025: (
        "DoPT O.M. F.No.12/2/2023-JCA dated 09.07.2024",
        "https://documents.doptcirculars.nic.in/D2/D02est/List%20of%20holidays%202025KtKLw.pdf",
        [
            ("2025-01-26", "Republic Day", "共和国日"),
            ("2025-02-26", "Maha Shivaratri", "大湿婆夜节"),
            ("2025-03-14", "Holi", "洒红节"),
            ("2025-03-31", "Id-ul-Fitr", "开斋节"),
            ("2025-04-10", "Mahavir Jayanti", "大雄节"),
            ("2025-04-18", "Good Friday", "耶稣受难日"),
            ("2025-05-12", "Buddha Purnima / Ram Navami", "佛诞节 / 罗摩诞辰"),
            ("2025-06-07", "Id-ul-Zuha (Bakrid)", "宰牲节"),
            ("2025-07-06", "Muharram", "穆哈兰姆节"),
            ("2025-08-15", "Independence Day", "独立日"),
            ("2025-08-16", "Janmashtami", "黑天诞辰节"),
            ("2025-09-05", "Milad-un-Nabi / Id-e-Milad", "圣纪节"),
            ("2025-10-02", "Mahatma Gandhi's Birthday + Dussehra", "甘地诞辰 / 十胜节"),
            ("2025-10-20", "Diwali (Deepavali)", "排灯节"),
            ("2025-11-05", "Guru Nanak's Birthday", "那纳克祖师诞辰"),
            ("2025-12-25", "Christmas Day", "圣诞节"),
        ],
    ),
    2026: (
        "DoPT O.M. F.No.12/2/2023-JCA dated 03.07.2025；"
        "Bakrid 日期按 PIB 2026-05-21 修订为 05-28",
        "https://documents.doptcirculars.nic.in/D2/D02est/Holidays%20to%20be%20observed%20in%20Central%20Government%20Offices%20during%20the%20year%2020265vgBs.pdf",
        [
            ("2026-01-26", "Republic Day", "共和国日"),
            ("2026-03-04", "Holi", "洒红节"),
            ("2026-03-21", "Id-ul-Fitr", "开斋节"),
            ("2026-03-26", "Ram Navami", "罗摩诞辰"),
            ("2026-03-31", "Mahavir Jayanti", "大雄节"),
            ("2026-04-03", "Good Friday", "耶稣受难日"),
            ("2026-05-01", "Buddha Purnima", "佛诞节"),
            ("2026-05-28", "Id-ul-Zuha (Bakrid) — PIB revised", "宰牲节"),
            ("2026-06-26", "Muharram", "穆哈兰姆节"),
            ("2026-08-15", "Independence Day", "独立日"),
            ("2026-08-26", "Milad-un-Nabi / Id-e-Milad", "圣纪节"),
            ("2026-09-04", "Janmashtami (Vaishnava)", "黑天诞辰节"),
            ("2026-10-02", "Mahatma Gandhi's Birthday", "甘地诞辰"),
            ("2026-10-20", "Dussehra", "十胜节"),
            ("2026-11-08", "Diwali (Deepavali)", "排灯节"),
            ("2026-11-24", "Guru Nanak's Birthday", "那纳克祖师诞辰"),
            ("2026-12-25", "Christmas Day", "圣诞节"),
        ],
    ),
    2027: (
        "DoPT O.M. F.No.12/2/2023-JCA dated 16.07.2026",
        "https://dopt.gov.in/sites/default/files/List%20of%20Holidays%20for%20the%20Year%202027.pdf",
        [
            ("2027-01-26", "Republic Day", "共和国日"),
            ("2027-03-10", "Id-ul-Fitr", "开斋节"),
            ("2027-03-23", "Holi", "洒红节"),
            ("2027-03-26", "Good Friday", "耶稣受难日"),
            ("2027-04-15", "Ram Navami", "罗摩诞辰"),
            ("2027-04-19", "Mahavir Jayanti", "大雄节"),
            ("2027-05-17", "Id-ul-Zuha (Bakrid)", "宰牲节"),
            ("2027-05-20", "Buddha Purnima", "佛诞节"),
            ("2027-06-16", "Muharram", "穆哈兰姆节"),
            ("2027-08-15", "Independence Day + Milad-un-Nabi", "独立日 / 圣纪节"),
            ("2027-08-25", "Janmashtami (Vaishnava)", "黑天诞辰节"),
            ("2027-10-02", "Mahatma Gandhi's Birthday", "甘地诞辰"),
            ("2027-10-09", "Dussehra (Vijaya Dashmi)", "十胜节"),
            ("2027-10-29", "Diwali (Deepavali)", "排灯节"),
            ("2027-11-14", "Guru Nanak's Birthday", "那纳克祖师诞辰"),
            ("2027-12-25", "Christmas Day", "圣诞节"),
        ],
    ),
}


def validate_year(year: int, records: list[tuple[str, str, str]]) -> None:
    prefix = f"{year}-"
    days = [r[0] for r in records]
    assert all(d.startswith(prefix) for d in days), f"{year} 存在跨年日期"
    unique = set(days)
    assert len(unique) >= 16, f"{year} 名单过短（{len(unique)} 天）"
    for fixed in (f"{year}-01-26", f"{year}-08-15", f"{year}-10-02", f"{year}-12-25"):
        assert fixed in unique, f"{year} 缺少全国固定假日 {fixed}"
    assert all(r[1].strip() and r[2].strip() for r in records), \
        f"{year} 存在缺英文/中文名的记录"


def main() -> None:
    all_days: list[str] = []
    holiday_names: dict[str, dict[str, str]] = {}
    for year in common.TARGET_YEARS:
        if year not in OFFICIAL_YEARS:
            continue  # 官方尚未公布（DoPT 每年 7 月公布次年）；App 用固定假日规则兜底
        _om, url, records = OFFICIAL_YEARS[year]
        validate_year(year, records)
        for day, en, zh in records:
            all_days.append(day)
            holiday_names[day] = {"en": en, "zh": zh}
        # 尝试连通官方文件服务器（不依赖 OCR，仅校验源可用性）
        if _pdf_reachable(url):
            print(f"✔ {year} 官方 PDF 可访问（扫描件，日期表来自 OM 文本核对）")
        else:
            print(f"  [WARN] {year} 官方 PDF 暂不可达，使用已核对的 OM 日期表")

    note = (
        "口径：DoPT 中央政府在 Delhi/New Delhi 行政办公室的带薪假日名单"
        "（含共和国日/独立日/甘地诞辰等固定假日与按历法公布的宗教节日）。"
        "印度各邦另有本地假日，未包含。官方文件为扫描版 PDF，日期表按官方 "
        "OM 文本逐条核对（2026 Bakrid 按 PIB 修订为 05-28）；"
        "holiday_names 的中文名为翻译，供 App 展示，官方仅提供英文名。"
        f"当前官方公布至 {max(OFFICIAL_YEARS)}；其后年份待 DoPT 公布后补充，"
        "App 端先以固定全国假日规则兜底。"
    )
    common.write_json(
        country="india",
        country_name="印度",
        holidays=all_days,
        official_years=sorted(OFFICIAL_YEARS.keys()),
        source="DoPT（印度人事与培训部）中央政府在德里放假名单（Office Memorandum）",
        source_urls=[v[1] for v in OFFICIAL_YEARS.values()],
        note=note,
        holiday_names=holiday_names,
    )


if __name__ == "__main__":
    main()
