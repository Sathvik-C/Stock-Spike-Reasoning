import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import clsx from 'clsx';
import { stocksAPI } from '../../api/client';
import Skeleton from 'react-loading-skeleton';
import { keepPreviousData } from '@tanstack/react-query';

const PERIODS = [
  { label: '1D', days: 1 },
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
];

const CustomTooltip = ({ active, payload, label, activePeriod }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const dateStr = new Date(data.date).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      ...(activePeriod?.days === 1 && { hour: '2-digit', minute: '2-digit' })
    });
    return (
      <div className="bg-surface border border-border p-3 rounded-[8px] shadow-xl shadow-black/20 text-xs">
        <p className="text-muted mb-1 font-mono tracking-tight">{dateStr}</p>
        <p className="font-mono text-primary font-bold text-sm">
          ₹{data.close.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </p>
      </div>
    );
  }
  return null;
};

export default function PriceChart({ ticker, dayChange }) {
  const [activePeriod, setActivePeriod] = useState(PERIODS[0]); // Default 1D

  const { data, isLoading, isError } = useQuery({
    queryKey: ['chart', ticker, activePeriod.days],
    queryFn: () =>
      stocksAPI.getChartData(ticker, activePeriod.days).then((res) => res.data),
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });

  if (isError) {
    return (
      <div className="w-full h-[280px] flex items-center justify-center surface-card border-negative/30 bg-negative/5 text-negative">
        Failed to load chart data for {ticker}.
      </div>
    );
  }

  // Determine line color based on start to end return over the chosen period
  let isPositive = true;
  let chartData = [];
  let pctChange = 0;
  
  if (data?.data && Array.isArray(data.data)) {
    chartData = data.data;

    const backendPct = Number(data.pct_change);
    if (Number.isFinite(backendPct)) {
      pctChange = backendPct;
      isPositive = pctChange >= 0;
    } else if (activePeriod.days === 1 && Number.isFinite(Number(dayChange))) {
      pctChange = Number(dayChange);
      isPositive = pctChange >= 0;
    } else if (chartData.length > 1) {
      const firstClose = chartData[0].close;
      const lastClose = chartData[chartData.length - 1].close;
      isPositive = lastClose >= firstClose;
      pctChange = ((lastClose - firstClose) / firstClose) * 100;
    }
  }

  const strokeColor = isPositive ? '#22c55e' : '#ef4444'; // positive mapping: green, negative: red

  return (
    <div className="w-full flex flex-col gap-4 mt-6">
      {/* Tabs & Returns */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          {PERIODS.map((period) => (
            <button
              key={period.label}
              onClick={() => setActivePeriod(period)}
              className={clsx(
                'px-3 py-1 rounded text-xs font-semibold tracking-wide transition-colors',
                activePeriod.label === period.label
                  ? 'bg-neutral text-primary'
                  : 'text-muted hover:text-primary hover:bg-neutral/20'
              )}
            >
              {period.label}
            </button>
          ))}
        </div>
        
        {chartData.length > 1 && !isLoading && (
          <div className={clsx(
            "text-sm font-bold tabular-nums font-mono px-2.5 py-1 rounded-md border", 
            isPositive ? "text-positive border-positive/20 bg-positive/10" : "text-negative border-negative/20 bg-negative/10"
          )}>
            {isPositive ? '+' : ''}{pctChange.toFixed(2)}%
          </div>
        )}
      </div>

      {/* Chart Area */}
      <div className="w-full h-[280px]">
        {isLoading || !chartData.length ? (
          <Skeleton
            height="100%"
            className="rounded-lg opacity-10"
            baseColor="var(--color-skeleton-base)"
            highlightColor="var(--color-skeleton-highlight)"
          />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              {/* Only subtle horizontal gridlines */}
              <CartesianGrid stroke="var(--color-chart-grid)" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(val) => {
                  const d = new Date(val);
                  if (activePeriod.days === 1) {
                    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
                  }
                  return activePeriod.days > 90
                    ? d.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })
                    : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                }}
                stroke="var(--color-chart-axis)"
                tick={{ fill: 'var(--color-chart-axis)', fontSize: 10, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
              />
              <YAxis
                domain={['auto', 'auto']}
                stroke="var(--color-chart-axis)"
                tick={{ fill: 'var(--color-chart-axis)', fontSize: 10, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => val.toLocaleString('en-IN')}
                orientation="right"
                width={50}
              />
              <Tooltip content={<CustomTooltip activePeriod={activePeriod} />} cursor={{ stroke: 'var(--color-chart-cursor)' }} />
              <Line
                type="linear"
                dataKey="close"
                stroke={strokeColor}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: strokeColor, stroke: 'var(--color-chart-dot-stroke)', strokeWidth: 2 }}
                isAnimationActive={true}
                animationDuration={600}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}