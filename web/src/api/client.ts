import axios from 'axios';
import type { Hero, Team, SuggestResponse } from '../types';

const BASE = 'http://localhost:8000/api';

const api = axios.create({ baseURL: BASE, timeout: 5000 });

export interface SuggestPayload {
  ally_team_id?: string;
  enemy_team_id?: string;
  bans: number[];
  ally_picks: number[];
  enemy_picks: number[];
  phase: number;
  is_ban_phase: boolean;
  ally_side?: string;  // 'radiant' | 'dire'，用于克制矩阵方向修正
}

export async function fetchHeroes(): Promise<Record<string, Hero>> {
  const res = await api.get<{ heroes: Record<string, Hero> }>('/heroes');
  // Attach numeric id from the key
  const out: Record<string, Hero> = {};
  for (const [hid, hdata] of Object.entries(res.data.heroes)) {
    out[hid] = { ...hdata, id: parseInt(hid) };
  }
  return out;
}

export async function fetchTeams(): Promise<Record<string, Team>> {
  const res = await api.get<{ teams: Record<string, Team> }>('/teams');
  const out: Record<string, Team> = {};
  for (const [tid, tdata] of Object.entries(res.data.teams)) {
    out[tid] = { ...tdata, id: tid };
  }
  return out;
}

export async function fetchSuggestions(payload: SuggestPayload): Promise<SuggestResponse> {
  const res = await api.post<SuggestResponse>('/suggest', payload);
  return res.data;
}

export async function fetchStatus() {
  const res = await api.get('/status');
  return res.data;
}
