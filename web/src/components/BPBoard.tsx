import { useEffect } from 'react';
import { useBPStore } from '../store/bpStore';
import { fetchHeroes, fetchTeams } from '../api/client';
import { useSuggestions } from '../hooks/useSuggestions';
import { HeroGrid } from './HeroGrid';
import { TeamPanel } from './TeamPanel';
import { SuggestionPanel } from './SuggestionPanel';
import type { Hero } from '../types';

export function BPBoard() {
  const {
    setHeroes, setTeams, setApiError,
    heroes, heroesLoaded,
    assignHero, undoLast, resetDraft,
    activeSlot, isComplete, currentOrder,
    apiError,
    firstBanSide, setFirstBanSide,
    allySide, setAllySide,
  } = useBPStore();

  // Load data on mount
  useEffect(() => {
    Promise.all([fetchHeroes(), fetchTeams()])
      .then(([heroData, teamData]) => {
        setHeroes(heroData);
        setTeams(teamData);
        setApiError(null);
      })
      .catch(() => {
        setApiError('无法连接后端 API。请确认: uvicorn api.main:app --reload --port 8000');
      });
  }, []);

  // Start suggestions hook
  useSuggestions();

  const handleHeroClick = (hero: Hero) => {
    const slot = activeSlot();
    if (!slot || isComplete) return;
    assignHero(hero);
  };

  const handleSuggestionHeroClick = (heroId: number) => {
    const hero = Object.values(heroes).find((h) => h.id === heroId);
    if (hero) handleHeroClick(hero);
  };

  const phase = useBPStore((s) => s.currentPhase());
  const slot = activeSlot();
  const phaseNames = ['', '初始 Ban (1-6)', 'Ban/Pick 交替 (7-10)', '主选阶段 (11-18)', '收尾 Ban+Pick (19-24)'];

  return (
    <div style={styles.root}>
      {/* Title bar */}
      <div style={styles.titleBar}>
        <span style={styles.title}>DOTA 2 BP ASSISTANT</span>
        <div style={styles.statusRow}>
          {apiError ? (
            <span style={styles.errorBadge}>⚠ {apiError}</span>
          ) : !heroesLoaded ? (
            <span style={styles.loadingBadge}>正在加载数据...</span>
          ) : isComplete ? (
            <span style={styles.completeBadge}>✓ 草稿完成</span>
          ) : (
            <span style={styles.phaseBadge}>
              {slot && `${phaseNames[phase]} · 第 ${currentOrder + 1}/24 步`}
            </span>
          )}
        </div>
        <div style={styles.controls}>
          {/* 先ban方选择 */}
          <div style={styles.btnGroup}>
            <button
              style={{ ...styles.btn, ...(firstBanSide === 'ally' ? styles.btnActive : {}) }}
              onClick={() => setFirstBanSide('ally')}
              title="我方先Ban"
            >我方先Ban</button>
            <button
              style={{ ...styles.btn, ...(firstBanSide === 'enemy' ? styles.btnActive : {}) }}
              onClick={() => setFirstBanSide('enemy')}
              title="对方先Ban"
            >对方先Ban</button>
          </div>
          {/* 天辉/夜魇 */}
          <div style={styles.btnGroup}>
            <button
              style={{ ...styles.btn, ...(allySide === 'radiant' ? styles.btnRadiant : {}) }}
              onClick={() => setAllySide('radiant')}
              title="我方是天辉"
            >☀ 天辉</button>
            <button
              style={{ ...styles.btn, ...(allySide === 'dire' ? styles.btnDire : {}) }}
              onClick={() => setAllySide('dire')}
              title="我方是夜魇"
            >☽ 夜魇</button>
          </div>
          <button style={styles.btn} onClick={undoLast} title="撤销上一步">↩ 撤销</button>
          <button style={{ ...styles.btn, ...styles.btnDanger }} onClick={resetDraft} title="重置草稿">↺ 重置</button>
        </div>
      </div>

      {/* Main area */}
      <div style={styles.main}>
        {/* Ally panel */}
        <div style={styles.sidePanel}>
          <TeamPanel side="ally" />
        </div>

        {/* Center: hero grid */}
        <div style={styles.center}>
          {apiError ? (
            <div style={styles.errorCard}>
              <div style={{ fontSize: 32 }}>🔌</div>
              <div style={{ color: '#f87171', fontWeight: 700 }}>后端未连接</div>
              <div style={{ color: '#64748b', fontSize: 13, marginTop: 8 }}>
                请在项目根目录运行:
              </div>
              <code style={styles.code}>
                uvicorn api.main:app --reload --port 8000
              </code>
              <div style={{ color: '#64748b', fontSize: 12, marginTop: 8 }}>
                如尚未生成分析数据，先运行:
                <br />
                python script/fetch_t1_matches_with_patch.py --output data/t1_matches_740c.json
                <br />
                python analysis/bp_analyzer.py
              </div>
            </div>
          ) : !heroesLoaded ? (
            <div style={styles.loadingCard}>
              <div style={{ fontSize: 32 }}>⚔</div>
              <div>正在加载英雄数据...</div>
            </div>
          ) : (
            <HeroGrid onHeroClick={handleHeroClick} />
          )}
        </div>

        {/* Enemy panel */}
        <div style={styles.sidePanel}>
          <TeamPanel side="enemy" />
        </div>
      </div>

      {/* Suggestion panel */}
      <SuggestionPanel onHeroClick={handleSuggestionHeroClick} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#060b14',
    color: '#e2e8f0',
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    overflow: 'hidden',
  },
  titleBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 16px',
    background: '#0d1117',
    borderBottom: '1px solid #1e293b',
    gap: 12,
    flexShrink: 0,
  },
  title: {
    fontSize: 16,
    fontWeight: 800,
    letterSpacing: 3,
    color: '#7dd3fc',
    textTransform: 'uppercase',
  },
  statusRow: {
    flex: 1,
    textAlign: 'center',
  },
  errorBadge: {
    color: '#f87171',
    fontSize: 12,
    background: '#7f1d1d33',
    padding: '3px 10px',
    borderRadius: 4,
    border: '1px solid #7f1d1d',
  },
  loadingBadge: {
    color: '#94a3b8',
    fontSize: 12,
  },
  completeBadge: {
    color: '#4ade80',
    fontSize: 13,
    fontWeight: 700,
  },
  phaseBadge: {
    color: '#7dd3fc',
    fontSize: 13,
    fontWeight: 600,
  },
  controls: {
    display: 'flex',
    gap: 6,
    alignItems: 'center',
  },
  btnGroup: {
    display: 'flex',
    gap: 0,
    borderRadius: 4,
    overflow: 'hidden',
  },
  btnActive: {
    background: '#1e40af',
    border: '1px solid #3b82f6',
    color: '#e0f2fe',
  },
  btnRadiant: {
    background: '#78350f',
    border: '1px solid #d97706',
    color: '#fde68a',
  },
  btnDire: {
    background: '#3b0764',
    border: '1px solid #7c3aed',
    color: '#ddd6fe',
  },
  btn: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 4,
    color: '#cbd5e1',
    padding: '4px 12px',
    fontSize: 12,
    cursor: 'pointer',
    fontWeight: 600,
  },
  btnDanger: {
    background: '#450a0a',
    border: '1px solid #7f1d1d',
    color: '#fca5a5',
  },
  main: {
    display: 'grid',
    gridTemplateColumns: '260px 1fr 260px',
    gap: 8,
    padding: 8,
    flex: 1,
    minHeight: 0,
    alignItems: 'start',
    overflow: 'hidden',
  },
  sidePanel: {
    overflow: 'hidden',
    maxHeight: '100%',
  },
  center: {
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    alignSelf: 'stretch',
    minHeight: 0,
  },
  errorCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 8,
    color: '#94a3b8',
    textAlign: 'center',
  },
  loadingCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 12,
    color: '#64748b',
    fontSize: 16,
  },
  code: {
    background: '#1a2030',
    border: '1px solid #334155',
    borderRadius: 4,
    padding: '6px 12px',
    fontSize: 12,
    color: '#7dd3fc',
    fontFamily: 'monospace',
    marginTop: 4,
    display: 'block',
  },
};
