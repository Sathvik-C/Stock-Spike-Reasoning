import React, { useState, useEffect } from 'react'
import { stocksAPI } from '../api/client'
import PriceChart from './PriceChart'
import ResearchBrief from './ResearchBrief'
import NewsPanel from './NewsPanel'

export default function StockAnalyzer() {
  const [lookbackDays, setLookbackDays] = useState(1)
  const [topMovers, setTopMovers] = useState(null)
  const [selectedTicker, setSelectedTicker] = useState(null)
  const [stockDetail, setStockDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    handleAnalyze()
  }, [])

  const handleAnalyze = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await stocksAPI.getTopMovers(lookbackDays)
      setTopMovers(response.data)
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  const handleSelectStock = async (ticker) => {
    setLoading(true)
    setError(null)
    try {
      setSelectedTicker(ticker)
      const [analysisRes, chartRes, earningsRes, newsRes, newsSummaryRes, sectorRes, technicalRes] = await Promise.all([
        stocksAPI.getAnalysis(ticker, lookbackDays),
        stocksAPI.getChartData(ticker, Math.max(lookbackDays, 5)),
        stocksAPI.getEarnings(ticker),
        stocksAPI.getNews(ticker, 8),
        stocksAPI.getNewsSummary(ticker),
        stocksAPI.getSector(ticker),
        stocksAPI.getTechnical(ticker),
      ])

      setStockDetail({
        analysis: analysisRes.data,
        chart: chartRes.data,
        earnings: earningsRes.data,
        news: newsRes.data,
        newsSummary: newsSummaryRes.data,
        sector: sectorRes.data,
        technical: technicalRes.data,
      })
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <div className="analyzer-container">
      <h1>📈 Stock Spike Analyzer 2.0</h1>
      <p className="subtitle">Daily market moves decoded into an analyst-style brief.</p>

      <div className="controls">
        <label>
          Lookback Period (days):
          <input
            type="range"
            min="1"
            max="30"
            value={lookbackDays}
            onChange={(e) => setLookbackDays(parseInt(e.target.value))}
          />
          <span>{lookbackDays} days</span>
        </label>
        <button onClick={handleAnalyze} disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze NIFTY100'}
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      {topMovers && (
        <div className="results">
          <h2>Top Movers</h2>
          <div className="movers-grid">
            <div className="gainers">
              <h3>🟢 Top Gainers</h3>
              {topMovers.gainers && topMovers.gainers.map((stock) => (
                <div
                  key={stock.ticker}
                  className="stock-card"
                  onClick={() => handleSelectStock(stock.ticker)}
                >
                  <div className="stock-title">{stock.ticker}</div>
                  <div className="stock-name">{stock.name}</div>
                  <div className="change green">{stock.change > 0 ? '+' : ''}{stock.change}%</div>
                </div>
              ))}
            </div>
            <div className="losers">
              <h3>🔴 Top Losers</h3>
              {topMovers.losers && topMovers.losers.map((stock) => (
                <div
                  key={stock.ticker}
                  className="stock-card"
                  onClick={() => handleSelectStock(stock.ticker)}
                >
                  <div className="stock-title">{stock.ticker}</div>
                  <div className="stock-name">{stock.name}</div>
                  <div className="change red">{stock.change}%</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {stockDetail && (
        <div className="detail-view">
          <div className="detail-header">
            <h2>Research Brief: {selectedTicker}</h2>
            <span className="chip">{lookbackDays}D Window</span>
          </div>

          <div className="detail-grid">
            <div className="card chart-card">
              <PriceChart ticker={selectedTicker} chartData={stockDetail.chart?.data || []} />
            </div>

            <div className="card news-card">
              <NewsPanel news={
                (stockDetail.news?.news?.length > 0 && stockDetail.news.news) ||
                (stockDetail.newsSummary?.top_news?.length > 0 && stockDetail.newsSummary.top_news) ||
                (stockDetail.newsSummary?.news_summary?.articles?.length > 0 && stockDetail.newsSummary.news_summary.articles) ||
                stockDetail.analysis?.top_news ||
                []
              } />
            </div>

            <div className="card research-card">
              <ResearchBrief
                analysis={stockDetail.analysis}
                sectorData={stockDetail.sector?.sector}
                technicalData={stockDetail.technical}
                earningsData={stockDetail.earnings}
              />
            </div>
          </div>
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        .analyzer-container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 28px;
          font-family: 'Sora', sans-serif;
          color: var(--color-primary);
        }

        h1 {
          font-size: 34px;
          margin-bottom: 6px;
          letter-spacing: -0.03em;
        }

        .subtitle {
          margin: 0 0 18px;
          color: var(--color-muted);
        }

        .controls {
          display: flex;
          gap: 20px;
          margin: 20px 0;
          align-items: center;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 14px;
          padding: 14px 16px;
        }

        .controls label {
          display: flex;
          align-items: center;
          gap: 10px;
          color: var(--color-primary);
        }

        .controls input[type="range"] {
          width: 220px;
        }

        .controls button {
          padding: 10px 20px;
          background: var(--color-accent);
          color: var(--color-bg);
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-family: 'Sora', sans-serif;
        }

        .controls button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .movers-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin: 20px 0;
        }

        .stock-card {
          padding: 15px;
          border: 1px solid var(--color-border);
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s;
          background: var(--color-surface);
        }

        .stock-card:hover {
          border-color: var(--color-accent);
          transform: translateY(-2px);
          box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
        }

        .stock-title {
          font-weight: 700;
          color: var(--color-primary);
        }

        .stock-name {
          margin-top: 3px;
          color: var(--color-muted);
          font-size: 12px;
        }

        .change {
          font-weight: 600;
          font-size: 13px;
          margin-top: 10px;
          font-family: 'IBM Plex Mono', monospace;
        }

        .change.green {
          color: var(--color-positive);
        }

        .change.red {
          color: var(--color-negative);
        }

        .error {
          padding: 12px;
          background: var(--color-negative);
          color: var(--color-bg);
          border-radius: 6px;
          margin: 10px 0;
          border: 1px solid var(--color-negative);
          opacity: 0.9;
        }

        .detail-view {
          margin-top: 30px;
          padding: 18px;
          background: var(--color-surface);
          border-radius: 14px;
          border: 1px solid var(--color-border);
        }

        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 14px;
        }

        .chip {
          font-size: 12px;
          font-weight: 600;
          background: var(--color-surface);
          color: var(--color-warning);
          border: 1px solid var(--color-border);
          padding: 6px 10px;
          border-radius: 999px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: 1fr;
          grid-template-areas:
            "chart"
            "news"
            "research";
          gap: 16px;
        }

        .card {
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 12px;
          padding: 14px;
          min-width: 0;
        }

        .chart-card {
          grid-area: chart;
        }

        .news-card {
          grid-area: news;
        }

        .research-card {
          grid-area: research;
        }

        @media (max-width: 900px) {
          .movers-grid {
            grid-template-columns: 1fr;
          }

          .controls {
            flex-direction: column;
            align-items: flex-start;
          }

          .detail-grid {
            grid-template-columns: 1fr;
            grid-template-areas:
              "chart"
              "research"
              "news";
          }

          .chart-card,
          .news-card {
            min-height: auto;
          }
        }
      `}</style>
    </div>
  )
}
