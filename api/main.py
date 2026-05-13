#!/usr/bin/env python3
"""
Dota 2 BP Assistant — FastAPI 后端
启动: uvicorn api.main:app --reload --port 8000
"""

import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ANALYSIS_FILE = DATA_DIR / "bp_analysis.json"

app = FastAPI(title="Dota 2 BP Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 全局数据（启动时加载）───────────────────────────
_analysis: dict = {}


def load_analysis():
    global _analysis
    if not ANALYSIS_FILE.exists():
        print(f"[警告] 分析文件不存在: {ANALYSIS_FILE}")
        print("请先运行: python analysis/bp_analyzer.py")
        _analysis = {"heroes": {}, "teams": {}, "synergy": {}, "counter": {}, "total_matches": 0}
        return
    with open(ANALYSIS_FILE, encoding="utf-8") as f:
        _analysis = json.load(f)
    print(f"[OK] 已加载分析数据: {ANALYSIS_FILE}")
    print(f"     英雄: {len(_analysis.get('heroes', {}))}, 队伍: {len(_analysis.get('teams', {}))}, 比赛: {_analysis.get('total_matches', 0)}")


@app.on_event("startup")
def startup():
    load_analysis()


# ─── 数据模型 ─────────────────────────────────────────

class SuggestRequest(BaseModel):
    ally_team_id: Optional[str] = None
    enemy_team_id: Optional[str] = None
    bans: list[int] = []           # 已 ban 掉的英雄 ID 列表（双方）
    ally_picks: list[int] = []     # 我方已选英雄 ID 列表
    enemy_picks: list[int] = []    # 对方已选英雄 ID 列表
    phase: int = 1                 # 1=初始ban, 2=交替ban/pick, 3=主选, 4=收尾
    is_ban_phase: bool = True      # 当前是否是 ban 阶段
    ally_side: str = 'radiant'     # 'radiant' | 'dire'，用于克制矩阵方向修正


# ─── 置信度常量 ────────────────────────────────────────
# 贝叶斯先验强度：相当于"虚拟样本"数量，样本越少越向 0.5 收缩
BAYES_K_HERO   = 10   # 全局英雄胜率（611场基数，k=10较保守）
BAYES_K_TEAM   = 5    # 队伍专属胜率（样本更少，k=5适中）
BAYES_K_PAIR   = 3    # 协同/克制对（对数多但每对样本少，k=3）
MIN_PAIR_COUNT = 3    # 协同/克制对最小样本（由2提高到3）


def bayesian_win_rate(wins: int, count: int, prior: float = 0.5, k: float = BAYES_K_HERO) -> float:
    """贝叶斯平滑胜率：小样本向先验均值收缩，样本越多越接近真实值。
    例: 3场3胜 → 原始1.00，k=10后 → (3+5)/(3+10) = 0.615
        50场35胜 → 原始0.70，k=10后 → (35+5)/(50+10) = 0.667（基本不变）
    """
    return (wins + k * prior) / (count + k)


# ─── 工具函数 ─────────────────────────────────────────

def get_drafted_set(bans: list, ally_picks: list, enemy_picks: list) -> set:
    return set(str(h) for h in bans + ally_picks + enemy_picks)


def compute_ban_suggestions(
    ally_team_id: Optional[str],
    enemy_team_id: Optional[str],
    drafted: set,
    ally_picks: list[int] = None,
    enemy_picks: list[int] = None,
    phase: int = 1,
    top_n: int = 8,
) -> list:
    """
    Ban 建议（Phase 感知版）：
    Phase 1-2（初始ban / 交替ban）：偏重全局热度和对手习惯
      score = 0.40*enemy_pr + 0.25*ban_rate + 0.20*win_rate + 0.10*counter + 0.05*enemy_syn
    Phase 3-4（后期ban）：偏重反协同和克制威胁
      score = 0.25*enemy_pr + 0.15*ban_rate + 0.15*win_rate + 0.20*counter + 0.25*enemy_syn

    - counter_threat: 该英雄克制我方已选英雄的程度
    - enemy_syn_bonus: 该英雄与对手已选英雄的协同强度（越高越应 ban）
    """
    heroes = _analysis.get("heroes", {})
    teams = _analysis.get("teams", {})
    counter = _analysis.get("counter", {})
    synergy = _analysis.get("synergy", {})
    ally_picks = ally_picks or []
    enemy_picks = enemy_picks or []
    ally_str = [str(h) for h in ally_picks]
    enemy_str = [str(h) for h in enemy_picks]

    enemy_picks_map = {}
    if enemy_team_id and enemy_team_id in teams:
        enemy_tm = teams[enemy_team_id]["total_matches"] or 1
        for hid, v in teams[enemy_team_id]["hero_picks"].items():
            enemy_picks_map[hid] = v["count"] / enemy_tm

    # Phase 权重：前期偏热度，后期偏精准反制
    if phase <= 2:
        w_enemy_pr, w_ban_rate, w_wr, w_ctr, w_enemy_syn = 0.40, 0.25, 0.20, 0.10, 0.05
    else:
        w_enemy_pr, w_ban_rate, w_wr, w_ctr, w_enemy_syn = 0.25, 0.15, 0.15, 0.20, 0.25

    results = []
    for hid, hdata in heroes.items():
        if hid in drafted:
            continue

        # ① 贝叶斯平滑全局胜率
        pc = hdata.get("pick_count", 0)
        pw = hdata.get("pick_win", 0)
        smoothed_wr = bayesian_win_rate(pw, pc, 0.5, BAYES_K_HERO)

        # ② 对手 pick 率
        global_pick_rate = hdata.get("pick_rate", 0)
        global_ban_rate = hdata.get("ban_rate", 0)
        enemy_pr = enemy_picks_map.get(hid, global_pick_rate)

        # ③ 克制威胁：候选英雄克制我方已选英雄（两个方向都检查）
        counter_bonus = 0.0
        ctr_samples = 0
        for ally_h in ally_str:
            key_a = f"{hid}:{ally_h}"
            if key_a in counter and counter[key_a]["count"] >= MIN_PAIR_COUNT:
                threat = bayesian_win_rate(
                    counter[key_a]["hero_a_wins"], counter[key_a]["count"],
                    0.5, BAYES_K_PAIR
                ) - 0.5
                if threat > 0:
                    counter_bonus += threat
                    ctr_samples += 1
            key_b = f"{ally_h}:{hid}"
            if key_b in counter and counter[key_b]["count"] >= MIN_PAIR_COUNT:
                threat = 0.5 - bayesian_win_rate(
                    counter[key_b]["hero_a_wins"], counter[key_b]["count"],
                    0.5, BAYES_K_PAIR
                )
                if threat > 0:
                    counter_bonus += threat
                    ctr_samples += 1
        if ctr_samples:
            counter_bonus /= ctr_samples

        # ④ 对手协同威胁：候选英雄与对手已选英雄的协同程度（越高越危险）
        enemy_syn_bonus = 0.0
        esyn_samples = 0
        for ene_h in enemy_str:
            key = ":".join(sorted([hid, ene_h]))
            if key in synergy and synergy[key]["count"] >= MIN_PAIR_COUNT:
                threat = bayesian_win_rate(
                    synergy[key]["wins"], synergy[key]["count"],
                    0.5, BAYES_K_PAIR
                ) - 0.5
                if threat > 0:
                    enemy_syn_bonus += threat
                    esyn_samples += 1
        if esyn_samples:
            enemy_syn_bonus /= esyn_samples

        score = (w_enemy_pr * enemy_pr
                 + w_ban_rate * global_ban_rate
                 + w_wr * smoothed_wr
                 + w_ctr * (0.5 + counter_bonus)
                 + w_enemy_syn * (0.5 + enemy_syn_bonus))

        results.append({
            "hero_id": int(hid),
            "name": hdata.get("name", ""),
            "cn_name": hdata.get("cn_name", ""),
            "npc_name": hdata.get("npc_name", ""),
            "img": hdata.get("img", ""),
            "score": round(score, 4),
            "reason": {
                "global_win_rate": round(smoothed_wr, 4),
                "enemy_pick_rate": round(enemy_pr, 4),
                "global_pick_rate": global_pick_rate,
                "global_ban_rate": global_ban_rate,
                "pick_count": pc,
                "counter_threat": round(counter_bonus, 4),
                "enemy_synergy_threat": round(enemy_syn_bonus, 4),
            },
        })

    results.sort(key=lambda x: -x["score"])
    return results[:top_n]


def compute_pick_suggestions(
    ally_team_id: Optional[str],
    enemy_team_id: Optional[str],
    drafted: set,
    ally_picks: list[int],
    enemy_picks: list[int],
    phase: int = 1,
    top_n: int = 8,
) -> list:
    """
    Pick 建议（Phase 感知版）：
    Phase 1-2（早期pick）：重视克制惩罚，避免过早暴露针对性
      score = 0.30*own_wr + 0.25*syn_bonus - 0.25*ctr_penalty + position + presence
    Phase 3-4（后期pick）：降低克制惩罚权重，更重视协同加成（针对pick场景）
      score = 0.30*own_wr + 0.30*syn_bonus - 0.15*ctr_penalty + position + presence
    """
    heroes = _analysis.get("heroes", {})
    teams = _analysis.get("teams", {})
    synergy = _analysis.get("synergy", {})
    counter = _analysis.get("counter", {})

    ally_str = [str(h) for h in ally_picks]
    enemy_str = [str(h) for h in enemy_picks]

    # 预取队伍原始数据（用于平滑时引入全局胜率作为先验）
    team_hero_picks = {}
    if ally_team_id and ally_team_id in teams:
        team_hero_picks = teams[ally_team_id]["hero_picks"]

    # 预计算我方已覆盖的位置集合（用于位置适配度评分）
    ally_positions: set = set()
    for ah in ally_str:
        pos = heroes.get(ah, {}).get("primary_position")
        if pos:
            ally_positions.add(pos)

    results = []
    for hid, hdata in heroes.items():
        if hid in drafted:
            continue

        # ① 基础胜率：优先用队伍历史数据，以全局平滑胜率为先验
        global_pc = hdata.get("pick_count", 0)
        global_pw = hdata.get("pick_win", 0)
        global_smoothed = bayesian_win_rate(global_pw, global_pc, 0.5, BAYES_K_HERO)

        if hid in team_hero_picks:
            v = team_hero_picks[hid]
            # 以全局平滑胜率作为队伍数据的先验，避免队伍小样本失真
            own_wr = bayesian_win_rate(v["wins"], v["count"], global_smoothed, BAYES_K_TEAM)
        else:
            own_wr = global_smoothed

        # ② 协同加成：与我方已选英雄的平均协同胜率（贝叶斯平滑，最小样本提高到 3）
        syn_bonus = 0.0
        syn_count = 0
        for ally_h in ally_str:
            key = ":".join(sorted([hid, ally_h]))
            if key in synergy and synergy[key]["count"] >= MIN_PAIR_COUNT:
                smoothed_syn = bayesian_win_rate(
                    synergy[key]["wins"], synergy[key]["count"], 0.5, BAYES_K_PAIR
                )
                syn_bonus += smoothed_syn - 0.5
                syn_count += 1
        if syn_count:
            syn_bonus /= syn_count

        # ③ 克制惩罚：被对方已选英雄克制（贝叶斯平滑，最小样本提高到 3）
        ctr_penalty = 0.0
        ctr_count = 0
        for ene_h in enemy_str:
            key = f"{ene_h}:{hid}"
            if key in counter and counter[key]["count"] >= MIN_PAIR_COUNT:
                smoothed_ctr = bayesian_win_rate(
                    counter[key]["hero_a_wins"], counter[key]["count"], 0.5, BAYES_K_PAIR
                )
                ctr_penalty += smoothed_ctr - 0.5
                ctr_count += 1
        if ctr_count:
            ctr_penalty /= ctr_count

        # ④ 位置适配度：优先填补我方尚未覆盖的位置，惩罚重复位置
        # position_fit: 1.0=填补空缺, 0.5=无位置数据(中性), 0.0=重复已有位置
        hero_pos = hdata.get("primary_position")
        if hero_pos is None:
            position_fit = 0.5
        elif hero_pos in ally_positions:
            position_fit = 0.0
        else:
            position_fit = 1.0

        # 位置权重随 pick 进度动态增长：前期位置不急迫，后期至关重要
        # 0 picks→0.00, 1 pick→0.05, 2→0.10, 3+→0.15
        n_ally = len(ally_picks)
        position_weight = min(0.05 * n_ally, 0.15)

        # ⑤ 版本出场率：pick_rate + ban_rate 越高说明英雄在职业赛越普适
        # 小众/超情境英雄（米波/哈斯卡等）出场率极低，视为高风险早期 pick
        presence = min(hdata.get("pick_rate", 0) + hdata.get("ban_rate", 0), 1.0)
        presence_weight = 0.20 - position_weight  # 两者之和固定 0.20，此消彼长

        # 后期 pick 降低克制惩罚（更倾向于主动针对），提高协同权重
        if phase >= 3:
            syn_w, ctr_w = 0.30, 0.15
        else:
            syn_w, ctr_w = 0.25, 0.25

        score = (0.30 * own_wr
                 + syn_w * (0.5 + syn_bonus)
                 - ctr_w * ctr_penalty
                 + position_weight * position_fit
                 + presence_weight * presence)

        results.append({
            "hero_id": int(hid),
            "name": hdata.get("name", ""),
            "cn_name": hdata.get("cn_name", ""),
            "npc_name": hdata.get("npc_name", ""),
            "img": hdata.get("img", ""),
            "score": round(score, 4),
            "reason": {
                "own_win_rate": round(own_wr, 4),
                "synergy_bonus": round(syn_bonus, 4),
                "counter_penalty": round(ctr_penalty, 4),
                "global_pick_rate": hdata.get("pick_rate", 0),
                "pick_count": global_pc,
                "primary_position": hero_pos,
                "position_fit": position_fit,
                "presence_rate": round(presence, 4),
            },
        })

    results.sort(key=lambda x: -x["score"])
    return results[:top_n]


def predict_win_rate(ally_picks: list[int], enemy_picks: list[int], ally_side: str = 'radiant') -> float:
    """
    基于克制矩阵预测胜率（贝叶斯平滑 + 天辉/夜魇方向修正版）

    counter 数据格式：key = "{radiant_hero}:{dire_hero}", hero_a_wins = radiant 一方的胜数
    - ally_side='radiant': ally 是天辉，key 方向为 ally:enemy，hero_a_wins 即 ally 胜率
    - ally_side='dire':    ally 是夜魇，key 方向为 enemy:ally，ally 胜率 = 1 - hero_a_wins
    """
    if not ally_picks or not enemy_picks:
        return 0.5

    counter = _analysis.get("counter", {})
    scores = []
    for a in ally_picks:
        for e in enemy_picks:
            if ally_side == 'radiant':
                # ally=radiant → key: ally_hero:enemy_hero, hero_a_wins = ally wins
                key_primary = f"{a}:{e}"
                key_fallback = f"{e}:{a}"
                flip = False
            else:
                # ally=dire → key: enemy_hero:ally_hero, ally wins = 1 - hero_a_wins
                key_primary = f"{e}:{a}"
                key_fallback = f"{a}:{e}"
                flip = True

            if key_primary in counter and counter[key_primary]["count"] >= MIN_PAIR_COUNT:
                smoothed = bayesian_win_rate(
                    counter[key_primary]["hero_a_wins"], counter[key_primary]["count"], 0.5, BAYES_K_PAIR
                )
                scores.append(1 - smoothed if flip else smoothed)
            elif key_fallback in counter and counter[key_fallback]["count"] >= MIN_PAIR_COUNT:
                smoothed = bayesian_win_rate(
                    counter[key_fallback]["hero_a_wins"], counter[key_fallback]["count"], 0.5, BAYES_K_PAIR
                )
                scores.append(smoothed if flip else 1 - smoothed)

    return round(sum(scores) / len(scores), 4) if scores else 0.5


# ─── API 路由 ─────────────────────────────────────────

@app.get("/api/heroes")
def get_heroes():
    """获取所有英雄及其统计数据"""
    heroes = _analysis.get("heroes", {})
    return {
        "count": len(heroes),
        "heroes": heroes,
    }


@app.get("/api/teams")
def get_teams():
    """获取所有 T1 队伍及其 BP 统计"""
    teams = _analysis.get("teams", {})
    # 只返回有足够比赛数量的队伍（至少 3 场）
    active_teams = {
        tid: tdata for tid, tdata in teams.items()
        if tdata.get("total_matches", 0) >= 3
    }
    return {
        "count": len(active_teams),
        "teams": active_teams,
    }


@app.post("/api/suggest")
def suggest(req: SuggestRequest):
    """
    实时 BP 建议
    根据当前草稿状态返回 ban/pick 建议和胜率预测
    """
    drafted = get_drafted_set(req.bans, req.ally_picks, req.enemy_picks)

    ban_suggestions = []
    pick_suggestions = []

    if req.is_ban_phase:
        ban_suggestions = compute_ban_suggestions(
            req.ally_team_id, req.enemy_team_id, drafted,
            req.ally_picks, req.enemy_picks, req.phase
        )
    else:
        pick_suggestions = compute_pick_suggestions(
            req.ally_team_id, req.enemy_team_id, drafted,
            req.ally_picks, req.enemy_picks, req.phase
        )

    # 无论阶段，都计算当前预测胜率（使用 ally_side 修正克制方向）
    win_rate = predict_win_rate(req.ally_picks, req.enemy_picks, req.ally_side)

    return {
        "ban_suggestions": ban_suggestions,
        "pick_suggestions": pick_suggestions,
        "win_rate": win_rate,
        "drafted_count": len(drafted),
    }


@app.get("/api/suggest-all")
def suggest_all(
    ally_team_id: Optional[str] = None,
    enemy_team_id: Optional[str] = None,
):
    """获取全局 ban/pick 建议（无当前草稿状态）"""
    return {
        "ban_suggestions": compute_ban_suggestions(ally_team_id, enemy_team_id, set(), [], [], 1),
        "pick_suggestions": compute_pick_suggestions(
            ally_team_id, enemy_team_id, set(), [], [], 1
        ),
        "win_rate": 0.5,
    }


@app.get("/api/hero/{hero_id}/stats")
def hero_stats(hero_id: int):
    """单英雄详细统计"""
    heroes = _analysis.get("heroes", {})
    hid = str(hero_id)
    if hid not in heroes:
        raise HTTPException(status_code=404, detail=f"Hero {hero_id} not found")
    return heroes[hid]


@app.get("/api/team/{team_id}/stats")
def team_stats(team_id: str):
    """单队伍详细 BP 统计"""
    teams = _analysis.get("teams", {})
    if team_id not in teams:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    return teams[team_id]


@app.get("/api/status")
def status():
    """数据状态"""
    return {
        "status": "ok",
        "total_matches": _analysis.get("total_matches", 0),
        "heroes_count": len(_analysis.get("heroes", {})),
        "teams_count": len(_analysis.get("teams", {})),
        "generated_at": _analysis.get("generated_at", "unknown"),
        "source_file": _analysis.get("source_file", "unknown"),
    }


@app.post("/api/reload")
def reload_data():
    """重新加载分析数据（数据更新后调用）"""
    load_analysis()
    return {"status": "reloaded", "total_matches": _analysis.get("total_matches", 0)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
