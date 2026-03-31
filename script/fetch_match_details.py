#!/usr/bin/env python3
"""
获取比赛详细信息（包括队伍名称、选手等）
使用方法:
    python fetch_match_details.py <match_id>
    python fetch_match_details.py --file ti2025_match_ids.json --limit 10
"""

import requests
import json
import argparse
import time
from datetime import datetime

BASE_URL = "https://api.opendota.com/api"


def get_match_details(match_id: int) -> dict:
    """获取单场比赛的详细信息"""
    response = requests.get(f"{BASE_URL}/matches/{match_id}")
    response.raise_for_status()
    return response.json()


def format_match_summary(match: dict) -> str:
    """格式化比赛摘要"""
    match_id = match.get('match_id', 'N/A')
    start_time = match.get('start_time', 0)
    match_time = datetime.fromtimestamp(start_time) if start_time else 'Unknown'
    
    radiant_name = match.get('radiant_name') or match.get('radiant_team', {}).get('name', 'Radiant')
    dire_name = match.get('dire_name') or match.get('dire_team', {}).get('name', 'Dire')
    
    radiant_win = match.get('radiant_win', False)
    winner = radiant_name if radiant_win else dire_name
    
    radiant_score = match.get('radiant_score', 0)
    dire_score = match.get('dire_score', 0)
    
    duration = match.get('duration', 0)
    duration_str = f"{duration // 60}:{duration % 60:02d}"
    
    league_name = match.get('league', {}).get('name', 'Unknown')
    
    return f"""
Match ID: {match_id}
时间: {match_time}
联赛: {league_name}
对阵: {radiant_name} vs {dire_name}
比分: {radiant_score} - {dire_score}
胜者: {winner}
时长: {duration_str}
"""


def main():
    parser = argparse.ArgumentParser(description='获取 Dota2 比赛详细信息')
    parser.add_argument('match_id', nargs='?', type=int, help='比赛ID')
    parser.add_argument('--file', type=str, help='包含比赛ID列表的JSON文件')
    parser.add_argument('--limit', type=int, default=5, help='从文件中获取的比赛数量限制')
    parser.add_argument('--output', type=str, help='输出文件名')
    parser.add_argument('--delay', type=float, default=1.0, help='请求间隔秒数')
    args = parser.parse_args()
    
    if args.match_id:
        # 获取单场比赛
        print(f"获取比赛 {args.match_id} 的详细信息...")
        match = get_match_details(args.match_id)
        print(format_match_summary(match))
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(match, f, indent=2, ensure_ascii=False)
            print(f"详细数据已保存到: {args.output}")
    
    elif args.file:
        # 从文件读取比赛ID列表
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        match_ids = data.get('match_ids', [])[:args.limit]
        print(f"从 {args.file} 读取 {len(match_ids)} 个比赛ID")
        print("=" * 60)
        
        all_matches = []
        teams = set()
        
        for i, match_id in enumerate(match_ids):
            print(f"\n[{i+1}/{len(match_ids)}] 获取比赛 {match_id}...")
            try:
                match = get_match_details(match_id)
                print(format_match_summary(match))
                all_matches.append(match)
                
                # 收集队伍名称
                radiant_team = match.get('radiant_team', {})
                dire_team = match.get('dire_team', {})
                if radiant_team.get('name'):
                    teams.add(radiant_team.get('name'))
                if dire_team.get('name'):
                    teams.add(dire_team.get('name'))
                
            except Exception as e:
                print(f"获取失败: {e}")
            
            if i < len(match_ids) - 1:
                time.sleep(args.delay)
        
        print("\n" + "=" * 60)
        print(f"共获取 {len(all_matches)} 场比赛详情")
        print(f"\n参赛队伍 ({len(teams)} 支):")
        for team in sorted(teams):
            print(f"  - {team}")
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_matches": len(all_matches),
                    "teams": sorted(list(teams)),
                    "matches": all_matches
                }, f, indent=2, ensure_ascii=False)
            print(f"\n详细数据已保存到: {args.output}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
