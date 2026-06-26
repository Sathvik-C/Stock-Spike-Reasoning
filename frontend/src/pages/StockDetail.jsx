import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { stocksAPI } from '../api/client';
import PriceChart from '../components/stock/PriceChart';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import { ExternalLink, TrendingUp, TrendingDown, Minus, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';

// subcomponents
const VerdictCard = ({ analysis, isLoading }) => {
  if (isLoading) return <Skeleton height={140} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20" />;
  if (!analysis) return null;

  const type = analysis.reason_category || 'general';

  const borderColors = {
    earnings: 'border-l-positive',
    corporate: 'border-l-neutral',
    sector: 'border-l-warning',
    technical: 'border-l-muted',
    general: 'border-l-muted',
  };
  const borderColor = borderColors[type] || borderColors.general;

  const confColors = {
    High: 'bg-positive/10 text-positive border-positive/20',
    Medium: 'bg-warning/10 text-warning border-warning/20',
    Low: 'bg-muted/10 text-muted border-muted/20',
  };
  const confBadge = confColors[analysis.reason_confidence] || confColors.Medium;

  return (
    <div className={clsx("w-full surface-card p-5 border-l-4 animate-in fade-in slide-in-from-bottom-2 duration-300", borderColor)}>
      <div className="flex justify-between items-start mb-2">
        <span className="text-muted text-sm font-semibold uppercase tracking-wider">Most Likely Cause</span>
        <span className={clsx("px-2 py-0.5 rounded text-xs font-bold border", confBadge)}>
          {analysis.reason_confidence} Confidence
        </span>
      </div>
      <h3 className="text-lg font-bold text-primary mb-2">{analysis.reason_detail}</h3>
    </div>
  );
};

const normalizeEarnings = (earnings) => {
  if (!earnings) return null;

  return {
    revenue: earnings.revenue ?? earnings.total_revenue ?? null,
    previous_revenue: earnings.previous_revenue ?? null,
    revenue_beat: earnings.revenue_beat ?? false,
    net_profit: earnings.net_profit ?? earnings.net_income ?? null,
    previous_profit: earnings.previous_profit ?? null,
    profit_beat: earnings.profit_beat ?? false,
    eps: earnings.eps ?? earnings.diluted_eps ?? null,
    previous_eps: earnings.previous_eps ?? null,
    eps_beat: earnings.eps_beat ?? false,
    gross_profit: earnings.gross_profit ?? null,
    ebitda: earnings.ebitda ?? null,
    quarter_end: earnings.quarter_end,
    calendar_date: earnings.calendar_date,
    calendar_event: earnings.calendar_event,
  };
};

const EarningsSection = ({ earningsData, isLoading }) => {
  if (isLoading) return <Skeleton height={100} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20" />;

  const earnings = earningsData?.earnings;
  const bseFiling = earningsData?.bse_filing;
  const normalized = normalizeEarnings(earnings);

  if ((!normalized || (normalized.revenue == null && normalized.net_profit == null && normalized.eps == null)) && !bseFiling) return null;

  let reportDate = '';
  if (bseFiling?.filed_at) {
    const d = new Date(bseFiling.filed_at);
    if (!isNaN(d)) reportDate = d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  if (!reportDate && normalized?.quarter_end) {
    const d = new Date(normalized.quarter_end);
    if (!isNaN(d)) reportDate = d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
  }

  const formatValue = (title, val) => {
    if (typeof val !== 'number') return val;
    if (title === 'EPS') return val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // For large monetary values (Revenue, Profit, EBITDA), format in Crores
    const inCrores = val / 10000000;
    return `${inCrores.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} Cr`;
  };

  const MetricCard = ({ title, value, prev, beat }) => (
    <div className="surface-card p-4 flex flex-col gap-1">
      <span className="text-muted text-sm font-medium">{title}</span>
      <div className="flex items-center justify-between mt-1">
        <span className="font-bold text-xl font-mono">
          {formatValue(title, value)}
        </span>
        {beat && (
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-positive/10 text-positive border border-positive/20">
            Beat
          </span>
        )}
      </div>
      <span className="text-muted text-xs font-mono">Prev: {prev !== 'N/A' ? formatValue(title, prev) : prev}</span>
    </div>
  );

  return (
    <div className="mt-8">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold flex items-center gap-2">
          Quarterly Earnings <span className="text-muted text-sm font-normal">(Latest{reportDate ? `: ${reportDate}` : ''})</span>
        </h3>
        {bseFiling?.attachment_url && (
          <a
            href={bseFiling.attachment_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded text-xs font-bold transition-colors"
          >
            <ExternalLink size={14} />
            View Official Document
          </a>
        )}
      </div>

      {normalized && (normalized.revenue != null || normalized.net_profit != null || normalized.eps != null) ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {normalized.revenue != null && <MetricCard title="Revenue" value={normalized.revenue} prev={normalized.previous_revenue || 'N/A'} beat={normalized.revenue_beat} />}
          {normalized.gross_profit != null && <MetricCard title="Gross Profit" value={normalized.gross_profit} prev="N/A" />}
          {normalized.ebitda != null && <MetricCard title="EBITDA" value={normalized.ebitda} prev="N/A" />}
          {normalized.net_profit != null && <MetricCard title="Net Profit" value={normalized.net_profit} prev={normalized.previous_profit || 'N/A'} beat={normalized.profit_beat} />}
          {normalized.eps != null && <MetricCard title="EPS" value={normalized.eps} prev={normalized.previous_eps || 'N/A'} beat={normalized.eps_beat} />}
        </div>
      ) : (
        <div className="surface-card p-4 text-sm text-muted">
          Numerical data is not available yet, but you can view the official filing above.
        </div>
      )}
    </div>
  );
};

const NewsSummarySection = ({ newsSummaryData, isLoading }) => {
  if (isLoading) return <Skeleton height={200} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20 mt-8" />;
  if (!newsSummaryData || !newsSummaryData.news_summary) return null;

  const { overall_summary, articles } = newsSummaryData.news_summary;
  const topNews = newsSummaryData.top_news || [];

  return (
    <div className="mt-8">
      <h3 className="text-lg font-bold mb-4">News Summary <span className="text-muted text-sm font-normal">(AI Generated)</span></h3>

      {/* AI Summary Paragraph */}
      <div className="surface-card p-5 mb-5 border-l-4 border-l-primary">
        <p className="text-[15px] leading-relaxed text-muted">
          {overall_summary || "Loading summary..."}
        </p>
      </div>

      {/* Top Headlines List */}
      {topNews.length > 0 && (
        <div className="flex flex-col gap-3">
          <h4 className="text-sm font-semibold text-muted uppercase tracking-wider mb-2">Top Headlines</h4>
          {topNews.slice(0, 5).map((article, i) => {
            const dateStr = new Date(article.published_ts || article.published).toLocaleString('en-IN', {
              day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
            });

            return (
              <a
                key={i}
                href={article.link || article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="surface-card p-4 hover:bg-surface/80 transition-colors group flex flex-col gap-2"
              >
                <div className="flex justify-between items-start gap-4">
                  <h4 className="font-bold text-[14px] leading-snug line-clamp-2 group-hover:text-accent transition-colors">
                    {article.title}
                  </h4>
                  <ExternalLink size={16} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5" />
                </div>
                <div className="flex justify-between items-center text-xs mt-1 text-muted">
                  <span>{article.source}</span>
                  <span>{dateStr !== 'Invalid Date' ? dateStr : ''}</span>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
};

import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const CLUSTER_COLORS = [
  '#ef4444', '#3b82f6', '#22c55e', '#eab308',
  '#a855f7', '#ec4899', '#f97316', '#14b8a6'
];

const ScatterTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-surface border border-border p-2 rounded shadow-xl text-xs font-mono">
        <div className="font-bold text-primary mb-1">{data.label}</div>
        <div className="text-muted text-[10px]">Cluster {data.cluster + 1}</div>
      </div>
    );
  }
  return null;
};

const PeersSection = ({ clusters, currentTicker, isLoading }) => {
  if (isLoading) return <Skeleton height={250} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20 mb-6" />;
  if (!clusters || !clusters.clusters) return null;

  const mapping = clusters.clusters;
  const currentData = mapping[currentTicker];

  if (!currentData || typeof currentData !== 'object') return null;

  const clusterId = currentData.cluster;

  // Format data for ScatterChart
  const dataPoints = Object.entries(mapping).map(([ticker, data]) => ({
    ticker,
    label: ticker.replace('.NS', ''),
    cluster: data.cluster,
    x: data.x,
    y: data.y,
    isCurrent: ticker === currentTicker,
    // Make the current stock point much larger
    z: ticker === currentTicker ? 200 : 30
  }));

  const peers = dataPoints
    .filter(p => p.cluster === clusterId && !p.isCurrent)
    .map(p => p.ticker)
    .sort();

  return (
    <div className="surface-card p-5 mb-6">
      <h3 className="text-[16px] font-bold mb-4 tracking-tight border-b border-border pb-3 flex items-center justify-between">
        <span>Market Peers</span>
        <span className="text-[10px] font-mono font-normal text-muted px-2 py-0.5 bg-bg rounded border border-border">K-Means PCA</span>
      </h3>

      <div className="w-full h-[220px] mb-4 bg-bg/50 rounded-lg border border-border/50 relative overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
            <XAxis type="number" dataKey="x" hide domain={['dataMin - 0.1', 'dataMax + 0.1']} />
            <YAxis type="number" dataKey="y" hide domain={['dataMin - 0.1', 'dataMax + 0.1']} />
            <ZAxis type="number" dataKey="z" range={[20, 250]} />
            <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#374151' }} />
            <Scatter data={dataPoints} isAnimationActive={false}>
              {dataPoints.map((entry, index) => {
                const color = CLUSTER_COLORS[entry.cluster % CLUSTER_COLORS.length];
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.isCurrent ? 'var(--color-scatter-current)' : color}
                    fillOpacity={entry.isCurrent ? 1 : (entry.cluster === clusterId ? 0.8 : 0.2)}
                    stroke={entry.isCurrent ? color : 'none'}
                    strokeWidth={entry.isCurrent ? 2 : 0}
                  />
                );
              })}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {peers.length === 0 ? (
        <div className="text-sm text-muted text-center py-4">No close peers found.</div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {peers.slice(0, 10).map(peer => (
            <Link
              key={peer}
              to={`/stock/${peer}`}
              className="px-2.5 py-1 text-[11px] font-mono font-medium bg-surface hover:bg-neutral/30 border border-border rounded transition-colors text-primary"
            >
              {peer.replace('.NS', '')}
            </Link>
          ))}
          {peers.length > 10 && (
            <span className="px-2.5 py-1 text-[11px] font-mono text-muted flex items-center">
              +{peers.length - 10} more
            </span>
          )}
        </div>
      )}
    </div>
  );
};

const TechnicalSignals = ({ tech, isLoading, currentPrice }) => {
  if (isLoading) return <Skeleton height={250} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20 mb-6" />;
  if (!tech || !tech.signals) return null;

  const rsi = tech.signals.rsi;
  const isOversold = rsi < 30;
  const isOverbought = rsi > 70;
  const technical = tech.signals;

  return (
    <div className="surface-card p-5 mb-6">
      <h3 className="text-[16px] font-bold mb-5 tracking-tight border-b border-border pb-3">Technical Signals</h3>

      <div className="flex flex-col gap-5">
        {/* 2a. Trend Banner */}
        <div className={clsx(
          "flex items-center justify-between px-4 py-2 rounded-lg text-sm font-bold uppercase tracking-wider",
          technical.trend === 'uptrend' ? 'bg-positive/10 text-positive border border-positive/20' :
            technical.trend === 'downtrend' ? 'bg-negative/10 text-negative border border-negative/20' :
              'bg-surface text-muted border border-border'
        )}>
          <span>Trend</span>
          <span>{technical.trend || 'Sideways'}</span>
        </div>

        {/* 2b. Moving Averages section */}
        <div className="flex flex-col gap-2 py-2 border-t border-border/50">
          {[
            { label: 'MA 20', val: technical.ma_20 },
            { label: 'MA 50', val: technical.ma_50 },
            { label: 'MA 200', val: technical.ma_200 },
          ].map(ma => {
            if (ma.val == null) return null;
            const isAbove = currentPrice != null && currentPrice > ma.val;
            return (
              <div key={ma.label} className="flex justify-between items-center text-sm">
                <span className="text-muted">{ma.label}</span>
                <div className="flex gap-4 text-right">
                  <span className="font-mono text-primary">₹{ma.val.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                  <span className={clsx("w-20 text-right", isAbove ? "text-positive" : "text-negative")}>
                    {isAbove ? '▲ above' : '▼ below'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* 2c. 52-Week Position bar */}
        <div className="py-2 border-t border-border/50 mt-1">
          <div className="flex items-center justify-between text-[10px] text-muted mb-2 font-mono uppercase tracking-wider">
            <span>52W Low ₹{technical.low_52w?.toLocaleString('en-IN', { maximumFractionDigits: 0 }) || '—'}</span>
            <span>52W High ₹{technical.high_52w?.toLocaleString('en-IN', { maximumFractionDigits: 0 }) || '—'}</span>
          </div>
          <div className="relative h-1 w-full bg-surface rounded-full border border-border mt-3">
            {technical.position_52w != null && (
              <div
                className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 bg-accent rounded-full shadow border-2 border-surface"
                style={{ left: `${Math.min(Math.max(technical.position_52w * 100, 0), 100)}%`, transform: 'translate(-50%, -50%)' }}
              />
            )}
          </div>
        </div>

        {/* 2d. Keep the existing RSI gauge bar */}
        <div className="py-2 border-t border-border/50">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-muted">RSI (14)</span>
            <span className={clsx("font-bold tabular-nums", isOversold ? "text-negative" : isOverbought ? "text-warning" : "text-primary")}>
              {rsi?.toFixed(1) || '—'}
            </span>
          </div>
          <div className="w-full h-1.5 bg-gradient-to-r from-negative via-surface to-warning rounded-full relative border border-border">
            {rsi && (
              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow border-2 border-surface"
                style={{ left: `${Math.min(Math.max(rsi, 0), 100)}%` }}
              />
            )}
          </div>
          <div className="flex justify-between text-[10px] text-muted mt-1 uppercase font-bold tracking-wider">
            <span>Oversold</span>
            <span>Neutral</span>
            <span>Overbought</span>
          </div>
        </div>

        {/* 2e. Signals grid */}
        <div className="grid grid-cols-2 gap-3 py-2 border-t border-border/50">
          <div className="surface-card p-3 border border-border rounded flex justify-between items-center">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted">MACD</span>
              <span className="text-sm font-medium capitalize text-primary">{technical.macd_signal || 'Neutral'}</span>
            </div>
            <div className={clsx("w-2 h-2 rounded-full", technical.macd_signal === 'bullish' ? "bg-positive" : technical.macd_signal === 'bearish' ? "bg-negative" : "bg-muted")} />
          </div>

          <div className="surface-card p-3 border border-border rounded flex justify-between items-center">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted">Bollinger</span>
              <span className="text-sm font-medium capitalize text-primary">{technical.bollinger_position || 'Within'}</span>
            </div>
            <div className={clsx("w-2 h-2 rounded-full", technical.bollinger_position === 'upper' ? "bg-warning" : technical.bollinger_position === 'lower' ? "bg-positive" : "bg-muted")} />
          </div>

          <div className="surface-card p-3 border border-border rounded flex justify-between items-center">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted">Volume</span>
              <span className="text-sm font-medium text-primary">{technical.volume_ratio ? `${technical.volume_ratio}x avg` : 'Normal'}</span>
            </div>
            <div className={clsx("w-2 h-2 rounded-full", technical.volume_ratio > 1.5 ? "bg-positive" : "bg-muted")} />
          </div>

          <div className="surface-card p-3 border border-border rounded flex justify-between items-center">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted">ATR Volatility</span>
              <span className="text-sm font-medium text-primary">{technical.atr_pct ? `${technical.atr_pct.toFixed(1)}% normal` : '—'}</span>
            </div>
            <div className={clsx("w-2 h-2 rounded-full", technical.atr_pct > 3.0 ? "bg-warning" : "bg-muted")} />
          </div>
        </div>

        {/* 2f. Breakout verdict */}
        {tech.breakout ? (
          <div className="surface-card border-l-4 border-l-positive p-3 text-sm text-primary mt-1">
            {tech.summary}
          </div>
        ) : (
          <p className="text-muted text-xs mt-1 text-center">{tech.summary}</p>
        )}

      </div>
    </div>
  );
};

const PERIODS = [
  { label: '1D', days: 1 },
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
];

const BenchmarkComparison = ({ ticker }) => {
  const [activePeriod, setActivePeriod] = React.useState(PERIODS[0]);

  const { data: stockData, isLoading: loadingStock } = useQuery({
    queryKey: ['chart', ticker, activePeriod.days],
    queryFn: () => stocksAPI.getChartData(ticker, activePeriod.days).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: benchmarkData, isLoading: loadingBenchmark } = useQuery({
    queryKey: ['chart', '^CNX100', activePeriod.days],
    queryFn: () => stocksAPI.getChartData(encodeURIComponent('^CNX100'), activePeriod.days).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = loadingStock || loadingBenchmark;

  if (isLoading && (!stockData || !benchmarkData)) {
    return <Skeleton height={150} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20 mb-6" />;
  }

  const getPctChange = (dataObj) => {
    if (!dataObj) return 0;

    // Always prefer calculating from the actual chart data shown to the user!
    if (dataObj.data && dataObj.data.length > 1) {
      const first = dataObj.data[0].close;
      const last = dataObj.data[dataObj.data.length - 1].close;
      if (first) {
        return ((last - first) / first) * 100;
      }
    }

    // Fallback to backend value
    if (Number.isFinite(Number(dataObj.pct_change))) return Number(dataObj.pct_change);

    return 0;
  };

  const pChg = getPctChange(stockData);
  const sChg = getPctChange(benchmarkData);
  const stockLabel = (ticker || 'Stock').replace('.NS', '');

  return (
    <div className="surface-card p-5 mb-6">
      <div className="flex justify-between items-center mb-4 border-b border-border pb-3">
        <h3 className="text-[16px] font-bold tracking-tight">NIFTY 100 vs Stock</h3>
        <div className="flex gap-1">
          {PERIODS.map((period) => (
            <button
              key={period.label}
              onClick={() => setActivePeriod(period)}
              className={clsx(
                'px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide transition-colors',
                activePeriod.label === period.label
                  ? 'bg-neutral text-primary'
                  : 'text-muted hover:text-primary hover:bg-neutral/20'
              )}
            >
              {period.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-4">
        <div>
          <div className="flex justify-between text-sm mb-1.5">
            <span className="text-primary font-medium">{stockLabel}</span>
            <span className={clsx("font-mono font-bold", pChg >= 0 ? "text-positive" : "text-negative")}>
              {pChg > 0 ? '+' : ''}{pChg.toFixed(2)}%
            </span>
          </div>
          <div className="h-2 w-full bg-bg rounded-full overflow-hidden">
            <div className={clsx("h-full rounded-full transition-all duration-500", pChg >= 0 ? "bg-positive" : "bg-negative")} style={{ width: `${Math.min(Math.abs(pChg) * 5, 100)}%` }} />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-sm mb-1.5">
            <span className="text-muted font-medium">NIFTY 100</span>
            <span className={clsx("font-mono font-bold", sChg >= 0 ? "text-positive" : "text-negative")}>
              {sChg > 0 ? '+' : ''}{sChg.toFixed(2)}%
            </span>
          </div>
          <div className="h-2 w-full bg-bg rounded-full overflow-hidden">
            <div className={clsx("h-full rounded-full opacity-60 transition-all duration-500", sChg >= 0 ? "bg-positive" : "bg-negative")} style={{ width: `${Math.min(Math.abs(sChg) * 5, 100)}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default function StockDetail() {
  const { ticker } = useParams();

  // Fetch exactly what fits the premium terminal view
  const { data: stocksList } = useQuery({ queryKey: ['stocks-list'], queryFn: () => stocksAPI.list().then(res => res.data), staleTime: Infinity });
  const { data: analysis, isLoading: loadingAnalysis } = useQuery({ queryKey: ['analysis', ticker], queryFn: () => stocksAPI.getAnalysis(ticker, 1).then(r => r.data) });
  const { data: chart1Y, isLoading: loadingChart } = useQuery({ queryKey: ['chart', ticker, 365], queryFn: () => stocksAPI.getChartData(ticker, 365).then(r => r.data) });
  const { data: earnings, isLoading: loadingEarnings } = useQuery({ queryKey: ['earnings', ticker], queryFn: () => stocksAPI.getEarnings(ticker).then(r => r.data) });
  const { data: newsSummaryData, isLoading: loadingNewsSummary } = useQuery({ queryKey: ['news-summary', ticker], queryFn: () => stocksAPI.getNewsSummary(ticker).then(r => r.data) });
  const { data: sectorRes, isLoading: loadingSector } = useQuery({ queryKey: ['sector', ticker], queryFn: () => stocksAPI.getSector(ticker).then(r => r.data) });
  const { data: techRes, isLoading: loadingTech } = useQuery({ queryKey: ['technical', ticker], queryFn: () => stocksAPI.getTechnical(ticker).then(r => r.data) });
  const { data: clustersData, isLoading: loadingClusters } = useQuery({ queryKey: ['clusters', 'v2'], queryFn: () => stocksAPI.getClusters().then(r => r.data), staleTime: 5 * 60 * 1000 });

  const companyName = stocksList?.find(s => s.ticker === ticker)?.name || ticker;

  // Calculate top-level stats from 1Y chart data
  let currentPrice = null;
  let todayChange = null;
  let high52 = null;
  let low52 = null;

  if (chart1Y?.data?.length > 0) {
    const closes = chart1Y.data.map((point) => point.close).filter((value) => typeof value === 'number');
    if (!closes.length) {
      // Keep nulls if no valid numeric points are present.
    } else {
      currentPrice = closes[closes.length - 1];
      const prevC = closes[closes.length - 2];
      if (prevC) {
        todayChange = ((currentPrice - prevC) / prevC) * 100;
      }
      high52 = Math.max(...closes);
      low52 = Math.min(...closes);
    }
  }

  // Keep all 1D percentages aligned with backend analysis value.
  const displayChange = analysis?.price_change ?? todayChange ?? 0;
  const isPositive = displayChange >= 0;

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

        {/* Left Column (70%) */}
        <div className="lg:col-span-8 flex flex-col gap-6">

          {/* Header */}
          <div className="mb-2">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-primary tracking-tight">{companyName}</h1>
              <span className="px-2.5 py-1 text-xs font-mono font-bold bg-surface border border-border rounded-full text-muted tracking-wider">
                {ticker}
              </span>
            </div>

            <div className="flex items-end gap-4 mt-4">
              {currentPrice !== null ? (
                <span className="text-4xl tabular-nums font-mono font-bold text-primary tracking-tight">
                  ₹{currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              ) : (
                <Skeleton width={150} height={40} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="opacity-20" />
              )}

              {currentPrice !== null && (
                <div className="flex items-center gap-4">
                  <div className={clsx("flex items-center mb-1 text-lg tabular-nums font-bold", isPositive ? "text-positive" : "text-negative")}>
                    {isPositive ? <TrendingUp size={20} className="mr-1.5" /> : <TrendingDown size={20} className="mr-1.5" />}
                    {isPositive ? '+' : ''}{displayChange.toFixed(2)}%
                  </div>

                  {/* Direction Prediction Badge */}
                  {analysis?.direction_prediction && analysis.direction_prediction.direction !== 'neutral' && (
                    <div className={clsx(
                      "flex items-center mb-1 px-3 py-1 text-sm font-bold rounded-full border",
                      analysis.direction_prediction.direction === 'bullish'
                        ? "bg-positive/10 text-positive border-positive/30"
                        : "bg-negative/10 text-negative border-negative/30"
                    )}>
                      {analysis.direction_prediction.direction === 'bullish' ? <ArrowUpRight size={16} className="mr-1" /> : <ArrowDownRight size={16} className="mr-1" />}
                      <span className="capitalize">{analysis.direction_prediction.direction}</span>
                      <span className="ml-1 opacity-80">{Math.round(analysis.direction_prediction.confidence * 100)}%</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 52-Week Range Bar */}
            {high52 && low52 && (
              <div className="flex items-center gap-3 mt-5 w-full max-w-md">
                <span className="text-xs text-muted font-mono w-14 text-right">{low52.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                <div className="flex-1 h-1.5 bg-surface border border-border rounded-full relative">
                  <div
                    className={clsx("absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full shadow-sm", currentPrice > (high52 + low52) / 2 ? "bg-positive" : "bg-negative")}
                    style={{ left: `${Math.max(0, Math.min(100, ((currentPrice - low52) / (high52 - low52)) * 100))}%` }}
                  />
                </div>
                <span className="text-xs text-muted font-mono w-14 text-left">{high52.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              </div>
            )}
          </div>

          <VerdictCard analysis={analysis} isLoading={loadingAnalysis} />

          <PriceChart ticker={ticker} dayChange={analysis?.price_change} />

          {/* Analysis Summary */}
          {!loadingAnalysis && analysis?.reason_detail && (
            <div className="mt-8 relative">
              <h3 className="text-lg font-bold mb-4">Analysis Summary</h3>
              <blockquote className="border-l-4 border-neutral bg-surface/50 rounded-r-lg p-5 text-[15px] leading-relaxed text-muted">
                {analysis.reason_detail}
              </blockquote>
            </div>
          )}

          <EarningsSection earningsData={earnings} isLoading={loadingEarnings} />

          <NewsSummarySection newsSummaryData={newsSummaryData} isLoading={loadingNewsSummary} />

        </div>

        {/* Right Column (30%) - Sticky on Desktop */}
        <div className="lg:col-span-4 lg:sticky lg:top-24">
          <TechnicalSignals tech={techRes} isLoading={loadingTech} currentPrice={currentPrice} />
          <BenchmarkComparison ticker={ticker} />

          <PeersSection clusters={clustersData} currentTicker={ticker} isLoading={loadingClusters} />
        </div>

      </div>
    </div>
  );
}