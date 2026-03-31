import { useState } from 'react';
import { useBPStore } from '../store/bpStore';
import type { Hero } from '../types';

interface Props {
  side: 'ally' | 'enemy';
}

export function TeamPanel({ side }: Props) {
  const {
    allyTeamId, enemyTeamId, teams, setAllyTeam, setEnemyTeam,
    activeSlot, slots, currentOrder,
  } = useBPStore();

  const teamId = side === 'ally' ? allyTeamId : enemyTeamId;
  const setTeam = side === 'ally' ? setAllyTeam : setEnemyTeam;
  const teamList = Object.values(teams).sort((a, b) =>
    b.total_matches - a.total_matches
  );

  const currentSlot = activeSlot();
  const isMyTurn = currentSlot?.team === side;

  const label = side === 'ally' ? '我方' : '对方';
  const accentColor = side === 'ally' ? '#2563eb' : '#dc2626';
  const selectedTeam = teamId ? teams[teamId] : null;

  return (
    <div style={{ ...styles.panel, borderColor: isMyTurn ? accentColor : '#1e293b' }}>
      {/* Header */}
      <div style={{ ...styles.header, background: accentColor + '22' }}>
        <div style={{ ...styles.turnIndicator, background: isMyTurn ? accentColor : 'transparent' }}>
          {isMyTurn ? '▶ 选择中' : label}
        </div>
        {selectedTeam?.logo_url && (
          <img src={selectedTeam.logo_url} alt="" style={styles.teamLogo} />
        )}
      </div>

      {/* Team selector */}
      <select
        style={styles.teamSelect}
        value={teamId ?? ''}
        onChange={(e) => setTeam(e.target.value || null)}
      >
        <option value="">-- 选择队伍 --</option>
        {teamList.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} ({t.total_matches}场)
          </option>
        ))}
      </select>

      {/* Ban slots */}
      <div style={styles.sectionLabel}>BAN</div>
      <div style={styles.banGrid}>
        {slots
          .filter((s) => s.action === 'ban' && s.team === side)
          .map((s) => (
            <DraftSlotCard
              key={s.order}
              hero={s.hero}
              isActive={s.order === currentOrder}
              action="ban"
              side={side}
            />
          ))}
      </div>

      {/* Pick slots */}
      <div style={styles.sectionLabel}>PICK</div>
      <div style={styles.pickList}>
        {slots
          .filter((s) => s.action === 'pick' && s.team === side)
          .map((s) => (
            <DraftSlotCard
              key={s.order}
              hero={s.hero}
              isActive={s.order === currentOrder}
              action="pick"
              side={side}
            />
          ))}
      </div>

      {/* Team stats */}
      {selectedTeam && (
        <TeamStats team={selectedTeam} />
      )}
    </div>
  );
}

function DraftSlotCard({
  hero, isActive, action, side,
}: {
  hero?: Hero;
  isActive: boolean;
  action: 'ban' | 'pick';
  side: 'ally' | 'enemy';
}) {
  const [imgErr, setImgErr] = useState(false);
  const accentColor = side === 'ally' ? '#2563eb' : '#dc2626';
  const emptyBg = action === 'ban' ? '#1a1a2e' : '#0f172a';

  return (
    <div style={{
      ...styles.slot,
      background: hero ? 'transparent' : emptyBg,
      border: isActive
        ? `2px solid ${accentColor}`
        : `1px solid ${hero ? '#334155' : '#1e293b'}`,
      boxShadow: isActive ? `0 0 10px ${accentColor}88` : 'none',
    }}>
      {hero ? (
        <>
          <img
            src={imgErr
              ? `https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/${hero.npc_name}_full.png`
              : hero.img}
            alt={hero.name}
            style={{
              ...styles.slotImg,
              filter: action === 'ban' ? 'grayscale(80%) brightness(0.6)' : 'none',
            }}
            onError={() => setImgErr(true)}
            draggable={false}
          />
          {action === 'ban' && (
            <div style={styles.banX}>✕</div>
          )}
          <div style={styles.slotName}>{hero.cn_name || hero.name}</div>
        </>
      ) : (
        <div style={styles.emptySlot}>
          {isActive ? '?' : ''}
        </div>
      )}
    </div>
  );
}

function TeamStats({ team }: { team: { total_matches: number; wins: number; win_rate: number } }) {
  return (
    <div style={styles.teamStats}>
      <span style={{ color: '#64748b', fontSize: 11 }}>
        {team.total_matches} 场 · {(team.win_rate * 100).toFixed(0)}% 胜率
      </span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    padding: 8,
    background: '#0d1117',
    border: '1px solid #1e293b',
    borderRadius: 6,
    transition: 'border-color 0.2s',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 6px',
    borderRadius: 4,
  },
  turnIndicator: {
    padding: '3px 10px',
    borderRadius: 4,
    fontSize: 13,
    fontWeight: 700,
    color: '#e2e8f0',
    letterSpacing: 1,
    transition: 'background 0.2s',
  },
  teamLogo: {
    width: 28,
    height: 28,
    objectFit: 'contain',
    borderRadius: 4,
  },
  teamSelect: {
    background: '#1a2030',
    border: '1px solid #334155',
    borderRadius: 4,
    color: '#e2e8f0',
    padding: '4px 8px',
    fontSize: 12,
    width: '100%',
    cursor: 'pointer',
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 2,
    color: '#475569',
    marginBottom: -4,
  },
  banGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 4,
  },
  pickList: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: 4,
  },
  slot: {
    position: 'relative',
    borderRadius: 4,
    overflow: 'hidden',
    transition: 'border-color 0.15s, box-shadow 0.15s',
    aspectRatio: '16/9',
  },
  slotImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: 'block',
  },
  slotName: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    fontSize: 9,
    color: '#e2e8f0',
    background: 'rgba(0,0,0,0.7)',
    textAlign: 'center',
    padding: '1px 2px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  banX: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: '#ef4444',
    fontSize: 18,
    fontWeight: 900,
    textShadow: '0 0 6px rgba(0,0,0,0.8)',
    zIndex: 1,
  },
  emptySlot: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#334155',
    fontSize: 16,
    fontWeight: 700,
  },
  teamStats: {
    padding: '2px 0',
    borderTop: '1px solid #1e293b',
    textAlign: 'center',
  },
};
