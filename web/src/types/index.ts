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

// Dota2 CM 顺序：24 个动作
// Ban Ph1: orders 0-5   (A B A B A B)
// Pick Ph1: orders 6-9  (A B B A)
// Ban Ph2: orders 10-13 (B A B A)
// Pick Ph2: orders 14-23 (B A A B A B)
export const CM_SEQUENCE: Array<{ order: number; action: 'ban' | 'pick'; team: 'ally' | 'enemy' }> = [
  // Ban Phase 1
  { order: 0, action: 'ban', team: 'ally' },
  { order: 1, action: 'ban', team: 'enemy' },
  { order: 2, action: 'ban', team: 'ally' },
  { order: 3, action: 'ban', team: 'enemy' },
  { order: 4, action: 'ban', team: 'ally' },
  { order: 5, action: 'ban', team: 'enemy' },
  // Pick Phase 1
  { order: 6, action: 'pick', team: 'ally' },
  { order: 7, action: 'pick', team: 'enemy' },
  { order: 8, action: 'pick', team: 'enemy' },
  { order: 9, action: 'pick', team: 'ally' },
  // Ban Phase 2
  { order: 10, action: 'ban', team: 'enemy' },
  { order: 11, action: 'ban', team: 'ally' },
  { order: 12, action: 'ban', team: 'enemy' },
  { order: 13, action: 'ban', team: 'ally' },
  // Pick Phase 2
  { order: 14, action: 'pick', team: 'enemy' },
  { order: 15, action: 'pick', team: 'ally' },
  { order: 16, action: 'pick', team: 'ally' },
  { order: 17, action: 'pick', team: 'enemy' },
  { order: 18, action: 'pick', team: 'ally' },
  { order: 19, action: 'pick', team: 'enemy' },
  // Total: 6 bans + 4 picks + 4 bans + 6 picks = 20 actions
  // (some CM variants have 24 — we use standard 20-action CM)
];

export type DraftAction = typeof CM_SEQUENCE[number];

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
