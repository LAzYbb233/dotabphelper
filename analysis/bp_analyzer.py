#!/usr/bin/env python3
"""
BP 分析引擎
读取 T1 比赛数据，生成：
- 英雄统计 (胜率、ban/pick率、阶段偏好)
- 队伍统计 (习惯英雄、常用ban、克制关系)
- 英雄协同/克制矩阵
- 输出 data/bp_analysis.json 供 API 使用
"""

import json
import re
import sys
import time
import argparse
import requests
from pathlib import Path
from collections import defaultdict
from itertools import combinations
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"


# ─────────────────────────────────────────────
# 英雄元数据
# ─────────────────────────────────────────────

def fetch_hero_metadata() -> dict:
    """从 OpenDota 获取英雄元数据（含 npc 名称，用于 CDN 图片 URL）"""
    cache_file = DATA_DIR / "heroes_meta.json"
    if cache_file.exists():
        print(f"  使用缓存英雄数据: {cache_file}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    print("  从 OpenDota 获取英雄元数据...")
    try:
        resp = requests.get("https://api.opendota.com/api/heroes", timeout=15)
        resp.raise_for_status()
        heroes = resp.json()
        # 转为 {hero_id: {name, localized_name, ...}}
        meta = {}
        for h in heroes:
            hid = str(h["id"])
            npc_short = h["name"].replace("npc_dota_hero_", "")  # e.g. "antimage"
            meta[hid] = {
                "id": h["id"],
                "name": h["localized_name"],           # "Anti-Mage"
                "npc_name": npc_short,                 # "antimage" (for CDN URL)
                "primary_attr": h.get("primary_attr", ""),
                "attack_type": h.get("attack_type", ""),
                "roles": h.get("roles", []),
                "img": f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{npc_short}.png",
            }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"  英雄数据已缓存: {len(meta)} 个英雄")
        return meta
    except Exception as e:
        print(f"  [警告] 无法获取英雄元数据: {e}")
        return {}


def fetch_hero_position_data() -> dict:
    """从 OpenDota heroStats 获取英雄位置分布数据（1-5号位）"""
    cache_file = DATA_DIR / "hero_positions.json"
    if cache_file.exists():
        print(f"  使用缓存位置数据: {cache_file}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)

    print("  从 OpenDota 获取英雄位置数据...")
    try:
        resp = requests.get("https://api.opendota.com/api/heroStats", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        result = {}
        for hero in data:
            hid = str(hero["id"])
            # heroStats 返回字段如 "1_pick", "2_pick" ... "5_pick"
            pos_picks = {p: hero.get(f"{p}_pick", 0) for p in range(1, 6)}
            total = sum(pos_picks.values())
            if total > 0:
                primary = max(range(1, 6), key=lambda p: pos_picks[p])
                result[hid] = {
                    "primary_position": primary,
                    "position_rates": {
                        str(p): round(pos_picks[p] / total, 3)
                        for p in range(1, 6)
                    },
                }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  位置数据已缓存: {len(result)} 个英雄")
        return result
    except Exception as e:
        print(f"  [警告] 无法获取英雄位置数据: {e}")
        return {}


def parse_hero_map_md() -> dict:
    """解析 config/dota2_hero_map.md 作为后备映射"""
    hero_md = CONFIG_DIR / "dota2_hero_map.md"
    if not hero_md.exists():
        return {}
    result = {}
    for line in hero_md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|", line)
        if m:
            hid, en, cn, attr = m.group(1), m.group(2), m.group(3), m.group(4)
            result[hid] = {"id": int(hid), "name": en, "cn_name": cn, "primary_attr": attr}
    return result


# ─────────────────────────────────────────────
# BP 顺序：Captains Mode
# order 0-23:
#   Ban Ph1:  0-5  (A B A B A B)
#   Pick Ph1: 6-9  (A B B A)
#   Ban Ph2:  10-13 (B A B A)
#   Pick Ph2: 14-23 (B A A B A B... )
# team 0 = radiant, 1 = dire
# "A" here means first-ban team (determined per match by picks_bans[0].team)
# ─────────────────────────────────────────────

def get_draft_phase(order: int) -> int:
    """返回所在阶段 1=Ban1, 2=Pick1, 3=Ban2, 4=Pick2"""
    if order <= 5:
        return 1  # Ban phase 1
    elif order <= 9:
        return 2  # Pick phase 1
    elif order <= 13:
        return 3  # Ban phase 2
    else:
        return 4  # Pick phase 2


# ─────────────────────────────────────────────
# 核心分析
# ─────────────────────────────────────────────

def analyze(matches: list, hero_meta: dict) -> dict:
    total = len(matches)
    print(f"\n分析 {total} 场比赛...")

    # --- 初始化统计容器 ---
    hero_stats = defaultdict(lambda: {
        "pick_count": 0, "ban_count": 0, "pick_win": 0,
        "phase_picks": defaultdict(int),  # phase → count
        "phase_bans": defaultdict(int),
    })

    team_stats = defaultdict(lambda: {
        "name": "", "tag": "", "logo_url": "",
        "total_matches": 0, "wins": 0,
        "hero_picks": defaultdict(lambda: {"count": 0, "wins": 0}),
        "hero_bans": defaultdict(lambda: {"count": 0}),
        "hero_against_bans": defaultdict(lambda: {"count": 0}),  # 对手 ban 掉哪些英雄
    })

    # pair synergy: (hero_a, hero_b) → {count, wins}
    pair_synergy = defaultdict(lambda: {"count": 0, "wins": 0})

    # counter data: (attacker_hero, victim_hero) → {count, attacker_wins}
    # attacker_hero 在 radiant, victim_hero 在 dire (or vice versa, we normalize by min,max)
    counter_data = defaultdict(lambda: {"count": 0, "hero_a_wins": 0})

    skipped = 0
    for match in matches:
        picks_bans = match.get("picks_bans")
        if not picks_bans:
            skipped += 1
            continue

        radiant_win = match.get("radiant_win")
        if radiant_win is None:
            skipped += 1
            continue

        radiant_team_id = match.get("radiant_team_id")
        dire_team_id = match.get("dire_team_id")

        # 更新队伍基本信息（取最后一次遇到的）
        for side, team_id, team_name, team_tag, team_logo, won in [
            ("radiant", radiant_team_id, match.get("radiant_team_name"), match.get("radiant_team_tag"),
             match.get("radiant_team_logo"), radiant_win),
            ("dire", dire_team_id, match.get("dire_team_name"), match.get("dire_team_tag"),
             match.get("dire_team_logo"), not radiant_win),
        ]:
            if not team_id:
                continue
            tid = str(team_id)
            ts = team_stats[tid]
            ts["name"] = team_name or ts["name"]
            ts["tag"] = team_tag or ts["tag"]
            ts["logo_url"] = team_logo or ts["logo_url"]
            ts["total_matches"] += 1
            if won:
                ts["wins"] += 1

        # 解析 picks_bans
        radiant_picks = []
        dire_picks = []
        radiant_bans = []
        dire_bans = []

        for pb in picks_bans:
            hero_id = str(pb.get("hero_id", 0))
            team = pb.get("team", 0)   # 0=radiant, 1=dire
            is_pick = pb.get("is_pick", False)
            order = pb.get("order", 0)
            phase = get_draft_phase(order)

            if is_pick:
                hero_stats[hero_id]["pick_count"] += 1
                hero_stats[hero_id]["phase_picks"][phase] += 1
                if team == 0:
                    radiant_picks.append(hero_id)
                    hero_stats[hero_id]["pick_win"] += 1 if radiant_win else 0
                    if radiant_team_id:
                        ts = team_stats[str(radiant_team_id)]
                        ts["hero_picks"][hero_id]["count"] += 1
                        if radiant_win:
                            ts["hero_picks"][hero_id]["wins"] += 1
                else:
                    dire_picks.append(hero_id)
                    hero_stats[hero_id]["pick_win"] += 0 if radiant_win else 1
                    if dire_team_id:
                        ts = team_stats[str(dire_team_id)]
                        ts["hero_picks"][hero_id]["count"] += 1
                        if not radiant_win:
                            ts["hero_picks"][hero_id]["wins"] += 1
            else:
                hero_stats[hero_id]["ban_count"] += 1
                hero_stats[hero_id]["phase_bans"][phase] += 1
                if team == 0:
                    radiant_bans.append(hero_id)
                    if radiant_team_id:
                        team_stats[str(radiant_team_id)]["hero_bans"][hero_id]["count"] += 1
                    # dire 方的英雄被 ban 掉
                    if dire_team_id:
                        team_stats[str(dire_team_id)]["hero_against_bans"][hero_id]["count"] += 1
                else:
                    dire_bans.append(hero_id)
                    if dire_team_id:
                        team_stats[str(dire_team_id)]["hero_bans"][hero_id]["count"] += 1
                    if radiant_team_id:
                        team_stats[str(radiant_team_id)]["hero_against_bans"][hero_id]["count"] += 1

        # 计算协同 (同队 picks)
        for picks, won in [(radiant_picks, radiant_win), (dire_picks, not radiant_win)]:
            for h_a, h_b in combinations(sorted(picks), 2):
                key = f"{h_a}:{h_b}"
                pair_synergy[key]["count"] += 1
                if won:
                    pair_synergy[key]["wins"] += 1

        # 计算克制 (跨队 picks)
        for r_hero in radiant_picks:
            for d_hero in dire_picks:
                key = f"{r_hero}:{d_hero}"
                counter_data[key]["count"] += 1
                if radiant_win:
                    counter_data[key]["hero_a_wins"] += 1

    print(f"  跳过无 BP 数据的比赛: {skipped} 场")

    # --- 计算衍生指标 ---
    # 英雄统计：胜率、pick/ban 率
    hero_output = {}
    for hid, hs in hero_stats.items():
        pc = hs["pick_count"]
        bc = hs["ban_count"]
        hero_output[hid] = {
            "pick_count": pc,
            "ban_count": bc,
            "pick_win": hs["pick_win"],
            "pick_rate": round(pc / total, 4) if total else 0,
            "ban_rate": round(bc / total, 4) if total else 0,
            "win_rate": round(hs["pick_win"] / pc, 4) if pc else 0,
            "phase_picks": dict(hs["phase_picks"]),
            "phase_bans": dict(hs["phase_bans"]),
        }

    # 队伍统计：序列化 defaultdict
    team_output = {}
    for tid, ts in team_stats.items():
        tm = ts["total_matches"]
        team_output[tid] = {
            "name": ts["name"],
            "tag": ts["tag"],
            "logo_url": ts["logo_url"],
            "total_matches": tm,
            "wins": ts["wins"],
            "win_rate": round(ts["wins"] / tm, 4) if tm else 0,
            "hero_picks": {
                hid: {"count": v["count"], "wins": v["wins"],
                      "win_rate": round(v["wins"] / v["count"], 4) if v["count"] else 0}
                for hid, v in ts["hero_picks"].items()
            },
            "hero_bans": {hid: v["count"] for hid, v in ts["hero_bans"].items()},
            "hero_against_bans": {hid: v["count"] for hid, v in ts["hero_against_bans"].items()},
        }

    # 协同矩阵：只保留出现 >= 2 次的对
    synergy_output = {
        k: {**v, "win_rate": round(v["wins"] / v["count"], 4)}
        for k, v in pair_synergy.items() if v["count"] >= 2
    }

    # 克制矩阵：只保留出现 >= 2 次的对
    counter_output = {
        k: {**v, "hero_a_win_rate": round(v["hero_a_wins"] / v["count"], 4)}
        for k, v in counter_data.items() if v["count"] >= 2
    }

    return {
        "total_matches": total,
        "skipped": skipped,
        "heroes": hero_output,
        "teams": team_output,
        "synergy": synergy_output,
        "counter": counter_output,
    }


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BP 分析引擎")
    parser.add_argument(
        "--input", type=str,
        default=str(DATA_DIR),
        help="输入路径：目录（读取所有 matches.json）或单个 JSON 文件 (默认: data/)"
    )
    parser.add_argument(
        "--output", type=str,
        default=str(DATA_DIR / "bp_analysis.json"),
        help="输出分析结果文件 (默认: data/bp_analysis.json)"
    )
    parser.add_argument(
        "--no-fetch-heroes", action="store_true",
        help="跳过从 OpenDota 获取英雄元数据"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    print("=" * 60)
    print("Dota 2 BP 分析引擎")
    print("=" * 60)

    if not input_path.exists():
        print(f"[错误] 找不到输入路径: {input_path}")
        print("请先运行: python script/fetch_t1_matches_with_patch.py --data-dir data")
        sys.exit(1)

    # 支持两种输入格式：目录 或 单个 JSON 文件
    matches = []
    if input_path.is_dir():
        match_files = sorted(input_path.rglob("matches.json"))
        if not match_files:
            print(f"[错误] 目录 {input_path} 中未找到任何 matches.json 文件")
            sys.exit(1)
        print(f"\n从目录读取比赛数据: {input_path}")
        print(f"  找到 {len(match_files)} 个数据文件:")
        for mf in match_files:
            rel = mf.relative_to(input_path)
            with open(mf, encoding="utf-8") as f:
                raw = json.load(f)
            file_matches = raw.get("matches", []) if isinstance(raw, dict) else raw
            matches.extend(file_matches)
            print(f"    {rel}  ({len(file_matches)} 场)")
    else:
        print(f"\n读取比赛数据: {input_path}")
        with open(input_path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            matches = raw
        elif isinstance(raw, dict):
            matches = raw.get("matches", [])

    print(f"\n共 {len(matches)} 场比赛")

    # 筛选有 picks_bans 的比赛
    matches_with_bp = [m for m in matches if m.get("picks_bans")]
    print(f"含 BP 数据的比赛: {len(matches_with_bp)} 场")

    if not matches_with_bp:
        print("\n[警告] 没有含 BP 数据的比赛。")
        print("请使用修改后的 fetch_t1_matches_with_patch.py 重新获取数据。")

    # 获取英雄元数据
    hero_meta = {}
    hero_positions = {}
    if not args.no_fetch_heroes:
        print("\n获取英雄元数据...")
        hero_meta = fetch_hero_metadata()
        print("\n获取英雄位置数据...")
        hero_positions = fetch_hero_position_data()

    # 运行分析
    analysis = analyze(matches_with_bp if matches_with_bp else matches, hero_meta)

    # 合并英雄元数据
    print(f"\n合并英雄元数据...")
    fallback = parse_hero_map_md()
    for hid, hdata in hero_meta.items():
        if hid not in analysis["heroes"]:
            analysis["heroes"][hid] = {
                "pick_count": 0, "ban_count": 0, "pick_win": 0,
                "pick_rate": 0.0, "ban_rate": 0.0, "win_rate": 0.0,
                "phase_picks": {}, "phase_bans": {},
            }
        analysis["heroes"][hid].update({
            "name": hdata.get("name", ""),
            "npc_name": hdata.get("npc_name", ""),
            "img": hdata.get("img", ""),
            "primary_attr": hdata.get("primary_attr", ""),
            "roles": hdata.get("roles", []),
        })

    # 合并英雄位置数据
    for hid, pdata in hero_positions.items():
        if hid in analysis["heroes"]:
            analysis["heroes"][hid].update(pdata)

    # 用 fallback 补充缺失的英雄
    for hid, hdata in fallback.items():
        if hid not in analysis["heroes"]:
            analysis["heroes"][hid] = {
                "pick_count": 0, "ban_count": 0, "pick_win": 0,
                "pick_rate": 0.0, "ban_rate": 0.0, "win_rate": 0.0,
                "phase_picks": {}, "phase_bans": {},
            }
        if "name" not in analysis["heroes"][hid]:
            analysis["heroes"][hid]["name"] = hdata.get("name", "")
        if "cn_name" not in analysis["heroes"][hid]:
            analysis["heroes"][hid]["cn_name"] = hdata.get("cn_name", "")
        if "primary_attr" not in analysis["heroes"][hid]:
            analysis["heroes"][hid]["primary_attr"] = hdata.get("primary_attr", "")

    # 输出
    output_path.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    final = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": str(input_path),
        "total_matches": analysis["total_matches"],
        "skipped": analysis["skipped"],
        "heroes": analysis["heroes"],
        "teams": analysis["teams"],
        "synergy": analysis["synergy"],
        "counter": analysis["counter"],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 分析完成")
    print(f"  英雄数: {len(analysis['heroes'])}")
    print(f"  队伍数: {len(analysis['teams'])}")
    print(f"  协同对数: {len(analysis['synergy'])}")
    print(f"  克制对数: {len(analysis['counter'])}")
    print(f"  输出: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
