# Dota 2 BP Helper

基于 T1 职业赛事数据的 Dota 2 Ban/Pick 辅助工具。实时分析当前 Draft 状态，给出数据驱动的 ban 和 pick 建议。

## 功能

- **实时 BP 建议**：每次选择后自动更新，支持我方/对方队伍历史数据加权
- **胜率预测**：基于英雄克制矩阵计算当前阵容预期胜率，支持天辉/夜魇方向修正
- **队伍特化**：可选择具体队伍，建议权重向该队伍历史 pick/ban 倾斜
- **英雄筛选**：按属性、定位、名称搜索快速定位英雄
- **正确 CM 顺序**：内置 24 步职业赛 Captain's Mode 流程（14ban + 10pick），支持先ban方切换
- **Phase 感知评分**：ban/pick 建议权重随阶段动态调整，后期 ban 自动强化反协同策略

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Zustand + Vite |
| 后端 | FastAPI + Uvicorn |
| 数据 | OpenDota API + 自定义分析 Pipeline |

## 项目结构

```
dotabphelper/
├── api/                    # FastAPI 后端
│   └── main.py             # BP 建议算法 + API 端点
├── analysis/
│   └── bp_analyzer.py      # 统计分析（英雄胜率、协同、克制矩阵）
├── script/                 # 数据抓取脚本（OpenDota API）
├── data/                   # 分析输出（bp_analysis.json 等）
├── web/                    # React 前端
│   └── src/
│       ├── components/     # BPBoard / HeroGrid / TeamPanel / SuggestionPanel
│       ├── store/          # Zustand 状态管理
│       └── hooks/          # useSuggestions（防抖请求）
└── config/                 # 英雄 ID 映射 / T1 赛事定义
```

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
cd web && npm install && cd ..
```

### 2. 获取并分析数据

```bash
# 抓取 T1 职业赛事数据（支持断点续传）
python script/fetch_t1_matches_with_patch.py --start-date 2026-01-22

# 生成分析文件
python analysis/bp_analyzer.py
```

### 3. 启动服务

```bash
# 终端 1 — 后端
uvicorn api.main:app --reload --port 8000

# 终端 2 — 前端
cd web && npm run dev
# 访问 http://localhost:5173
```

## 建议算法

**CM Draft 顺序**（职业赛 7.40 实际格式，24 步）

| 阶段 | 步骤 | 动作 | 顺序 |
|------|------|------|------|
| Phase 1 | 0–5   | 初始 6 ban  | AA BB A B |
| Phase 2 | 6–9   | 2ban + 2pick | B pick\_A pick\_B A |
| Phase 3 | 10–17 | 2ban + 6pick | AA B · pick\_BA ABBA |
| Phase 4 | 18–23 | 4ban + 2pick | ABAB · pick\_AB |

A = 先ban方，B = 后ban方，每队各 7 ban + 5 pick。

**Ban 建议**（Phase 感知评分）

| 权重项 | Phase 1–2（初始 ban）| Phase 3–4（后期 ban）|
|--------|---------------------|---------------------|
| 对手历史 pick 率 | 40% | 25% |
| 全局 ban 率 | 25% | 15% |
| 全局英雄胜率 | 20% | 15% |
| 克制我方已选英雄 | 10% | 20% |
| 与对手已选英雄协同 | 5% | 25% |

**Pick 建议**（Phase 感知评分）

| 权重项 | Phase 1–2（早期 pick）| Phase 3–4（后期 pick）|
|--------|----------------------|----------------------|
| 本队英雄历史胜率 | 30% | 30% |
| 与我方协同加成 | 25% | 30% |
| 被对手克制惩罚 | 25% | 15% |
| 位置适配动态权重 | 20% | 25% |

**胜率预测**：我方 vs 对方所有英雄对的历史克制胜率加权均值，根据天辉/夜魇侧别修正克制矩阵方向

> 贝叶斯平滑用于处理小样本偏差（K=10 英雄 / K=5 队伍 / K=3 配对）

## 数据更新

```bash
# 重新抓取（保留进度）
python script/fetch_t1_matches_with_patch.py --resume

# 重新分析
python analysis/bp_analyzer.py

# 热重载（无需重启服务器）
curl -X POST http://localhost:8000/api/reload
```

## 数据来源

比赛数据来自 [OpenDota API](https://api.opendota.com)，仅统计 T1 职业赛事（The International、DreamLeague、PGL、ESL One、Riyadh Masters 等）。
