# Dota 2 BP Assistant — 快速启动

## 1. 安装依赖

```bash
pip install -r requirements.txt
cd web && npm install && cd ..
```

## 2. 获取数据（7.40c 版本，约需几十分钟）

```bash
python script/fetch_t1_matches_with_patch.py \
  --start-date 2026-01-22 \
  --output data/t1_matches_740c.json
```

> API 速率：~55 次/分钟（1秒/次），约 200-300 场比赛预计 4-5 分钟。
> 支持断点续传：加 `--resume` 参数。

## 3. 分析数据

```bash
python analysis/bp_analyzer.py
# 输出: data/bp_analysis.json
```

## 4. 启动后端（终端 1）

```bash
uvicorn api.main:app --reload --port 8000
```

## 5. 启动前端（终端 2）

```bash
cd web
npm run dev
# 打开 http://localhost:5173
```

---

## 功能说明

- **左侧**：我方队伍 — 选择队伍、查看 ban/pick 槽位
- **中间**：英雄选择区 — 支持搜索、属性/定位筛选，点击选中
- **右侧**：对方队伍
- **底部**：实时建议（每次 ban/pick 后自动更新）+ 胜率预测

### BP 顺序（标准 CM 模式，20 步）

```
Ban 阶段 1：A B A B A B（6 ban）
Pick 阶段 1：A B B A（4 pick）
Ban 阶段 2：B A B A（4 ban）
Pick 阶段 2：B A A B A B（6 pick）
```

### 建议算法

**Ban 建议** = 对手历史 pick 率 × 0.6 + 全局英雄胜率 × 0.4

**Pick 建议** = 本队英雄胜率 × 0.4 + 与已选英雄协同 × 0.3 − 被对手克制惩罚 × 0.3

**胜率预测** = 基于克制矩阵，我方 vs 对方所有英雄对的历史胜率均值

---

## 数据更新

```bash
# 重新获取最新数据（保留旧进度）
python script/fetch_t1_matches_with_patch.py --resume --output data/t1_matches_740c.json

# 重新分析
python analysis/bp_analyzer.py

# 通知 API 重载数据（无需重启服务器）
curl -X POST http://localhost:8000/api/reload
```
