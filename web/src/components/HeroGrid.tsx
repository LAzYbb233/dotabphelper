import { useState, useMemo, useRef, useEffect } from 'react';
import { useBPStore } from '../store/bpStore';
import type { Hero } from '../types';

const ROLES = ['Carry', 'Support', 'Nuker', 'Disabler', 'Jungler', 'Durable', 'Escape', 'Pusher', 'Initiator'];
const ATTRS = [
  { value: '', label: '全部' },
  { value: 'agi', label: '敏捷' },
  { value: 'str', label: '力量' },
  { value: 'int', label: '智力' },
  { value: 'all', label: '万能' },
];

const GAP = 3;
const NAME_H = 16; // 英雄名标签高度
const ASPECT = 4 / 3; // 头像高/宽比

/** 根据容器尺寸和英雄数量，计算让所有卡片恰好铺满容器的最优列数 */
function calcOptimalCols(w: number, h: number, n: number): number {
  if (n === 0 || w === 0 || h === 0) return 10;
  let bestCols = 1;
  for (let cols = 1; cols <= n; cols++) {
    const rows = Math.ceil(n / cols);
    const cellW = (w - (cols - 1) * GAP) / cols;
    const cellH = cellW * ASPECT + NAME_H;
    const totalH = rows * cellH + (rows - 1) * GAP;
    if (totalH <= h) {
      bestCols = cols;
      break; // 找到能放下的最少列数（= 最大格子）
    }
  }
  return bestCols;
}

interface Props {
  onHeroClick: (hero: Hero) => void;
}

export function HeroGrid({ onHeroClick }: Props) {
  const { heroes, draftedHeroIds, isComplete } = useBPStore();
  const drafted = draftedHeroIds();

  const [search, setSearch] = useState('');
  const [attrFilter, setAttrFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });
  const gridRef = useRef<HTMLDivElement>(null);

  // 监听容器尺寸变化
  useEffect(() => {
    const el = gridRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setContainerSize({ w: width, h: height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const heroList = useMemo(() => {
    return Object.values(heroes)
      .filter((h) => {
        const q = search.toLowerCase();
        if (q && !h.name.toLowerCase().includes(q) && !(h.cn_name ?? '').includes(q)) return false;
        if (attrFilter && h.primary_attr !== attrFilter) return false;
        if (roleFilter && !h.roles.includes(roleFilter)) return false;
        return true;
      })
      .sort((a, b) => b.ban_rate + b.pick_rate - a.ban_rate - a.pick_rate);
  }, [heroes, search, attrFilter, roleFilter]);

  const cols = calcOptimalCols(containerSize.w, containerSize.h, heroList.length);

  return (
    <div style={styles.container}>
      {/* Filters */}
      <div style={styles.filters}>
        <input
          style={styles.search}
          placeholder="搜索英雄..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div style={styles.attrBtns}>
          {ATTRS.map((a) => (
            <button
              key={a.value}
              style={{ ...styles.filterBtn, ...(attrFilter === a.value ? styles.filterBtnActive : {}) }}
              onClick={() => setAttrFilter(attrFilter === a.value ? '' : a.value)}
            >
              {a.label}
            </button>
          ))}
        </div>
        <select
          style={styles.roleSelect}
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
        >
          <option value="">全部定位</option>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* Hero Grid — 充满剩余空间，不滚动 */}
      <div
        ref={gridRef}
        style={{
          ...styles.grid,
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
        }}
      >
        {heroList.map((hero) => {
          const isDrafted = drafted.has(hero.id);
          return (
            <HeroCard
              key={hero.id}
              hero={hero}
              isDrafted={isDrafted}
              disabled={isDrafted || isComplete}
              onClick={() => !isDrafted && !isComplete && onHeroClick(hero)}
            />
          );
        })}
      </div>
    </div>
  );
}

function HeroCard({
  hero, isDrafted, disabled, onClick,
}: {
  hero: Hero;
  isDrafted: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const [imgErr, setImgErr] = useState(false);
  const portraitUrl = `https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/portraits/${hero.npc_name}.png`;
  const fallback = `https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/${hero.npc_name}_full.png`;

  return (
    <div
      style={{
        ...styles.card,
        opacity: isDrafted ? 0.3 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        filter: isDrafted ? 'grayscale(100%)' : 'none',
      }}
      onClick={onClick}
      title={`${hero.name}${hero.cn_name ? ' / ' + hero.cn_name : ''} | 胜率 ${(hero.win_rate * 100).toFixed(0)}% | pick率 ${(hero.pick_rate * 100).toFixed(1)}%`}
    >
      <img
        src={imgErr ? fallback : portraitUrl}
        alt={hero.name}
        style={styles.cardImg}
        onError={() => setImgErr(true)}
        draggable={false}
      />
      <div style={styles.cardName}>{hero.cn_name || hero.name}</div>
      {hero.win_rate > 0 && (
        <div style={{
          ...styles.cardWr,
          color: hero.win_rate >= 0.55 ? '#4ade80' : hero.win_rate <= 0.45 ? '#f87171' : '#fbbf24',
        }}>
          {(hero.win_rate * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    height: '100%',
    overflow: 'hidden',
  },
  filters: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    padding: '4px 0',
    flexShrink: 0,
  },
  search: {
    background: '#1a2030',
    border: '1px solid #334155',
    borderRadius: 4,
    color: '#e2e8f0',
    padding: '4px 10px',
    fontSize: 13,
    width: 140,
    outline: 'none',
  },
  attrBtns: {
    display: 'flex',
    gap: 4,
  },
  filterBtn: {
    background: '#1a2030',
    border: '1px solid #334155',
    borderRadius: 4,
    color: '#94a3b8',
    padding: '3px 8px',
    fontSize: 12,
    cursor: 'pointer',
  },
  filterBtnActive: {
    background: '#1e40af',
    border: '1px solid #3b82f6',
    color: '#e0f2fe',
  },
  roleSelect: {
    background: '#1a2030',
    border: '1px solid #334155',
    borderRadius: 4,
    color: '#94a3b8',
    padding: '3px 8px',
    fontSize: 12,
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gap: GAP,
    flex: 1,
    overflow: 'hidden',  // 不滚动，全部铺满
    alignContent: 'start',
  },
  card: {
    position: 'relative',
    borderRadius: 4,
    overflow: 'hidden',
    border: '1px solid #1e293b',
    transition: 'opacity 0.15s',
    userSelect: 'none',
  },
  cardImg: {
    width: '100%',
    aspectRatio: '3/4',
    display: 'block',
    objectFit: 'cover',
    objectPosition: 'center top',
  },
  cardName: {
    fontSize: 9,
    color: '#cbd5e1',
    textAlign: 'center',
    padding: '1px 2px',
    background: 'rgba(0,0,0,0.75)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    height: NAME_H,
    lineHeight: `${NAME_H}px`,
  },
  cardWr: {
    position: 'absolute',
    top: 2,
    right: 3,
    fontSize: 9,
    fontWeight: 700,
    textShadow: '0 0 3px rgba(0,0,0,0.9)',
  },
};
