#!/usr/bin/env python3
"""
获取 T1 级别赛事的比赛数据（包含版本号）
- T1 赛事定义：The International, DreamLeague, PGL, ESL One, Riyadh Masters, BetBoom Dacha, Esports World Cup
- API 限制: 每分钟 60 次调用
- 需要获取比赛详情以获取 patch 版本号
"""

import requests
import time
import json
import argparse
from datetime import datetime
from typing import Optional, List, Dict

BASE_URL = "https://api.opendota.com/api"

# 请求间隔：每分钟60次 = 每次请求间隔1秒
REQUEST_INTERVAL = 1.0

# T1 赛事关键词
T1_FILTERS = {
    'The International': ['The International', 'Road To The International'],
    'DreamLeague': ['DreamLeague'],
    'PGL': ['PGL Wallachia', 'PGL Major'],
    'ESL One': ['ESL One', 'ESL ONE'],
    'Riyadh Masters': ['Riyadh Masters'],
    'BetBoom Dacha': ['BetBoom Dacha'],
    'Esports World Cup': ['Esports World Cup'],
}


def is_t1_league(name: str) -> Optional[str]:
    """判断是否为 T1 联赛，返回类别名"""
    for category, keywords in T1_FILTERS.items():
        if any(kw.lower() in name.lower() for kw in keywords):
            return category
    return None


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


def get_league_matches(league_id: int, request_count: list) -> list:
    """获取指定联赛的所有比赛"""
    data = rate_limited_request(f"{BASE_URL}/leagues/{league_id}/matches", request_count)
    if data and isinstance(data, list):
        return data
    return []


def get_match_details(match_id: int, request_count: list) -> Optional[dict]:
    """获取比赛详情（包含 patch 版本号）"""
    data = rate_limited_request(f"{BASE_URL}/matches/{match_id}", request_count)
    return data


def filter_matches_by_time(matches: list, start_timestamp: int) -> list:
    """根据时间筛选比赛（只保留指定时间戳之后的比赛）"""
    return [m for m in matches if m.get('start_time', 0) >= start_timestamp]


def save_progress(data: dict, filename: str):
    """保存进度"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_patch_version_map(request_count: list) -> Dict[int, str]:
    """获取 patch ID → 版本名称映射（如 55 → '7.40c'）"""
    print("获取版本号映射...")
    data = rate_limited_request(f"{BASE_URL}/constants/patch", request_count)
    if not data or not isinstance(data, list):
        return {}
    mapping = {}
    for p in data:
        pid = p.get('id')
        pname = p.get('name', '')
        if pid is not None:
            mapping[int(pid)] = pname
    print(f"  获取到 {len(mapping)} 个版本记录")
    return mapping


def sanitize_dirname(name: str) -> str:
    """将名称转换为合法目录名（保留中文，替换特殊字符）"""
    import re
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name


def save_by_directory(
    matches: list,
    data_dir: str,
    patch_map: Dict[int, str],
    start_date: str,
    leagues_with_matches: list,
):
    """
    按 /版本号/比赛名称/ 目录结构保存数据
    data/{patch_name}/{t1_category}/matches.json
    """
    import os
    from collections import defaultdict

    # 按 (patch_name, category) 分组
    groups: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for match in matches:
        raw_patch = match.get('patch')
        if raw_patch is not None:
            version = patch_map.get(int(raw_patch), f'patch_{raw_patch}')
        else:
            version = 'unknown'
        category = sanitize_dirname(match.get('t1_category') or 'Unknown')
        groups[version][category].append(match)

    saved_paths = []
    for version, categories in sorted(groups.items()):
        for category, cat_matches in sorted(categories.items()):
            dir_path = os.path.join(data_dir, version, category)
            os.makedirs(dir_path, exist_ok=True)
            out_file = os.path.join(dir_path, 'matches.json')

            cat_matches.sort(key=lambda x: x.get('start_time', 0), reverse=True)
            output = {
                'version': version,
                'category': category,
                'start_date': start_date,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_matches': len(cat_matches),
                'matches': cat_matches,
            }
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            saved_paths.append(out_file)
            print(f"  ✓ {version}/{category}/matches.json  ({len(cat_matches)} 场)")

    # 保存顶层索引
    index_file = os.path.join(data_dir, 'index.json')
    index = {
        'description': f'T1 级别赛事比赛数据（{start_date} 之后）',
        'start_date': start_date,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_matches': len(matches),
        'versions': sorted(groups.keys()),
        'leagues': leagues_with_matches,
        'files': [p.replace(data_dir + '/', '') for p in saved_paths],
    }
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"\n  索引已保存: {index_file}")
    return saved_paths


def load_progress(filename: str) -> Optional[dict]:
    """加载进度"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def main():
    parser = argparse.ArgumentParser(description='获取 T1 级别赛事比赛数据（含版本号）')
    parser.add_argument('--start-date', type=str, default='2026-01-22', 
                        help='起始日期 (默认: 2026-01-22，即 7.40c 更新日期)')
    parser.add_argument('--save-interval', type=int, default=50, 
                        help='每处理多少场比赛保存一次进度')
    parser.add_argument('--resume', action='store_true', 
                        help='从上次进度继续')
    parser.add_argument('--output', type=str, default='t1_matches_with_patch.json',
                        help='进度文件名（中间进度用，不影响最终目录输出）')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='最终输出根目录，按 {版本号}/{比赛名称}/matches.json 保存 (默认: data)')
    args = parser.parse_args()
    
    # 解析起始日期
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    start_timestamp = int(start_date.timestamp())
    
    print("=" * 70)
    print("获取 T1 级别赛事比赛数据（含版本号）")
    print("=" * 70)
    print(f"起始日期: {args.start_date} (7.40c 更新后)")
    print(f"API 限制: 每分钟 60 次请求 (间隔 {REQUEST_INTERVAL} 秒)")
    print(f"T1 赛事类别: {', '.join(T1_FILTERS.keys())}")
    print("=" * 70)
    
    request_count = [0]

    # 获取版本号映射
    patch_map = get_patch_version_map(request_count)

    # 检查是否有进度文件
    progress_file = args.output.replace('.json', '_progress.json')
    processed_match_ids = set()
    all_match_details = []
    
    if args.resume:
        progress = load_progress(progress_file)
        if progress:
            processed_match_ids = set(progress.get('processed_match_ids', []))
            all_match_details = progress.get('match_details', [])
            print(f"从进度恢复: 已处理 {len(processed_match_ids)} 场比赛")
    
    # 1. 获取所有联赛
    all_leagues = get_all_leagues(request_count)
    if not all_leagues:
        print("获取联赛列表失败")
        return
    
    # 2. 筛选 T1 级别联赛
    t1_leagues = []
    for league in all_leagues:
        name = league.get('name', '')
        category = is_t1_league(name)
        if category:
            league['t1_category'] = category
            t1_leagues.append(league)
    
    # 按联赛ID降序排列（更新的联赛优先）
    t1_leagues.sort(key=lambda x: x.get('leagueid', 0), reverse=True)
    
    print(f"\n找到 {len(t1_leagues)} 个 T1 级别联赛")
    
    # 按类别统计
    category_count = {}
    for league in t1_leagues:
        cat = league.get('t1_category')
        category_count[cat] = category_count.get(cat, 0) + 1
    
    print("\n各类别联赛数量:")
    for cat, count in sorted(category_count.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} 个")
    
    # 3. 获取各联赛的比赛列表
    print(f"\n开始获取 {args.start_date} 之后的比赛...")
    
    t1_match_ids = []
    leagues_with_matches = []
    
    for i, league in enumerate(t1_leagues):
        league_id = league.get('leagueid')
        league_name = league.get('name', 'Unknown')
        category = league.get('t1_category')
        
        print(f"\n[{i+1}/{len(t1_leagues)}] [{category}] {league_name[:40]} (ID: {league_id})")
        
        matches = get_league_matches(league_id, request_count)
        
        if matches:
            # 筛选指定日期之后的比赛
            matches_filtered = filter_matches_by_time(matches, start_timestamp)
            
            if matches_filtered:
                print(f"    ✓ 找到 {len(matches_filtered)} 场比赛 (总共 {len(matches)} 场)")
                for match in matches_filtered:
                    match['league_name'] = league_name
                    match['league_id'] = league_id
                    match['t1_category'] = category
                    t1_match_ids.append(match)
                leagues_with_matches.append({
                    'name': league_name,
                    'id': league_id,
                    'category': category,
                    'match_count': len(matches_filtered)
                })
            else:
                print(f"    - 无 {args.start_date} 之后的比赛")
        else:
            print(f"    - 无比赛数据")
    
    print(f"\n共找到 {len(t1_match_ids)} 场待获取详情的比赛")
    
    # 4. 获取每场比赛的详情（包含 patch 版本号）
    print(f"\n开始获取比赛详情（含版本号）...")
    print(f"预计耗时: {len(t1_match_ids) // 60} 分钟")
    
    start_time = time.time()
    
    for i, match_basic in enumerate(t1_match_ids):
        match_id = match_basic.get('match_id')
        
        # 跳过已处理的比赛
        if match_id in processed_match_ids:
            continue
        
        elapsed = time.time() - start_time
        remaining = len(t1_match_ids) - i
        if i > 0:
            avg_time = elapsed / (i - len(processed_match_ids) + 1) if i > len(processed_match_ids) else 1
            eta = avg_time * remaining
            eta_str = f"剩余 {int(eta//60)}分{int(eta%60)}秒"
        else:
            eta_str = ""
        
        print(f"[{i+1}/{len(t1_match_ids)}] 获取比赛 {match_id} ... {eta_str}", end='')
        
        match_detail = get_match_details(match_id, request_count)
        
        if match_detail:
            # 提取关键信息
            radiant_team = match_detail.get('radiant_team') or {}
            dire_team = match_detail.get('dire_team') or {}
            match_info = {
                'match_id': match_id,
                'start_time': match_detail.get('start_time'),
                'duration': match_detail.get('duration'),
                'patch': match_detail.get('patch'),
                'version': match_detail.get('version'),
                'game_mode': match_detail.get('game_mode'),
                'radiant_win': match_detail.get('radiant_win'),
                'radiant_score': match_detail.get('radiant_score'),
                'dire_score': match_detail.get('dire_score'),
                'radiant_team_id': match_detail.get('radiant_team_id'),
                'radiant_team_name': radiant_team.get('name'),
                'radiant_team_tag': radiant_team.get('tag'),
                'radiant_team_logo': radiant_team.get('logo_url'),
                'dire_team_id': match_detail.get('dire_team_id'),
                'dire_team_name': dire_team.get('name'),
                'dire_team_tag': dire_team.get('tag'),
                'dire_team_logo': dire_team.get('logo_url'),
                'league_id': match_basic.get('league_id'),
                'league_name': match_basic.get('league_name'),
                't1_category': match_basic.get('t1_category'),
                # BP 数据：每场比赛的 ban/pick 序列
                'picks_bans': match_detail.get('picks_bans', []),
                # 玩家英雄数据
                'players': [
                    {
                        'hero_id': p.get('hero_id'),
                        'team_number': p.get('team_number'),
                        'isRadiant': p.get('isRadiant'),
                        'player_slot': p.get('player_slot'),
                    }
                    for p in (match_detail.get('players') or [])
                ],
            }
            all_match_details.append(match_info)
            processed_match_ids.add(match_id)
            
            patch = match_detail.get('patch', 'N/A')
            print(f" patch={patch}")
        else:
            print(f" [失败]")
        
        # 定期保存进度
        if (i + 1) % args.save_interval == 0:
            save_progress({
                'start_date': args.start_date,
                'processed_match_ids': list(processed_match_ids),
                'match_details': all_match_details,
                'leagues': leagues_with_matches
            }, progress_file)
            print(f"    [进度已保存: {len(processed_match_ids)} 场]")
    
    # 5. 保存最终结果
    total_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("统计结果")
    print("=" * 70)
    print(f"总请求次数: {request_count[0]}")
    print(f"总耗时: {int(total_time//60)}分{int(total_time%60)}秒")
    print(f"获取比赛详情: {len(all_match_details)} 场")
    
    if all_match_details:
        # 按 patch 统计
        patch_stats = {}
        for match in all_match_details:
            patch = match.get('patch', 'unknown')
            patch_stats[patch] = patch_stats.get(patch, 0) + 1
        
        print("\n各版本比赛数量:")
        print("-" * 40)
        for patch in sorted(patch_stats.keys(), reverse=True):
            print(f"  patch {patch}: {patch_stats[patch]} 场")
        
        # 按 T1 类别统计
        category_stats = {}
        for match in all_match_details:
            cat = match.get('t1_category', 'unknown')
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        print("\n各 T1 类别比赛数量:")
        print("-" * 40)
        for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} 场")
        
        # 按 版本号/比赛名称 目录结构保存
        print(f"\n按目录结构保存到: {args.data_dir}/")
        save_by_directory(
            matches=all_match_details,
            data_dir=args.data_dir,
            patch_map=patch_map,
            start_date=args.start_date,
            leagues_with_matches=leagues_with_matches,
        )
        
        # 显示最近几场比赛
        all_match_details.sort(key=lambda x: x.get('start_time', 0), reverse=True)
        print(f"\n最近 10 场比赛:")
        print("-" * 70)
        for match in all_match_details[:10]:
            match_time = datetime.fromtimestamp(match.get('start_time', 0))
            patch = match.get('patch', 'N/A')
            category = match.get('t1_category', '')
            radiant = match.get('radiant_team_name') or 'Unknown'
            dire = match.get('dire_team_name') or 'Unknown'
            print(f"  [{match_time.strftime('%Y-%m-%d')}] patch {patch} | {category[:10]:10} | {radiant} vs {dire}")
    else:
        print("\n未找到符合条件的比赛数据")


if __name__ == "__main__":
    main()
