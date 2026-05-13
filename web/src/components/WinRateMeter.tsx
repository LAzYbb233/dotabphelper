interface Props {
  winRate: number;   // 0-1, ally win rate
  loading?: boolean;
  hasData?: boolean; // false = picks 数量不足，显示占位而非实际数值
}

export function WinRateMeter({ winRate, loading, hasData = true }: Props) {
  const pct = Math.round(winRate * 100);
  const barWidth = `${pct}%`;

  const color = winRate >= 0.6
    ? '#22c55e'
    : winRate >= 0.55
    ? '#86efac'
    : winRate <= 0.4
    ? '#ef4444'
    : winRate <= 0.45
    ? '#fca5a5'
    : '#facc15';

  if (!hasData) {
    return (
      <div style={styles.container}>
        <div style={styles.labels}>
          <span style={{ color: '#60a5fa', fontWeight: 700 }}>我方</span>
          <span style={{ color: '#475569', fontSize: 12 }}>各选≥2英雄后显示预测胜率</span>
          <span style={{ color: '#f87171', fontWeight: 700 }}>对方</span>
        </div>
        <div style={styles.track}>
          <div style={{ ...styles.fill, width: '50%', background: '#334155' }} />
          <div style={styles.center} />
        </div>
        <div style={styles.pcts}>
          <span style={{ color: '#475569', fontWeight: 700 }}>--</span>
          <span style={{ color: '#475569', fontWeight: 700 }}>--</span>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.labels}>
        <span style={{ color: '#60a5fa', fontWeight: 700 }}>我方</span>
        <span style={{ color: '#94a3b8', fontSize: 12 }}>
          {loading ? '计算中...' : `预测胜率 ${pct}%`}
        </span>
        <span style={{ color: '#f87171', fontWeight: 700 }}>对方</span>
      </div>
      <div style={styles.track}>
        <div style={{ ...styles.fill, width: barWidth, background: color }} />
        <div style={{ ...styles.center }} />
      </div>
      <div style={styles.pcts}>
        <span style={{ color: color, fontWeight: 700 }}>{pct}%</span>
        <span style={{ color: '#ef4444', fontWeight: 700 }}>{100 - pct}%</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    minWidth: 200,
  },
  labels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
    color: '#94a3b8',
  },
  track: {
    position: 'relative',
    height: 10,
    background: '#7f1d1d',
    borderRadius: 5,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: '5px 0 0 5px',
    transition: 'width 0.5s ease',
  },
  center: {
    position: 'absolute',
    top: 0,
    left: '50%',
    width: 2,
    height: '100%',
    background: 'rgba(255,255,255,0.3)',
    transform: 'translateX(-50%)',
  },
  pcts: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 13,
  },
};
