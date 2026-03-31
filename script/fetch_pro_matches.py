#!/usr/bin/env python3
"""
获取所有顶级 (premium + professional tier) 联赛的比赛数据
API 限制: 每分钟 60 次调用，即每秒 1 次

Tier 说明:
- premium: TI 系列赛事
- professional: DPC、Major、ESL One、DreamLeague 等职业赛事
- excluded: 其他业余/小型赛事
"""

import requests
import time
import json
import argparse
from datetime import datetime
from typing import Optional, List

BASE_URL = "https://api.opendota.com/api"
REQUEST_INTERVAL = 1.0  # 每分钟60次 = 每秒1次


def get_year_timestamps(year: int) -> tuple:
    """获取指定年份的开始和结束时间戳"""
    start = int(datetime(year, 1, 1).timestamp())
    end = int(datetime(year, 12, 31, 23, 59, 59).timestamp())
    return start, end


def rate_limited_request(url: str, request_count: list) -> Optional[dict]:
    """带速率限制的请求"""
    time.sleep(REQUEST_INTERVAL)
    request_count[0] += 1
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 429:
            print(f"    [警告] 触发限流，等待 60 秒...")
            time.sleep(60)
            return rate_limited_request(url, request_count)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"    [错误] 请求失败: {e}")
        return None


def get_all_leagues(request_count: list) -> list:
    """获取所有联赛列表"""
    print("正在获取联赛列表...")
    data = rate_limited_request(f"{BASE_URL}/leagues", request_count)
    if data:
        print(f"共获取到 {len(data)} 个联赛")
        return data
    return []


def filter_top_tier_leagues(leagues: list, tiers: List[str]) -> list:
    """筛选指定级别的联赛"""
    filtered = [l for l in leagues if l.get('tier') in tiers]
    tier_counts = {}
    for l in filtered:
        t = l.get('tier')
        tier_counts[t] = tier_counts.get(t, 0) + 1
    
    for tier, count in tier_counts.items():
        print(f"  {tier} 级别联赛: {count} 个")
    print(f"  合计: {len(filtered)} 个")
    return filtered


def get_league_matches(league_id: int, request_count: list) -> list:
    """获取指定联赛的所有比赛"""
    data = rate_limited_request(f"{BASE_URL}/leagues/{league_id}/matches", request_count)
    if data and isinstance(data, list):
        return data
    return []


def filter_matches_by_year(matches: list, year_start: int, year_end: int) -> list:
    """根据时间筛选比赛"""
    return [m for m in matches if year_start <= m.get('start_time', 0) <= year_end]


def save_progress(data: dict, filename: str):
    """保存进度"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='获取顶级联赛比赛数据')
    parser.add_argument('--year', type=int, default=2025, help='目标年份 (默认: 2025)')
    parser.add_argument('--tiers', type=str, default='premium,professional', 
                        help='联赛级别，逗号分隔 (默认: premium,professional)')
    parser.add_argument('--save-interval', type=int, default=50, help='每处理多少个联赛保存一次进度')
    parser.add_argument('--limit', type=int, default=0, help='限制处理的联赛数量 (0=不限制)')
    args = parser.parse_args()
    
    year = args.year
    tiers = [t.strip() for t in args.tiers.split(',')]
    year_start, year_end = get_year_timestamps(year)
    
    print("=" * 70)
    print("获取顶级职业联赛比赛数据")
    print("=" * 70)
    print(f"目标年份: {year}")
    print(f"联赛级别: {', '.join(tiers)}")
    print(f"时间范围: {datetime.fromtimestamp(year_start)} - {datetime.fromtimestamp(year_end)}")
    print(f"API 限制: 每分钟 60 次请求 (间隔 {REQUEST_INTERVAL} 秒)")
    print("=" * 70)
    
    request_count = [0]
    
    # 1. 获取所有联赛
    all_leagues = get_all_leagues(request_count)
    if not all_leagues:
        print("获取联赛列表失败")
        return
    
    # 2. 筛选指定级别联赛
    print(f"\n筛选联赛级别: {', '.join(tiers)}")
    top_leagues = filter_top_tier_leagues(all_leagues, tiers)
    if not top_leagues:
        print("未找到符合条件的联赛")
        return
    
    # 按联赛ID降序排列（更新的联赛优先）
    top_leagues.sort(key=lambda x: x.get('leagueid', 0), reverse=True)
    
    # 应用限制
    if args.limit > 0:
        top_leagues = top_leagues[:args.limit]
        print(f"\n限制处理前 {args.limit} 个联赛")
    
    # 估算时间
    total_seconds = len(top_leagues) * REQUEST_INTERVAL
    print(f"\n预计需要时间: {int(total_seconds//60)}分{int(total_seconds%60)}秒")
    
    # 打印部分联赛
    print(f"\n最新的 30 个联赛:")
    print("-" * 70)
    for i, league in enumerate(top_leagues[:30]):
        tier = league.get('tier', 'unknown')
        name = league.get('name', 'Unknown')[:45]
        lid = league.get('leagueid')
        print(f"  {i+1:3}. [{tier:12}] {name:45} (ID: {lid})")
    if len(top_leagues) > 30:
        print(f"  ... 还有 {len(top_leagues) - 30} 个联赛")
    print("-" * 70)
    
    # 3. 获取每个联赛的比赛
    all_matches = []
    leagues_with_matches = []
    all_match_ids = []
    
    print(f"\n开始获取各联赛的 {year} 年比赛数据...")
    
    start_time = time.time()
    
    for i, league in enumerate(top_leagues):
        league_id = league.get('leagueid')
        league_name = league.get('name', 'Unknown')
        league_tier = league.get('tier', 'unknown')
        
        elapsed = time.time() - start_time
        if i > 0:
            avg_time = elapsed / i
            eta = avg_time * (len(top_leagues) - i)
            eta_str = f"剩余 {int(eta//60)}分{int(eta%60)}秒"
        else:
            eta_str = ""
        
        print(f"\n[{i+1}/{len(top_leagues)}] [{league_tier}] {league_name[:35]} (ID: {league_id}) {eta_str}")
        
        matches = get_league_matches(league_id, request_count)
        
        if matches:
            matches_year = filter_matches_by_year(matches, year_start, year_end)
            
            if matches_year:
                print(f"    ✓ 找到 {len(matches_year)} 场 {year} 年比赛")
                for match in matches_year:
                    match['league_name'] = league_name
                    match['league_id'] = league_id
                    match['league_tier'] = league_tier
                all_matches.extend(matches_year)
                all_match_ids.extend([m.get('match_id') for m in matches_year])
                leagues_with_matches.append({
                    'name': league_name,
                    'id': league_id,
                    'tier': league_tier,
                    'match_count': len(matches_year)
                })
            else:
                if len(matches) > 0:
                    print(f"    - 无 {year} 年比赛 (历史 {len(matches)} 场)")
                else:
                    print(f"    - 无比赛数据")
        else:
            print(f"    - 请求失败或无数据")
        
        # 定期保存进度
        if (i + 1) % args.save_interval == 0:
            progress_file = f"pro_matches_{year}_progress.json"
            save_progress({
                "year": year,
                "tiers": tiers,
                "processed": i + 1,
                "total_leagues": len(top_leagues),
                "matches_found": len(all_matches),
                "leagues_with_matches": len(leagues_with_matches),
                "match_ids": all_match_ids,
                "leagues": leagues_with_matches
            }, progress_file)
            print(f"    [进度已保存]")
    
    # 4. 输出结果
    total_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("统计结果")
    print("=" * 70)
    print(f"总请求次数: {request_count[0]}")
    print(f"总耗时: {int(total_time//60)}分{int(total_time%60)}秒")
    print(f"\n{year} 年比赛总数: {len(all_matches)}")
    print(f"涉及联赛数: {len(leagues_with_matches)}")
    
    if all_matches:
        # 按tier分组统计
        tier_stats = {}
        for league in leagues_with_matches:
            tier = league['tier']
            if tier not in tier_stats:
                tier_stats[tier] = {'leagues': 0, 'matches': 0}
            tier_stats[tier]['leagues'] += 1
            tier_stats[tier]['matches'] += league['match_count']
        
        print(f"\n各级别统计:")
        print("-" * 40)
        for tier, stats in tier_stats.items():
            print(f"  {tier:15}: {stats['leagues']:3} 个联赛, {stats['matches']:5} 场比赛")
        
        # 按比赛数量排序
        leagues_with_matches.sort(key=lambda x: x['match_count'], reverse=True)
        
        print(f"\n比赛数量 Top 30 联赛:")
        print("-" * 70)
        for league in leagues_with_matches[:30]:
            tier = league['tier']
            name = league['name'][:40]
            count = league['match_count']
            print(f"  [{tier:12}] {name:40} : {count:4} 场")
        
        # 保存结果
        output_file = f"pro_match_ids_{year}.json"
        save_progress({
            "year": year,
            "tiers": tiers,
            "total_matches": len(all_match_ids),
            "leagues_count": len(leagues_with_matches),
            "tier_stats": tier_stats,
            "match_ids": all_match_ids,
            "leagues": leagues_with_matches
        }, output_file)
        print(f"\n比赛ID已保存到: {output_file}")
        
        full_output_file = f"pro_matches_{year}_full.json"
        save_progress({
            "year": year,
            "tiers": tiers,
            "total_matches": len(all_matches),
            "leagues": leagues_with_matches,
            "matches": all_matches
        }, full_output_file)
        print(f"完整数据已保存到: {full_output_file}")
    else:
        print(f"\n未找到 {year} 年的比赛数据")


if __name__ == "__main__":
    main()
