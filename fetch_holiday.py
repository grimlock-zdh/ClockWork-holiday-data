#!/usr/bin/env python3
"""
国务院放假通知爬虫 — 自动抓取并解析为 holiday-data-china.json

原理：
1. 通过 Bing 搜索找到 gov.cn 上的放假通知
2. 提取纯文本内容，用正则解析出：
   - 假期名称、起止日期
   - 调休补班日
3. 输出 holiday-data-china.json（与 App 端格式一致）

使用：python3 fetch_holiday.py
输出：holiday-data-china.json（直接写入当前目录）
"""

import json
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import date, timedelta
from typing import Optional

# ============================================================
# 配置
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# Bing 搜索 URL 模板
BING_SEARCH_URL = (
    "https://www.bing.com/search?q={query}&setlang=zh-Hans"
)

# 已知的放假通知文章号（Fallback，当 Bing 搜索失败时直接尝试）
# 每年约 10~11 月发布，URL 模式为 /zhengce/content/{YYYY}{MM}/content_{数字}.htm
# 数字是递增的，这个表用来兜底
KNOWN_ARTICLE_PATHS = {
    2024: "202310/content_6914152.htm",
    2025: "202410/content_6973123.htm",
    2026: "202511/content_7047090.htm",
}

# 月份名称 -> 数字
MONTH_MAP = {
    "1": 1, "01": 1, "一": 1, "元": 1,
    "2": 2, "02": 2, "二": 2,
    "3": 3, "03": 3, "三": 3,
    "4": 4, "04": 4, "四": 4,
    "5": 5, "05": 5, "五": 5,
    "6": 6, "06": 6, "六": 6,
    "7": 7, "07": 7, "七": 7,
    "8": 8, "08": 8, "八": 8,
    "9": 9, "09": 9, "九": 9,
    "10": 10, "十": 10,
    "11": 11, "十一": 11,
    "12": 12, "十二": 12,
}

# 星期映射（仅为验证）
WEEKDAY_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}


# ============================================================
# 工具函数
# ============================================================

def fetch_page(url: str) -> Optional[str]:
    """获取网页内容"""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] 获取 {url} 失败: {e}", file=sys.stderr)
        return None


def extract_text_from_html(html: str) -> str:
    """提取 HTML 中的纯文本（去掉标签）"""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-z]+;', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def find_article_url(year: int) -> Optional[str]:
    """通过 Bing 搜索找到对应年份的放假通知 URL"""
    query = urllib.parse.quote(f"{year}年放假安排 site:gov.cn")
    url = BING_SEARCH_URL.format(query=query)
    html = fetch_page(url)
    if not html:
        return None

    # 找到所有 gov.cn 的链接
    links = re.findall(r'https?://[^"\'<>]*gov\.cn[^"\'<>]*', html)
    
    for link in links:
        # 排除不相关的
        if any(x in link for x in ["beian", "miit", "big5", "search", "javascript"]):
            continue
        # 优先选择 content 路径的
        if f"/zhengce/content/{year}" in link or f"/zhengce/zhengceku/{year}" in link:
            # 验证页面标题是否包含放假
            page_html = fetch_page(link)
            if page_html and "节假日安排" in page_html:
                return link
    
    return None


def find_article_url_direct(year: int) -> Optional[str]:
    """直接尝试已知 URL 模式"""
    base_patterns = [
        f"https://www.gov.cn/zhengce/content/{year}11/content_7047090.htm",  # 2026
        f"https://www.gov.cn/zhengce/content/{year}10/content_6973123.htm",  # 2025?
    ]
    for url in base_patterns:
        html = fetch_page(url)
        if html and "节假日安排" in html:
            return url
    return None


def parse_holiday_text(text: str, year: int) -> dict:
    """
    从纯文本中解析放假安排
    
    输入: "一、元旦：1月1日（周四）至3日（周六）放假调休，共3天。1月4日（周日）上班。"
    输出: {"name": "元旦", "range_dates": [date, date, date], "extra_workdays": [date]}
    """
    results = {
        "holidays": [],       # [date strings]
        "extra_workdays": [],  # [date strings]
        "ranges": [],          # [{name, start, end}]
    }
    
    # 节假日名称列表
    holiday_names = ["元旦", "春节", "清明节", "劳动节", "端午节", "中秋节", "国庆节"]
    
    # 分割段落（按 "一、二、三、" 或 "一． 二．"）
    # 先把 "1月4日（周日）上班" 这类补班句统一处理
    
    # 第一步：提取所有调休补班日
    # 补班句式："X月X日（周X）上班" 或 "X月X日、X月X日（周X）上班"
    # 注意排除 "X月X日（农历X、周X）" 中的日期（那是春节放假开始日）
    
    # 先找出所有放假日期（用于排除误匹配）
    holiday_date_strs = set()
    
    # 再提取上班句式
    # 句式1: "1月4日（周日）上班"
    # 句式2: "2月14日（周六）、2月28日（周六）上班"
    # 句式3: "9月20日（周日）、10月10日（周六）上班"
    
    # 用更精确的模式：先按句号分词，找包含"上班"的句子
    sentences = re.split(r'[。；]', text)
    for sent in sentences:
        if '上班' not in sent:
            continue
        # 提取所有 "X月X日" 模式，排除包含 "农历" 的（那是春节放假日期不是补班）
        if '农历' in sent:
            # 春节的放假日期里有农历日期，需要排除
            # 如 "2月15日（农历腊月二十八、周日）至23日（农历正月初七、周一）"
            # 其中的 "2月15日" 和 "23日" 是放假不是补班
            continue
        dates = re.findall(r'(\d+)月(\d+)日', sent)
        for month_str, day_str in dates:
            m, d = int(month_str), int(day_str)
            results["extra_workdays"].append(f"{year}-{m:02d}-{d:02d}")
    
    # 第二步：解析每个节假日的段落
    for name in holiday_names:
        # 查找该节假日的描述文字
        # 匹配示例:
        #   "一、元旦： 1月1日（周四）至3日（周六）放假调休，共3天。"
        #   "二、春节： 2月15日（农历腊月二十八、周日）至23日（农历正月初七、周一）放假调休，共9天。"
        #   "三、清明节： 4月4日（周六）至6日（周一）放假，共3天。"
        #   "四、劳动节： 5月1日（周五）至5日（周二）放假调休，共5天。"
        
        # 模式1: "{name}： XX月XX日（...）至[XX月]XX日（...）放假"
        pat1 = rf'{name}[:：]\s*(\d+)月(\d+)日[^至]*?至\s*(?:(\d+)月)?(\d+)日'
        # 模式2: "{name}： XX月XX日放假"（单日）
        pat2 = rf'{name}[:：]\s*(\d+)月(\d+)日[^。]*?(?:放|假)'
        
        match = re.search(pat1, text)
        if match:
            groups = match.groups()
            start_m = int(groups[0])
            start_d = int(groups[1])
            end_m = int(groups[2]) if groups[2] else start_m
            end_d = int(groups[3])
        else:
            match = re.search(pat2, text)
            if match:
                start_m = int(match.group(1))
                start_d = int(match.group(2))
                end_m = start_m
                end_d = start_d
            else:
                print(f"  [WARN] 未找到 {name} 的放假日期", file=sys.stderr)
                continue
        
        start_date = date(year, start_m, start_d)
        end_date = date(year, end_m, end_d)
        
        range_dates = []
        d = start_date
        while d <= end_date:
            range_dates.append(d)
            d += timedelta(days=1)
        
        for dt in range_dates:
            results["holidays"].append(dt.strftime("%Y-%m-%d"))
        
        results["ranges"].append({
            "name": name,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        })
        
        print(f"  [OK] {name}: {start_date} ~ {end_date}", file=sys.stderr)
    
    return results


# ============================================================
# 主流程
# ============================================================

def fetch_holiday_data(year: int) -> Optional[dict]:
    """获取指定年份的放假数据"""
    print(f"[INFO] 正在获取 {year} 年放假安排...", file=sys.stderr)
    
    # 1. 找文章 URL
    article_url = find_article_url(year)
    if not article_url:
        print(f"  [INFO] Bing 搜索未找到，尝试直接 URL...", file=sys.stderr)
        article_url = find_article_url_direct(year)
    
    if not article_url:
        print(f"  [ERROR] 无法找到 {year} 年放假通知 URL", file=sys.stderr)
        # 尝试已知 URL
        if year in KNOWN_ARTICLE_PATHS:
            article_url = f"https://www.gov.cn/zhengce/content/{KNOWN_ARTICLE_PATHS[year]}"
            print(f"  [INFO] 尝试已知 URL: {article_url}", file=sys.stderr)
            html_check = fetch_page(article_url)
            if not html_check or "节假日安排" not in html_check:
                article_url = None
        # 如果已知 URL 也失效，尝试猜测模式
        # 当年 10~11 月发布的，content_ 后面的数字每年递增大约 5-15 万
        if not article_url:
            # 以 2026 年为基准向前/向后尝试
            base_path = KNOWN_ARTICLE_PATHS.get(year - 1) or KNOWN_ARTICLE_PATHS.get(year + 1)
            if base_path:
                # 提取年月和数字
                m = re.match(r'(\d{6})/content_(\d+)\.htm', base_path)
                if m:
                    base_ym = m.group(1)
                    base_num = int(m.group(2))
                    # 尝试偏移
                    offsets = [0, 5000, 10000, -5000, -10000, 20000, 30000]
                    target_ym = f"{year}11"
                    for offset in offsets:
                        guess_num = base_num + offset
                        guess_url = f"https://www.gov.cn/zhengce/content/{target_ym}/content_{guess_num}.htm"
                        html_check = fetch_page(guess_url)
                        if html_check and "节假日安排" in html_check:
                            article_url = guess_url
                            print(f"  [OK] 猜测成功: {article_url}", file=sys.stderr)
                            break
    
    if not article_url:
        return None
    
    print(f"  [OK] URL: {article_url}", file=sys.stderr)
    
    # 2. 获取页面内容
    html = fetch_page(article_url)
    if not html:
        return None
    
    # 3. 提取文本
    text = extract_text_from_html(html)
    
    # 调试：打印提取的文本
    print(f"  [INFO] 提取文本 ({len(text)} chars)", file=sys.stderr)
    
    # 4. 解析
    data = parse_holiday_text(text, year)
    
    print(f"  [OK] 节假日: {len(data['holidays'])} 天, 补班: {len(data['extra_workdays'])} 天", file=sys.stderr)
    for r in data["ranges"]:
        print(f"    {r['name']}: {r['start']} ~ {r['end']}", file=sys.stderr)
    if data["extra_workdays"]:
        print(f"    补班: {', '.join(data['extra_workdays'])}", file=sys.stderr)
    
    return data


def merge_with_existing(existing: dict, new_data: dict, year: int) -> dict:
    """合并新数据到已有 JSON"""
    # 对于指定年份，完全覆盖
    # 移除已有年份的旧数据
    existing["holidays"] = [h for h in existing["holidays"] if not h.startswith(f"{year}-")]
    existing["extra_workdays"] = [w for w in existing["extra_workdays"] if not w.startswith(f"{year}-")]
    existing["ranges"] = [r for r in existing["ranges"] if not r["start"].startswith(f"{year}-")]
    
    # 添加新数据
    existing["holidays"].extend(new_data["holidays"])
    existing["extra_workdays"].extend(new_data["extra_workdays"])
    existing["ranges"].extend(new_data["ranges"])
    
    # 去重排序
    existing["holidays"] = sorted(set(existing["holidays"]))
    existing["extra_workdays"] = sorted(set(existing["extra_workdays"]))
    existing["ranges"] = sorted(existing["ranges"], key=lambda r: r["start"])
    
    return existing


def main():
    existing = {
        "holidays": [],
        "extra_workdays": [],
        "ranges": []
    }
    
    try:
        with open("holiday-data-china.json", "r") as f:
            existing = json.load(f)
        print(f"[INFO] 读取已有数据: {len(existing['holidays'])} 假日, {len(existing['extra_workdays'])} 补班", file=sys.stderr)
    except FileNotFoundError:
        print(f"[INFO] 新建数据文件", file=sys.stderr)
    
    current_year = date.today().year
    years_to_fetch = [current_year - 1, current_year, current_year + 1, current_year + 2]
    
    for year in years_to_fetch:
        data = fetch_holiday_data(year)
        if data and (data["holidays"] or data["extra_workdays"]):
            existing = merge_with_existing(existing, data, year)
    
    output = json.dumps(existing, ensure_ascii=False, indent=2)
    with open("holiday-data-china.json", "w") as f:
        f.write(output)
    
    print(f"\n[OK] 已写入 holiday-data-china.json ({len(existing['holidays'])} 假日, {len(existing['extra_workdays'])} 补班)", file=sys.stderr)


if __name__ == "__main__":
    main()
