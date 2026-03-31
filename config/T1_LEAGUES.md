# Dota2 T1 级别赛事列表

> T1 赛事定义：Valve 官方认可的最高级别职业赛事

## T1 赛事分类

| 赛事系列 | 英文名称 | 说明 |
|----------|----------|------|
| **The International** | The International (TI) | Dota2 最高荣誉赛事，年度总决赛 |
| **梦幻联赛** | DreamLeague | DreamHack 主办的顶级联赛 |
| **PGL 系列赛** | PGL Major / Wallachia | PGL 主办的大型赛事 |
| **ESL One** | ESL One | ESL 主办的顶级赛事 |
| **利雅得大师赛** | Riyadh Masters | 沙特举办的高额奖金赛事 |
| **BB 别墅杯** | BetBoom Dacha | BetBoom 主办的邀请赛 |
| **电竞世界杯** | Esports World Cup | 沙特电竞世界杯 Dota2 项目 |



## OpenDota Tier 说明

| Tier | 说明 | 包含赛事 |
|------|------|----------|
| `premium` | 最高级别 | 仅 The International |
| `professional` | 职业级别 | Major、DPC、其他 T1 赛事 |
| `excluded` | 业余/小型 | 非职业赛事 |

---

## API 获取方式

```bash
# 获取联赛列表
curl https://api.opendota.com/api/leagues

# 获取指定联赛比赛
curl https://api.opendota.com/api/leagues/{league_id}/matches

# 获取比赛详情
curl https://api.opendota.com/api/matches/{match_id}
```

**限制**: 每分钟 60 次请求
