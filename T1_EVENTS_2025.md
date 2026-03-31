# Dota2 T1 级别赛事汇总 (2025)

> 数据来源: OpenDota API  
> 更新时间: 2026-03-23

## 统计概览

| 指标 | 数值 |
|------|------|
| T1 联赛总数（历史） | 235 个 |
| 2025 年活跃联赛 | 39 个 |
| 2025 年 T1 比赛总数 | 4,411 场 |

## T1 赛事分类

### 1. The International (TI)
> 最高级别赛事，tier: premium

**2025 年赛事 (7 个联赛, 369 场比赛)**

| 赛事名称 | League ID | 比赛数 |
|----------|-----------|--------|
| The International 2025 | 18324 | 144 |
| Road To TI 2025 - Eastern Europe | 18304 | 44 |
| Road To TI 2025 - South America | 18305 | 44 |
| Road To TI 2025 - Southeast Asia | 18308 | 43 |
| Road To TI 2025 - Western Europe | 18309 | 39 |
| Road To TI 2025 - China | 18306 | 31 |
| Road To TI 2025 - North America | 18307 | 24 |

---

### 2. 梦幻联赛 (DreamLeague)
> tier: professional

**2025 年赛事 (8 个联赛, 2,185 场比赛)**

| 赛事名称 | League ID | 比赛数 |
|----------|-----------|--------|
| DreamLeague Season 25 Qualifiers | 17628 | 454 |
| DreamLeague Season 27 Qualifiers | 18629 | 432 |
| DreamLeague Season 26 Qualifiers | 17874 | 427 |
| DreamLeague Season 27 | 18988 | 206 |
| DreamLeague Season 26 | 18111 | 202 |
| DreamLeague Season 25 | 17765 | 196 |
| DreamLeague Division 2 Season 1 | 18769 | 170 |
| DreamLeague Division 2 Season 2 | 18897 | 98 |

---

### 3. PGL 大型赛事
> tier: professional

**2025 年赛事 (20 个联赛, 935 场比赛)**

| 赛事名称 | League ID | 比赛数 |
|----------|-----------|--------|
| PGL Wallachia 2025 Season 6 | 18849 | 118 |
| PGL Wallachia 2025 Season 5 | 18649 | 116 |
| PGL Wallachia 2025 Season 4 | 18369 | 115 |
| PGL Wallachia 2025 Season 3 | 18115 | 112 |
| PGL Wallachia S6 EEU Closed Qualifiers | 18794 | 39 |
| PGL Wallachia S4 EEU Closed Qualifiers | 18196 | 39 |
| PGL Wallachia S6 AMER Closed Qualifiers | 18799 | 38 |
| PGL Wallachia S6 SEA Closed Qualifiers | 18795 | 37 |
| PGL Wallachia S4 SEA Closed Qualifiers | 18197 | 37 |
| PGL Wallachia S4 WEU Closed Qualifiers | 18195 | 37 |
| *... 还有 10 个预选赛* | - | - |

---

### 4. ESL One 系列赛
> tier: professional

**2025 年赛事 (2 个联赛, 555 场比赛)**

| 赛事名称 | League ID | 比赛数 |
|----------|-----------|--------|
| ESL One Raleigh 2025 Qualifiers | 17629 | 465 |
| ESL One Raleigh 2025 | 17795 | 90 |

---

### 5. Esports World Cup
> tier: professional

**2025 年赛事 (2 个联赛, 367 场比赛)**

| 赛事名称 | League ID | 比赛数 |
|----------|-----------|--------|
| Esports World Cup 2025 Qualifiers | 18210 | 278 |
| Esports World Cup 2025 | 18375 | 89 |

---

### 6. 利雅得大师赛 (Riyadh Masters)
> tier: professional

**2025 年赛事: 暂无比赛数据**

历史赛事 (9 个):
- Riyadh Masters 2024 at Esports World Cup (ID: 16881)
- Riyadh Masters 2024 Qualifiers (ID: 16740)
- Riyadh Masters 2023 by Gamers8 (ID: 15475)
- Riyadh Masters by Gamers8 (ID: 14391)
- WEC Riyadh 2024 (ID: 17369)

---

### 7. BB 别墅杯 (BetBoom Dacha)
> tier: professional

**2025 年赛事: 暂无比赛数据**

历史赛事 (15 个):
- BetBoom Dacha Belgrade 2024 (ID: 17126)
- BetBoom Dacha Dubai 2024 (ID: 16169)
- BetBoom Dacha (ID: 15638)
- *以及多个区域预选赛*

---

## 数据文件

| 文件 | 说明 |
|------|------|
| `t1_events_2025.json` | 完整 T1 赛事数据 (含所有比赛 ID) |
| `pro_match_ids_2025.json` | 所有职业比赛 ID |
| `pro_matches_2025_full.json` | 完整比赛详情数据 |

## 获取比赛详情

使用 `fetch_match_details.py` 脚本获取具体比赛信息:

```bash
# 获取单场比赛
python3 fetch_match_details.py 8461956309

# 批量获取
python3 fetch_match_details.py --file t1_events_2025.json --limit 20 --output t1_details.json
```
