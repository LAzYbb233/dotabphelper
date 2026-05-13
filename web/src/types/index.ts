// ─── Hero ───────────────────────────────────────────
export interface Hero {
  id: number;
  name: string;         // "Anti-Mage"
  cn_name?: string;     // "敌法师"
  npc_name: string;     // "antimage" (for CDN img)
  img: string;          // full CDN URL
  primary_attr: 'agi' | 'str' | 'int' | 'all' | '';
  roles: string[];
  // stats
  pick_count: number;
  ban_count: number;
  pick_win: number;
  pick_rate: number;
  ban_rate: number;
  win_rate: number;
  phase_picks: Record<string, number>;
  phase_bans: Record<string, number>;
}

// ─── Team ───────────────────────────────────────────
export interface TeamHeroPick {
  count: number;
  wins: number;
  win_rate: number;
}

export interface Team {
  id: string;
  name: string;
  tag: string;
  logo_url: string;
  total_matches: number;
  wins: number;
  win_rate: number;
  hero_picks: Record<string, TeamHeroPick>;  // hero_id → stats
  hero_bans: Record<string, number>;          // hero_id → count
  hero_against_bans: Record<string, number>;
}

// ─── Draft State ─────────────────────────────────────

// Dota2 职业赛 CM 顺序（7.40 验证，24 步 = 14ban + 10pick）
// A = 先ban方, B = 后ban方
// Phase 1 (0-5):   初始 6 ban  (AA BB A B)
// Phase 2 (6-9):   交替 ban/pick (B[pick AB] A)
// Phase 3 (10-17): 主选阶段 (AA B [pick BA ABBA])
// Phase 4 (18-23): 收尾 4ban + 2pick (ABAB [pick AB])
export function buildCMSequence(firstBanTeam: 'ally' | 'enemy'): DraftSlot[] {
  const A = firstBanTeam;
  const B: 'ally' | 'enemy' = firstBanTeam === 'ally' ? 'enemy' : 'ally';
  return [
    // Phase 1: 初始 6 ban (AA BB A B)
    { order: 0, action: 'ban', team: A },
    { order: 1, action: 'ban', team: A },
    { order: 2, action: 'ban', team: B },
    { order: 3, action: 'ban', team: B },
    { order: 4, action: 'ban', team: A },
    { order: 5, action: 'ban', team: B },
    // Phase 2: 2ban + 2pick 交替 (B pick_A pick_B A)
    { order: 6, action: 'ban', team: B },
    { order: 7, action: 'pick', team: A },
    { order: 8, action: 'pick', team: B },
    { order: 9, action: 'ban', team: A },
    // Phase 3: 2ban + 6pick 主选 (AA B pick_BA pick_ABBA)
    { order: 10, action: 'ban', team: A },
    { order: 11, action: 'ban', team: B },
    { order: 12, action: 'pick', team: B },
    { order: 13, action: 'pick', team: A },
    { order: 14, action: 'pick', team: A },
    { order: 15, action: 'pick', team: B },
    { order: 16, action: 'pick', team: B },
    { order: 17, action: 'pick', team: A },
    // Phase 4: 4ban + 2pick 收尾 (ABAB pick_AB)
    { order: 18, action: 'ban', team: A },
    { order: 19, action: 'ban', team: B },
    { order: 20, action: 'ban', team: A },
    { order: 21, action: 'ban', team: B },
    { order: 22, action: 'pick', team: A },
    { order: 23, action: 'pick', team: B },
    // 合计: 14 ban + 10 pick = 24 步，每队 7 ban + 5 pick
  ];
}

export type DraftAction = DraftSlot;

export interface DraftSlot {
  order: number;
  action: 'ban' | 'pick';
  team: 'ally' | 'enemy';
  hero?: Hero;           // filled once selected
}

// ─── Suggestions ─────────────────────────────────────
export interface HeroSuggestion {
  hero_id: number;
  name: string;
  cn_name?: string;
  npc_name: string;
  img: string;
  score: number;
  reason: {
    global_win_rate?: number;
    enemy_pick_rate?: number;
    own_win_rate?: number;
    synergy_bonus?: number;
    counter_penalty?: number;
    global_pick_rate?: number;
    global_ban_rate?: number;
  };
}

export interface SuggestResponse {
  ban_suggestions: HeroSuggestion[];
  pick_suggestions: HeroSuggestion[];
  win_rate: number;
  drafted_count: number;
}
