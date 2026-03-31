# Dota 2 BP Helper

基于 T1 职业赛事数据的 Dota 2 Ban/Pick 辅助工具。实时分析当前 Draft 状态，给出数据驱动的 ban 和 pick 建议。

## 功能

- **实时 BP 建议**：每次选择后自动更新，支持我方/对方队伍历史数据加权
- **胜率预测**：基于英雄克制矩阵计算当前阵容预期胜率
- **队伍特化**：可选择具体队伍，建议权重向该队伍历史 pick/ban 倾斜
- **英雄筛选**：按属性、定位、名称搜索快速定位英雄
- **标准 CM 顺序**：内置 20 步 Captain's Mode 流程，自动跟踪当前阶段

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

**Ban 建议**（综合评分）
- 对手历史 pick 率 × 40%
- 全局 ban 率 × 25%
- 全局英雄胜率（贝叶斯平滑）× 20%
- 克制威胁系数 × 15%

**Pick 建议**（综合评分）
- 本队英雄历史胜率（贝叶斯平滑）× 30%
- 与已 pick 英雄协同加成 × 25%
- 被对手克制惩罚 × 25%
- 位置适配动态权重 × 20%

**胜率预测**：我方 vs 对方所有英雄对的历史克制胜率加权均值

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
