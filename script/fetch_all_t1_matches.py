#!/usr/bin/env python3
"""
获取所有 T1 (premium tier) 联赛的比赛数据
API 限制: 每分钟 60 次调用，即每秒 1 次
"""

import requests
import time
import json
import argparse
from datetime import datetime
from typing import Optional

BASE_URL = "https://api.opendota.com/api"

# 请求间隔：每分钟60次 = 每次请求间隔1秒
REQUEST_INTERVAL = 1.0


def get_year_timestamps(year: int) -> tuple:
    """获取指定年份的开始和结束时间戳"""
    start = int(datetime(year, 1, 1).timestamp())
    end = int(datetime(year, 12, 31, 23, 59, 59).timestamp())
    return start, end


def rate_limited_request(url: str, request_count: list) -> Optional[dict]:
    """带速率限制的请求"""
    # 确保请求间隔
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


def filter_premium_leagues(leagues: list) -> list:
    """筛选 premium (T1) 级别的联赛"""
    premium_leagues = [l for l in leagues if l.get('tier') == 'premium']
    print(f"其中 premium (T1) 级别联赛: {len(premium_leagues)} 个")
    return premium_leagues


def get_league_matches(league_id: int, request_count: list) -> list:
    """获取指定联赛的所有比赛"""
    data = rate_limited_request(f"{BASE_URL}/leagues/{league_id}/matches", request_count)
    if data and isinstance(data, list):
        return data
    return []


def filter_matches_by_year(matches: list, year_start: int, year_end: int) -> list:
    """根据时间筛选比赛"""
    return [m for m in matches if year_start <= m.get('start_time', 0) <= year_end]


def estimate_time(num_leagues: int) -> str:
    """估算所需时间"""
    # 每个联赛需要 1 次请求，加上获取联赛列表 1 次
    total_requests = num_leagues + 1
    total_seconds = total_requests * REQUEST_INTERVAL
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}分{seconds}秒"


def save_progress(data: dict, filename: str):
    """保存进度"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='获取所有 T1 联赛比赛数据')
    parser.add_argument('--year', type=int, default=2025, help='目标年份 (默认: 2025)')
    parser.add_argument('--save-interval', type=int, default=10, help='每处理多少个联赛保存一次进度')
    args = parser.parse_args()
    
    year = args.year
    year_start, year_end = get_year_timestamps(year)
    
    print("=" * 70)
    print("获取所有 T1 (Premium) 联赛比赛数据")
    print("=" * 70)
    print(f"目标年份: {year}")
    print(f"时间范围: {datetime.fromtimestamp(year_start)} - {datetime.fromtimestamp(year_end)}")
    print(f"API 限制: 每分钟 60 次请求 (间隔 {REQUEST_INTERVAL} 秒)")
    print("=" * 70)
    
    request_count = [0]  # 使用列表以便在函数间传递引用
    
    # 1. 获取所有联赛
    all_leagues = get_all_leagues(request_count)
    if not all_leagues:
        print("获取联赛列表失败")
        return
    
    # 2. 筛选 premium 级别联赛
    premium_leagues = filter_premium_leagues(all_leagues)
    if not premium_leagues:
        print("未找到 premium 级别的联赛")
        return
    
    # 按联赛ID降序排列（更新的联赛优先）
    premium_leagues.sort(key=lambda x: x.get('leagueid', 0), reverse=True)
    
    # 估算时间
    print(f"\n预计需要时间: {estimate_time(len(premium_leagues))}")
    
    # 打印所有 premium 联赛
    print(f"\n所有 Premium (T1) 联赛 ({len(premium_leagues)} 个):")
    print("-" * 70)
    for i, league in enumerate(premium_leagues):
        print(f"  {i+1:3}. {league.get('name', 'Unknown')[:50]:50} (ID: {league.get('leagueid')})")
    print("-" * 70)
    
    # 3. 获取每个联赛的比赛
    all_matches = []
    leagues_with_matches = []
    all_match_ids = []
    
    print(f"\n开始获取各联赛的 {year} 年比赛数据...")
    print(f"(每 {args.save_interval} 个联赛自动保存进度)")
    
    start_time = time.time()
    
    for i, league in enumerate(premium_leagues):
        league_id = league.get('leagueid')
        league_name = league.get('name', 'Unknown')
        
        elapsed = time.time() - start_time
        remaining_leagues = len(premium_leagues) - i
        if i > 0:
            avg_time = elapsed / i
            eta = avg_time * remaining_leagues
            eta_str = f"预计剩余 {int(eta//60)}分{int(eta%60)}秒"
        else:
            eta_str = ""
        
        print(f"\n[{i+1}/{len(premium_leagues)}] {league_name[:40]} (ID: {league_id}) {eta_str}")
        
        matches = get_league_matches(league_id, request_count)
        
        if matches:
            # 筛选指定年份的比赛
            matches_year = filter_matches_by_year(matches, year_start, year_end)
            
            if matches_year:
                print(f"    ✓ 找到 {len(matches_year)} 场 {year} 年比赛 (总共 {len(matches)} 场)")
                for match in matches_year:
                    match['league_name'] = league_name
                    match['league_id'] = league_id
                    match['league_tier'] = 'premium'
                all_matches.extend(matches_year)
                all_match_ids.extend([m.get('match_id') for m in matches_year])
                leagues_with_matches.append({
                    'name': league_name,
                    'id': league_id,
                    'match_count': len(matches_year),
                    'total_matches': len(matches)
                })
            else:
                print(f"    - 无 {year} 年比赛 (历史比赛 {len(matches)} 场)")
        else:
            print(f"    - 无比赛数据")
        
        # 定期保存进度
        if (i + 1) % args.save_interval == 0:
            progress_file = f"t1_matches_{year}_progress.json"
            save_progress({
                "year": year,
                "processed_leagues": i + 1,
                "total_leagues": len(premium_leagues),
                "matches_found": len(all_matches),
                "leagues_with_matches": len(leagues_with_matches),
                "match_ids": all_match_ids,
                "leagues": leagues_with_matches
            }, progress_file)
            print(f"    [进度已保存到 {progress_file}]")
    
    # 4. 输出最终结果
    total_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("统计结果")
    print("=" * 70)
    print(f"总请求次数: {request_count[0]}")
    print(f"总耗时: {int(total_time//60)}分{int(total_time%60)}秒")
    print(f"\n{year} 年 T1 比赛总数: {len(all_matches)}")
    print(f"涉及联赛数: {len(leagues_with_matches)}")
    
    if all_matches:
        # 按比赛数量排序
        leagues_with_matches.sort(key=lambda x: x['match_count'], reverse=True)
        
        print(f"\n各联赛 {year} 年比赛数量 (Top 20):")
        print("-" * 70)
        for league in leagues_with_matches[:20]:
            print(f"  {league['name'][:45]:45} : {league['match_count']:4} 场")
        if len(leagues_with_matches) > 20:
            print(f"  ... 还有 {len(leagues_with_matches) - 20} 个联赛")
        
        # 保存比赛ID列表
        output_file = f"t1_match_ids_{year}.json"
        save_progress({
            "year": year,
            "tier": "premium",
            "total_matches": len(all_match_ids),
            "leagues_count": len(leagues_with_matches),
            "match_ids": all_match_ids,
            "leagues": leagues_with_matches
        }, output_file)
        print(f"\n比赛ID已保存到: {output_file}")
        
        # 保存完整比赛数据
        full_output_file = f"t1_matches_{year}_full.json"
        save_progress({
            "year": year,
            "tier": "premium",
            "total_matches": len(all_matches),
            "leagues_count": len(leagues_with_matches),
            "leagues": leagues_with_matches,
            "matches": all_matches
        }, full_output_file)
        print(f"完整比赛数据已保存到: {full_output_file}")
        
        # 显示最近几场比赛示例
        all_matches.sort(key=lambda x: x.get('start_time', 0), reverse=True)
        print(f"\n最近 10 场 T1 比赛:")
        print("-" * 70)
        for match in all_matches[:10]:
            match_time = datetime.fromtimestamp(match.get('start_time', 0))
            league = match.get('league_name', 'Unknown')[:25]
            match_id = match.get('match_id', 'N/A')
            print(f"  [{match_time.strftime('%Y-%m-%d')}] {league:25} | ID: {match_id}")
    else:
        print(f"\n未找到 {year} 年的 T1 比赛数据")


if __name__ == "__main__":
    main()
