import { useEffect, useRef } from 'react';
import { useBPStore } from '../store/bpStore';
import { fetchSuggestions } from '../api/client';

const DEBOUNCE_MS = 400;

/**
 * 每当 BP 状态变化时，debounce 请求建议
 */
export function useSuggestions() {
  const {
    allyTeamId, enemyTeamId,
    allyPickIds, enemyPickIds, banIds,
    currentPhase, activeSlot,
    setSuggestions, setSuggestionLoading,
    heroesLoaded, isComplete,
  } = useBPStore();

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentOrder = useBPStore((s) => s.currentOrder);

  useEffect(() => {
    if (!heroesLoaded) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      setSuggestionLoading(true);
      const slot = activeSlot();
      const isBanPhase = slot?.action === 'ban';
      const phase = currentPhase();

      try {
        const res = await fetchSuggestions({
          ally_team_id: allyTeamId ?? undefined,
          enemy_team_id: enemyTeamId ?? undefined,
          bans: banIds(),
          ally_picks: allyPickIds(),
          enemy_picks: enemyPickIds(),
          phase,
          is_ban_phase: isBanPhase ?? true,
        });
        setSuggestions(res);
      } catch {
        // silently ignore network errors during BP
        setSuggestions(null);
      } finally {
        setSuggestionLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [currentOrder, allyTeamId, enemyTeamId, heroesLoaded]);
}
