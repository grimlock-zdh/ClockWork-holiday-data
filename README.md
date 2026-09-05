# ClockWork-holiday-data

发条 ClockWork 的法定节假日数据仓库（公开）。每个国家一份
`holiday-data-<country>.json`（country = china / japan / usa / uk /
france / germany），统一 schema：

```json
{ "holidays": [...], "extra_workdays": [], "ranges": [], "metadata": {...} }
```

- `holidays`：休息日日期（YYYY-MM-DD）
- `extra_workdays`：补班日（目前只有中国有）
- `ranges`：中国放假区间（名称/起止；其它国家为空）
- `metadata.officialYears`：官方公布/官方口径核对的年份

## 数据源（各国官方口径）

| 国家 | 数据源 | 官方覆盖 | 说明 |
| --- | --- | --- | --- |
| 中国 | 国务院办公厅放假通知（gov.cn，Bing 检索） | 当年/次年 | 含调休补班，每年 10-11 月公布次年 |
| 日本 | 内閣府「国民の祝日について」公式 CSV | 至当年+1 年 | 含振替休日/国民の休日；其后按法定规则+天文预测 |
| 美国 | OPM（联邦人事管理局）Federal Holidays | 至 2030 | 联邦雇员实际休息日（含周末顺延 observed）；不含仅 DC 的就职日 |
| 英国 | GOV.UK Bank Holidays API | 至 2028 | 英格兰+威尔士口径；苏格兰/北爱尔兰另有当地假日 |
| 法国 | data.gouv / Etalab jours fériés API | 至当前+5 年 | 法国本土口径；不含阿尔萨斯-摩泽尔与海外省当地假日 |
| 德国 | 各州 Feiertagsgesetz 统一法定口径 + Berlin.de 官方核对 | 2024-2030 | 全德 16 州一致的 9 个全国性假日；不含各州特有假日 |

## 爬虫脚本

| 脚本 | 输出 |
| --- | --- |
| `fetch_holiday.py` | `holiday-data-china.json` |
| `fetch_holiday_japan.py` | `holiday-data-japan.json` |
| `fetch_holiday_usa.py` | `holiday-data-usa.json` |
| `fetch_holiday_uk.py` | `holiday-data-uk.json` |
| `fetch_holiday_france.py` | `holiday-data-france.json` |
| `fetch_holiday_germany.py` | `holiday-data-germany.json` |
| `holiday_common.py` | 共享工具（HTTP/日期/Easter/输出 schema） |

只依赖 Python 标准库。官方尚未公布的年份（如日本 2028+、英国 2029+）
由脚本按法定规则推算并写入文件，但**不计入 `officialYears`**——官方源
更新后爬虫自动用官方日期覆盖。

## 更新数据

```bash
python3 fetch_holiday.py            # 中国
python3 fetch_holiday_japan.py      # 日本
python3 fetch_holiday_usa.py        # 美国
python3 fetch_holiday_uk.py         # 英国
python3 fetch_holiday_france.py     # 法国
python3 fetch_holiday_germany.py    # 德国
```

或到 Actions 手动触发「自动更新节假日数据（6 国官方源）」
（每周一北京时间 08:00 自动运行，有变化才提交）。

## App 拉取地址

国内访问建议走 jsDelivr CDN：

```
https://cdn.jsdelivr.net/gh/grimlock-zdh/ClockWork-holiday-data@main/holiday-data-<country>.json
```

原始地址：

```
https://raw.githubusercontent.com/grimlock-zdh/ClockWork-holiday-data/main/holiday-data-<country>.json
```

> ClockWork 主仓库的 `sync-holiday-data.yml` 每周从本仓库拉全部
> `holiday-data-*.json` 同步 App/挂件内置快照。
