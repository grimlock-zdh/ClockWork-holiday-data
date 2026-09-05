# ClockWork-holiday-data

发条 ClockWork 的法定节假日/调休/节气数据仓库（公开）。

## 内容

- `holiday-data-china.json` — 中国数据（`holidays` / `extra_workdays` / `ranges` / `metadata`）
- `holiday-data-<country>.json` — 规则型国家数据（日本/美国/英国/法国/德国，
  由 `generate_statutory.py` 从 App 内置规则生成）
- `fetch_holiday.py` — 自动抓取国务院放假通知并生成 `holiday-data-china.json` 的脚本
- `generate_statutory.py` — 按国家规则生成 `holiday-data-<country>.json`
- `HOLIDAY_RULES.md` — 节假日规则说明（哪些算放假/补班）
- `.github/workflows/fetch-holiday.yml` — 每周一自动检查更新 + 手动触发

## 多国数据结构

每个国家一份 `holiday-data-<country>.json`（country = App 国家标识：
china / japan / usa / uk / france / germany），命名统一。

各国文件统一 schema：

```json
{ "holidays": ["2024-01-01"], "extra_workdays": [], "ranges": [], "metadata": {...} }
```

⚠️ **规则型国家（非中国）是简化数据**：不含基督教浮动假日（复活节等）与
「逢周末顺延/补休」；正式支持某国前需按官方口径核对补齐（见
`generate_statutory.py` 顶部说明）。

## App 拉取地址

国内访问建议走 jsDelivr CDN（GitHub 镜像，国内一般可直连）：

```
https://cdn.jsdelivr.net/gh/grimlock-zdh/ClockWork-holiday-data@main/holiday-data-china.json
```

原始地址：

```
https://raw.githubusercontent.com/grimlock-zdh/ClockWork-holiday-data/main/holiday-data-china.json
```

## 更新数据

```bash
python3 fetch_holiday.py   # 生成 holiday-data-china.json
```

或到 Actions 里手动触发 `自动更新节假日数据` workflow。

规则型国家更新：改规则后运行 `python3 generate_statutory.py` 重新生成各国文件。
