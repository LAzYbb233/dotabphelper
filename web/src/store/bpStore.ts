import { create } from 'zustand';
import { CM_SEQUENCE } from '../types';
import type { Hero, Team, DraftSlot, SuggestResponse } from '../types';

export interface BPStore {
  // ─── Data ───────────────────────────────
  heroes: Record<string, Hero>;
  teams: Record<string, Team>;
  heroesLoaded: boolean;
  teamsLoaded: boolean;
  apiError: string | null;

  // ─── Draft State ─────────────────────────
  allyTeamId: string | null;
  enemyTeamId: string | null;
  slots: DraftSlot[];       // 20 slots in CM order
  currentOrder: number;     // 0-19, which slot is active
  isComplete: boolean;

  // ─── Suggestions ─────────────────────────
  suggestions: SuggestResponse | null;
  suggestionLoading: boolean;

  // ─── Actions ─────────────────────────────
  setHeroes: (heroes: Record<string, Hero>) => void;
  setTeams: (teams: Record<string, Team>) => void;
  setApiError: (err: string | null) => void;
  setAllyTeam: (teamId: string | null) => void;
  setEnemyTeam: (teamId: string | null) => void;
  assignHero: (hero: Hero) => void;   // assign to current active slot
  undoLast: () => void;
  resetDraft: () => void;
  setSuggestions: (s: SuggestResponse | null) => void;
  setSuggestionLoading: (v: boolean) => void;

  // ─── Derived helpers ─────────────────────
  draftedHeroIds: () => Set<number>;
  activeSlot: () => DraftSlot | null;
  allyBans: () => Hero[];
  enemyBans: () => Hero[];
  allyPicks: () => Hero[];
  enemyPicks: () => Hero[];
  allyPickIds: () => number[];
  enemyPickIds: () => number[];
  banIds: () => number[];
  currentPhase: () => number;
  isAllyTurn: () => boolean;
}

const initialSlots = (): DraftSlot[] =>
  CM_SEQUENCE.map((s) => ({ ...s }));

export const useBPStore = create<BPStore>((set, get) => ({
  heroes: {},
  teams: {},
  heroesLoaded: false,
  teamsLoaded: false,
  apiError: null,

  allyTeamId: null,
  enemyTeamId: null,
  slots: initialSlots(),
  currentOrder: 0,
  isComplete: false,

  suggestions: null,
  suggestionLoading: false,

  setHeroes: (heroes) => set({ heroes, heroesLoaded: true }),
  setTeams: (teams) => set({ teams, teamsLoaded: true }),
  setApiError: (apiError) => set({ apiError }),
  setAllyTeam: (allyTeamId) => set({ allyTeamId }),
  setEnemyTeam: (enemyTeamId) => set({ enemyTeamId }),

  assignHero: (hero) => {
    const { slots, currentOrder, isComplete } = get();
    if (isComplete || currentOrder >= CM_SEQUENCE.length) return;
    const newSlots = slots.map((s) =>
      s.order === currentOrder ? { ...s, hero } : s
    );
    const nextOrder = currentOrder + 1;
    set({
      slots: newSlots,
      currentOrder: nextOrder,
      isComplete: nextOrder >= CM_SEQUENCE.length,
    });
  },

  undoLast: () => {
    const { currentOrder, slots } = get();
    if (currentOrder <= 0) return;
    const prevOrder = currentOrder - 1;
    const newSlots = slots.map((s) =>
      s.order === prevOrder ? { ...s, hero: undefined } : s
    );
    set({ slots: newSlots, currentOrder: prevOrder, isComplete: false, suggestions: null });
  },

  resetDraft: () => {
    set({
      slots: initialSlots(),
      currentOrder: 0,
      isComplete: false,
      suggestions: null,
    });
  },

  setSuggestions: (suggestions) => set({ suggestions }),
  setSuggestionLoading: (suggestionLoading) => set({ suggestionLoading }),

  // ─── Derived ───────────────────────────────
  draftedHeroIds: () => {
    const ids = new Set<number>();
    for (const s of get().slots) {
      if (s.hero) ids.add(s.hero.id);
    }
    return ids;
  },

  activeSlot: () => {
    const { currentOrder, slots, isComplete } = get();
    if (isComplete) return null;
    return slots.find((s) => s.order === currentOrder) ?? null;
  },

  allyBans: () =>
    get().slots
      .filter((s) => s.action === 'ban' && s.team === 'ally' && s.hero)
      .map((s) => s.hero!),

  enemyBans: () =>
    get().slots
      .filter((s) => s.action === 'ban' && s.team === 'enemy' && s.hero)
      .map((s) => s.hero!),

  allyPicks: () =>
    get().slots
      .filter((s) => s.action === 'pick' && s.team === 'ally' && s.hero)
      .map((s) => s.hero!),

  enemyPicks: () =>
    get().slots
      .filter((s) => s.action === 'pick' && s.team === 'enemy' && s.hero)
      .map((s) => s.hero!),

  allyPickIds: () => get().allyPicks().map((h) => h.id),
  enemyPickIds: () => get().enemyPicks().map((h) => h.id),

  banIds: () => {
    const ids: number[] = [];
    for (const s of get().slots) {
      if (s.action === 'ban' && s.hero) ids.push(s.hero.id);
    }
    return ids;
  },

  currentPhase: () => {
    const order = get().currentOrder;
    if (order <= 5) return 1;
    if (order <= 9) return 2;
    if (order <= 13) return 3;
    return 4;
  },

  isAllyTurn: () => {
    const slot = get().activeSlot();
    return slot?.team === 'ally';
  },
}));
