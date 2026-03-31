import { useState } from 'react';
import { useBPStore } from '../store/bpStore';
import { WinRateMeter } from './WinRateMeter';
import type { HeroSuggestion } from '../types';

interface Props {
  onHeroClick: (heroId: number) => void;
}

export function SuggestionPanel({ onHeroClick }: Props) {
  const { suggestions, suggestionLoading, activeSlot, currentPhase } = useBPStore();
  const slot = activeSlot();
  const phase = currentPhase();

  const phaseLabels: Record<number, string> = {
    1: 'Ban 阶段 1 (1-6)',
    2: 'Pick 阶段 1 (7-10)',
    3: 'Ban 阶段 2 (11-14)',
    4: 'Pick 阶段 2 (15-20)',
  };

  const isBan = slot?.action === 'ban';
  const winRate = suggestions?.win_rate ?? 0.5;

  const banSuggestions = suggestions?.ban_suggestions ?? [];
  const pickSuggestions = suggestions?.pick_suggestions ?? [];

  return (
    <div style={styles.container}>
      {/* Phase indicator */}
      <div style={styles.phaseRow}>
        <span style={styles.phaseLabel}>
          {phaseLabels[phase]} · {slot ? (slot.team === 'ally' ? '我方' : '对方') + (isBan ? ' BAN' : ' PICK') : '草稿完成'}
        </span>
        <WinRateMeter winRate={winRate} loading={suggestionLoading} />
      </div>

      <div style={styles.columns}>
        {/* Ban suggestions */}
        <SuggestionColumn
          title="⛔ Ban 建议"
          items={banSuggestions}
          loading={suggestionLoading && isBan}
          type="ban"
          onHeroClick={onHeroClick}
        />
        {/* Pick suggestions */}
        <SuggestionColumn
          title="✅ Pick 建议"
          items={pickSuggestions}
          loading={suggestionLoading && !isBan}
          type="pick"
          onHeroClick={onHeroClick}
        />
      </div>
    </div>
  );
}

function SuggestionColumn({
  title, items, loading, type, onHeroClick,
}: {
  title: string;
  items: HeroSuggestion[];
  loading: boolean;
  type: 'ban' | 'pick';
  onHeroClick: (heroId: number) => void;
}) {
  const { draftedHeroIds, isComplete, activeSlot } = useBPStore();
  const drafted = draftedHeroIds();
  const slot = activeSlot();
  const isMyTurn = slot != null && !isComplete;

  return (
    <div style={styles.column}>
      <div style={styles.colHeader}>{title}</div>
      {loading ? (
        <div style={styles.loading}>计算中...</div>
      ) : items.length === 0 ? (
        <div style={styles.empty}>--</div>
      ) : (
        <div style={styles.list}>
          {items.map((item, i) => (
            <SuggestionRow
              key={item.hero_id}
              item={item}
              rank={i + 1}
              type={type}
              clickable={isMyTurn && !drafted.has(item.hero_id)}
              onClick={() => onHeroClick(item.hero_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SuggestionRow({
  item, rank, type, clickable, onClick,
}: {
  item: HeroSuggestion;
  rank: number;
  type: 'ban' | 'pick';
  clickable: boolean;
  onClick: () => void;
}) {
  const [imgErr, setImgErr] = useState(false);
  const accentColor = type === 'ban' ? '#ef4444' : '#22c55e';

  const reasonText = (() => {
    if (type === 'ban') {
      const ep = item.reason.enemy_pick_rate ?? 0;
      const wr = item.reason.global_win_rate ?? 0;
      return `对手pick率 ${(ep * 100).toFixed(0)}% · 全局胜率 ${(wr * 100).toFixed(0)}%`;
    } else {
      const wr = item.reason.own_win_rate ?? 0;
      const syn = item.reason.synergy_bonus ?? 0;
      return `本队胜率 ${(wr * 100).toFixed(0)}% · 协同 ${syn >= 0 ? '+' : ''}${(syn * 100).toFixed(0)}%`;
    }
  })();

  return (
    <div
      style={{
        ...styles.row,
        cursor: clickable ? 'pointer' : 'default',
        background: clickable ? '#0d1117' : '#0a0f1a',
      }}
      onClick={clickable ? onClick : undefined}
      title={clickable ? `快速选择 ${item.name}` : ''}
    >
      <span style={{ ...styles.rank, color: accentColor }}>{rank}</span>
      <img
        src={imgErr
          ? `https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/${item.npc_name}_full.png`
          : item.img}
        alt={item.name}
        style={styles.rowImg}
        onError={() => setImgErr(true)}
        draggable={false}
      />
      <div style={styles.rowInfo}>
        <span style={styles.rowName}>{item.cn_name || item.name}</span>
        <span style={styles.rowReason}>{reasonText}</span>
      </div>
      <span style={{ ...styles.score, color: accentColor }}>
        {(item.score * 100).toFixed(0)}
      </span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    background: '#0a0f1a',
    borderTop: '1px solid #1e293b',
    padding: '8px 12px',
  },
  phaseRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
  },
  phaseLabel: {
    fontSize: 13,
    color: '#94a3b8',
    fontWeight: 600,
    letterSpacing: 0.5,
  },
  columns: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
  },
  column: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  colHeader: {
    fontSize: 12,
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: 1,
    marginBottom: 2,
  },
  loading: {
    color: '#475569',
    fontSize: 12,
    padding: '4px 0',
  },
  empty: {
    color: '#334155',
    fontSize: 12,
    padding: '4px 0',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 6px',
    borderRadius: 4,
    border: '1px solid #1e293b',
    transition: 'background 0.1s',
  },
  rank: {
    fontSize: 13,
    fontWeight: 800,
    minWidth: 18,
    textAlign: 'center',
  },
  rowImg: {
    width: 36,
    height: 20,
    objectFit: 'cover',
    borderRadius: 3,
    flexShrink: 0,
  },
  rowInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
    overflow: 'hidden',
  },
  rowName: {
    fontSize: 12,
    color: '#e2e8f0',
    fontWeight: 600,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  rowReason: {
    fontSize: 10,
    color: '#64748b',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  score: {
    fontSize: 13,
    fontWeight: 700,
    minWidth: 28,
    textAlign: 'right',
  },
};
