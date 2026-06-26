import React, { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { useQuery } from '@tanstack/react-query';
import { stocksAPI } from '../api/client';
import { useNavigate } from 'react-router-dom';
import CountUp from 'react-countup';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import { motion } from 'framer-motion';
import {
  Activity,
  BarChart2,
  ChevronRight,
  Newspaper,
  TrendingDown,
  TrendingUp,
  Zap,
  Search,
} from 'lucide-react';

const TOP_MOVERS_CACHE_KEY = 'stock-spike-top-movers-v2';
const TOP_MOVERS_CACHE_TTL = 5 * 60 * 1000;

const readCachedTopMovers = () => {
  try {
    const raw = localStorage.getItem(TOP_MOVERS_CACHE_KEY);
    if (!raw) return undefined;

    const parsed = JSON.parse(raw);
    if (!parsed?.data || typeof parsed?.timestamp !== 'number') return undefined;

    if (Date.now() - parsed.timestamp > TOP_MOVERS_CACHE_TTL) return undefined;
    return parsed;
  } catch {
    return undefined;
  }
};

const writeCachedTopMovers = (data) => {
  try {
    localStorage.setItem(TOP_MOVERS_CACHE_KEY, JSON.stringify({
      timestamp: Date.now(),
      data,
    }));
  } catch {
    // Ignore storage failures and fall back to network only.
  }
};

const stripTicker = (ticker = '') => ticker.replace('.NS', '');

const formatPct = (value) => `${value > 0 ? '+' : ''}${Number(value || 0).toFixed(2)}%`;

const buildVerdictCopy = (stock) => {
  if (!stock) {
    return {
      title: 'Waiting for live movers',
      summary: 'The landing card updates from the latest top movers once market data is available.',
      signal: 'Live feed pending',
      confidence: '—',
      positive: true,
    };
  }

  const change = Number(stock.change || 0);
  const positive = change >= 0;
  const confidence = Math.min(96, Math.max(68, 74 + Math.round(Math.abs(change) * 2.5)));

  return {
    title: stock.ticker,
    summary: `${stock.name} moved ${positive ? 'higher' : 'lower'} by ${Math.abs(change).toFixed(2)}% in the selected window. The card rotates through live movers so the landing page stays current.`,
    signal: positive ? 'Momentum-led move' : 'Distribution-led move',
    confidence: `${confidence}%`,
    positive,
  };
};

const HeroVerdictCard = ({ stock, index }) => {
  const verdict = buildVerdictCopy(stock);

  return (
    <div className={`surface-card hidden lg:block border-l-4 p-6 shadow-[0_20px_80px_rgba(16,185,129,0.08)] ${verdict.positive ? 'border-positive' : 'border-negative'}`}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <span className="text-muted text-xs font-semibold uppercase tracking-[0.24em]">Most Likely Cause</span>
        <span className={`px-2.5 py-1 rounded-full border text-xs font-bold ${verdict.positive ? 'border-positive/20 bg-positive/10 text-positive' : 'border-negative/20 bg-negative/10 text-negative'}`}>
          {stock ? `Live mover ${index + 1}` : 'High Confidence'}
        </span>
      </div>
      <h3 className="text-2xl font-bold text-primary mb-2">{verdict.title}</h3>
      <p className="text-sm text-muted leading-6">{verdict.summary}</p>
      <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
        <div className="surface-card px-3 py-2">
          <div className="text-muted mb-1">Signal</div>
          <div className="font-semibold text-primary">{verdict.signal}</div>
        </div>
        <div className="surface-card px-3 py-2">
          <div className="text-muted mb-1">Confidence</div>
          <div className="font-semibold text-positive">{verdict.confidence}</div>
        </div>
      </div>
    </div>
  );
};

const MarketStatCard = ({ label, value, tone = 'neutral', loading = false, sublabel }) => {
  const toneClass = tone === 'positive' ? 'text-positive' : tone === 'negative' ? 'text-negative' : 'text-primary';

  return (
    <div className="surface-card p-4 lg:p-5">
      <div className="text-xs uppercase tracking-[0.18em] text-muted mb-2">{label}</div>
      {loading ? (
        <Skeleton height={28} width="72%" baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20" />
      ) : (
        <div className={`text-xl lg:text-2xl font-bold tabular-nums ${toneClass}`}>{value}</div>
      )}
      {sublabel && <div className="text-xs text-muted mt-2">{sublabel}</div>}
    </div>
  );
};

const MoverSkeleton = ({ index }) => (
  <div className="surface-card p-4 border-l-4 border-border">
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <Skeleton width={52} height={14} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="mb-2 opacity-20" />
        <Skeleton width="70%" height={18} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="mb-2 opacity-20" />
        <Skeleton width="45%" height={12} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="opacity-20" />
      </div>
      <Skeleton width={66} height={26} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="rounded-lg opacity-20" />
    </div>
    <div className="mt-3 text-[10px] text-muted font-mono">Loading #{index + 1}</div>
  </div>
);

const SECTOR_MAP = {
  'INFY': 'IT', 'TCS': 'IT', 'WIPRO': 'IT', 'HCLTECH': 'IT', 'TECHM': 'IT',
  'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking', 'KOTAKBANK': 'Banking', 'AXISBANK': 'Banking',
  'RELIANCE': 'Energy', 'ONGC': 'Energy', 'BPCL': 'Energy', 'NTPC': 'Energy', 'POWERGRID': 'Energy',
  'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma', 'DIVISLAB': 'Pharma',
  'MARUTI': 'Auto', 'TATAMOTORS': 'Auto', 'BAJAJ-AUTO': 'Auto', 'HEROMOTOCO': 'Auto', 'EICHERMOT': 'Auto',
  'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG', 'BRITANNIA': 'FMCG', 'TATACONSUM': 'FMCG',
  'LT': 'Infra', 'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'JSWSTEEL': 'Metal', 'HINDALCO': 'Metal',
  'TITAN': 'Consumer', 'ASIANPAINT': 'Consumer', 'DMART': 'Retail', 'BAJFINANCE': 'Finance', 'BAJAJFINSV': 'Finance',
};

const MoverCard = ({ stock, index, tone }) => {
  const navigate = useNavigate();
  const isPositive = tone === 'positive';
  const sector = SECTOR_MAP[stripTicker(stock.ticker)] || 'NIFTY';

  return (
    <motion.button
      type="button"
      onClick={() => navigate(`/stock/${stock.ticker}`)}
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.35 }}
      transition={{ duration: 0.35, delay: index * 0.06 }}
      whileHover={{ y: -2, scale: 1.01 }}
      className={clsx(
        "group relative surface-card w-full text-left p-4 overflow-hidden border-l-4 transition-all duration-200",
        isPositive ? "border-positive" : "border-negative",
        "hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)]"
      )}
    >
      <div className={clsx(
        "absolute right-2 top-1/2 -translate-y-1/2 text-6xl font-black tabular-nums opacity-[0.04] select-none pointer-events-none",
        isPositive ? "text-positive" : "text-negative"
      )}>
        {isPositive ? '+' : ''}{Number(stock.change || 0).toFixed(1)}%
      </div>
      <div className={clsx(
        "absolute inset-y-0 left-0 w-24 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
        isPositive ? "bg-gradient-to-r from-positive/20 to-transparent" : "bg-gradient-to-r from-negative/20 to-transparent"
      )} />
      <div className="relative flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[10px] font-mono text-muted mb-1">#{index + 1}</div>
          <div className="font-bold text-primary text-[15px] leading-tight truncate">{stock.name}</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-muted font-mono">{stripTicker(stock.ticker)}</span>
            <span className="text-[10px] font-mono text-muted/60 bg-surface px-1.5 py-0.5 rounded border border-border/40 inline-block">
              {sector}
            </span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-1">
          <div className={clsx("font-bold tabular-nums text-lg lg:text-xl", isPositive ? "text-positive" : "text-negative")}>
            {isPositive ? '+' : ''}<CountUp end={stock.change || 0} decimals={2} duration={1.1} separator="," suffix="%" />
          </div>
          <span className="text-[10px] text-muted opacity-0 group-hover:opacity-100 transition-opacity font-mono">
            Analyze →
          </span>
        </div>
      </div>
      <div className="mt-3 h-0.5 w-full bg-surface rounded-full overflow-hidden relative z-10">
        <motion.div
          className={clsx("h-full rounded-full", isPositive ? "bg-positive" : "bg-negative")}
          initial={{ width: 0 }}
          whileInView={{ width: `${Math.min(100, Math.abs(stock.change || 0) * 10)}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: index * 0.06 + 0.2 }}
        />
      </div>
    </motion.button>
  );
};

const HeroTicker = ({ items }) => {
  const tapeItems = useMemo(() => [...items, ...items], [items]);

  return (
    <div className="relative overflow-hidden -mx-6 sm:-mx-8 border-y border-border bg-surface/40">
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 sm:w-24 bg-gradient-to-r from-bg to-transparent z-10" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 sm:w-24 bg-gradient-to-l from-bg to-transparent z-10" />
      <motion.div
        className="flex w-max gap-8 py-3 px-6 sm:px-8"
        animate={{ x: ['0%', '-50%'] }}
        transition={{ repeat: Infinity, repeatType: 'loop', duration: 28, ease: 'linear' }}
      >
        {tapeItems.map((stock, index) => {
          const positive = stock.change >= 0;
          return (
            <div key={`${stock.ticker}-${index}`} className={`flex items-center gap-2 whitespace-nowrap font-mono text-sm ${positive ? 'text-positive' : 'text-negative'}`}>
              <span className="font-semibold tracking-wide">{stripTicker(stock.ticker)}</span>
              <span>{positive ? '+' : ''}{Number(stock.change || 0).toFixed(2)}%</span>
            </div>
          );
        })}
      </motion.div>
    </div>
  );
};

export default function Home() {
  const [activeVerdictIndex, setActiveVerdictIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  
  const handleHeroSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      let query = searchQuery.trim().toUpperCase();
      if (!query.endsWith('.NS')) {
        query = `${query}.NS`;
      }
      navigate(`/stock/${query}`);
    }
  };

  const cachedTopMovers = typeof window !== 'undefined' ? readCachedTopMovers() : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ['top-movers', 'v2'],
    queryFn: () => stocksAPI.getTopMovers(1, 5).then((res) => res.data),
    initialData: cachedTopMovers?.data,
    initialDataUpdatedAt: cachedTopMovers?.timestamp,
    staleTime: TOP_MOVERS_CACHE_TTL,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  });

  useEffect(() => {
    if (data) {
      writeCachedTopMovers(data);
    }
  }, [data]);

  const gainers = data?.gainers || [];
  const losers = data?.losers || [];
  const topGainer = gainers[0];
  const topLoser = losers[0];
  const avgGain = gainers.length ? (gainers.reduce((sum, stock) => sum + Number(stock.change || 0), 0) / gainers.length) : 0;

  const featuredMovers = useMemo(() => {
    const combined = [...gainers, ...losers];
    return combined.filter((stock, index, list) => list.findIndex((item) => item.ticker === stock.ticker) === index);
  }, [gainers, losers]);

  useEffect(() => {
    if (featuredMovers.length <= 1) {
      setActiveVerdictIndex(0);
      return undefined;
    }

    setActiveVerdictIndex((current) => current % featuredMovers.length);
    const timer = window.setInterval(() => {
      setActiveVerdictIndex((current) => (current + 1) % featuredMovers.length);
    }, 4500);

    return () => window.clearInterval(timer);
  }, [featuredMovers]);

  const tickerTapeItems = [...gainers, ...losers];
  const activeVerdict = featuredMovers[activeVerdictIndex];

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-8 lg:py-10">
      <section className="border-b border-border pb-10 lg:pb-12">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-positive/20 bg-positive/10 text-positive text-xs font-semibold tracking-[0.22em] uppercase mb-5">
              <span className="inline-block h-2 w-2 rounded-full bg-positive animate-pulse" />
              Live · NIFTY 100
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-primary leading-[1.02]">
              Why is this stock <span className="text-accent">moving?</span>
            </h1>
            <p className="mt-5 text-base sm:text-lg text-muted leading-7 max-w-xl">
              Spike Terminal analyzes NIFTY 100 price spikes with news, technicals, sector context, and FinBERT sentiment to
              return the most likely cause behind the move.
            </p>

            <div className="mt-8 max-w-lg relative animate-in fade-in slide-in-from-bottom-4 duration-500 delay-150">
              <form onSubmit={handleHeroSearch} className="relative flex items-center shadow-2xl">
                <Search size={22} className="absolute left-4 text-muted" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-surface/80 backdrop-blur border border-border rounded-lg py-4 pl-12 pr-32 text-base text-primary placeholder-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                  placeholder="Enter ticker (e.g. RELIANCE)..."
                />
                <button
                  type="submit"
                  disabled={!searchQuery.trim()}
                  className="absolute right-2 py-2 px-5 bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-bg font-bold rounded-md transition-colors"
                >
                  Analyze
                </button>
              </form>
            </div>
          </div>

          <HeroVerdictCard stock={activeVerdict} index={activeVerdictIndex} />
        </div>
      </section>

      <div className="mt-6">
        {isLoading ? (
          <div className="relative overflow-hidden -mx-6 sm:-mx-8 border-y border-border bg-surface/40">
            <div className="pointer-events-none absolute inset-y-0 left-0 w-16 sm:w-24 bg-gradient-to-r from-bg to-transparent" />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-16 sm:w-24 bg-gradient-to-l from-bg to-transparent" />
            <div className="flex gap-8 py-3 px-6 sm:px-8">
              {Array(12).fill(0).map((_, i) => (
                <Skeleton key={`ticker-skel-${i}`} width={120} height={18} baseColor="var(--color-skeleton-base)" highlightColor="var(--color-skeleton-highlight)" className="opacity-20" />
              ))}
            </div>
          </div>
        ) : (
          <HeroTicker items={tickerTapeItems} />
        )}
      </div>

      <section className="mt-8 lg:mt-10">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MarketStatCard label="Top Gainer" loading={isLoading} value={topGainer ? `${stripTicker(topGainer.ticker)} ${formatPct(topGainer.change)}` : '—'} tone="positive" />
          <MarketStatCard label="Top Loser" loading={isLoading} value={topLoser ? `${stripTicker(topLoser.ticker)} ${formatPct(topLoser.change)}` : '—'} tone="negative" />
          <MarketStatCard label="Avg Gain (Top 5)" loading={isLoading} value={`${formatPct(avgGain)}`} tone={avgGain >= 0 ? 'positive' : 'negative'} />
          <MarketStatCard label="Universe" loading={isLoading} value="100 stocks tracked live" sublabel="NIFTY 100 coverage" />
        </div>
      </section>

      <section className="mt-10 lg:mt-12 grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-10">
        <div>
          <div className="flex items-center gap-3 mb-5 pb-3 border-b border-border">
            <TrendingUp className="text-positive" size={18} />
            <h2 className="text-lg font-bold tracking-tight text-primary">Top Gainers</h2>
            <span className="ml-auto text-xs text-muted font-mono">Live movers</span>
          </div>
          <div className="flex flex-col gap-3">
            {isLoading
              ? Array(5).fill(0).map((_, i) => <MoverSkeleton key={`gainer-skel-${i}`} index={i} />)
              : gainers.slice(0, 5).map((stock, index) => <MoverCard key={stock.ticker} stock={stock} index={index} tone="positive" />)}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-3 mb-5 pb-3 border-b border-border">
            <TrendingDown className="text-negative" size={18} />
            <h2 className="text-lg font-bold tracking-tight text-primary">Top Losers</h2>
            <span className="ml-auto text-xs text-muted font-mono">Live movers</span>
          </div>
          <div className="flex flex-col gap-3">
            {isLoading
              ? Array(5).fill(0).map((_, i) => <MoverSkeleton key={`loser-skel-${i}`} index={i} />)
              : losers.slice(0, 5).map((stock, index) => <MoverCard key={stock.ticker} stock={stock} index={index} tone="negative" />)}
          </div>
        </div>
      </section>

      <section className="mt-12 lg:mt-16 pb-4">
        <div className="flex items-center justify-center gap-4 mb-8">
          <div className="h-px flex-1 bg-border max-w-28" />
          <span className="text-xs font-semibold tracking-[0.3em] text-muted uppercase">How It Works</span>
          <div className="h-px flex-1 bg-border max-w-28" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[
            {
              step: '01',
              icon: Activity,
              title: 'Spike Detection',
              tone: 'text-accent bg-accent/10',
              copy: 'Scans live price and volume bursts across NIFTY 100 to identify unusual movement fast.',
            },
            {
              step: '02',
              icon: Newspaper,
              title: 'News Ingestion',
              tone: 'text-warning bg-warning/10',
              copy: 'Pulls the latest market headlines and company news to capture catalyst context.',
            },
            {
              step: '03',
              icon: BarChart2,
              title: 'Signal Layering',
              tone: 'text-positive bg-positive/10',
              copy: 'Combines technicals, sector movement, and sentiment into a unified signal stack.',
            },
            {
              step: '04',
              icon: Zap,
              title: 'Reason Output',
              tone: 'text-muted bg-surface',
              copy: 'Returns the most likely reason for the move in a clean, analyst-style verdict.',
            },
          ].map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.35, delay: index * 0.08 }}
                className="surface-card p-5"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="px-2.5 py-1 rounded-full bg-bg border border-border text-[11px] font-mono text-muted">
                    Step {item.step}
                  </div>
                  <div className={`h-11 w-11 rounded-xl flex items-center justify-center ${item.tone}`}>
                    <Icon size={18} />
                  </div>
                </div>
                <h3 className="text-base font-bold text-primary mb-2">{item.title}</h3>
                <p className="text-sm text-muted leading-6">{item.copy}</p>
              </motion.div>
            );
          })}
        </div>
      </section>
    </div>
  );
}