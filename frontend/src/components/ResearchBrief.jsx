import React from 'react'

const formatReason = (value) => {
  if (!value) return 'unknown'
  return value.replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase())
}

export default function ResearchBrief({ analysis, sectorData, technicalData, earningsData }) {
  if (!analysis) {
    return <div>No analysis available</div>
  }

  const technical = technicalData?.signals || analysis?.signals?.technical || {}
  const earnings = earningsData?.earnings || analysis?.signals?.earnings || {}
  const sector = sectorData || analysis?.signals?.sector || {}

  return (
    <div className="research-brief">
      <div className="brief-header">
        <h2>{analysis.ticker} Brief</h2>
        <div className="change" style={{ color: analysis.price_change > 0 ? '#10b981' : '#ef4444' }}>
          {analysis.price_change > 0 ? '+' : ''}{analysis.price_change}%
        </div>
      </div>

      <div className="reason-section">
        <h3>💡 Why Did It Move?</h3>
        <div className="reason-card">
          <div className="reason-category">{formatReason(analysis.reason_category)}</div>
          <div className="reason-confidence">Confidence: {analysis.reason_confidence}%</div>
          <p>{analysis.reason_detail}</p>
        </div>
      </div>

      <div className="grid-2">
        <div>
          <h3>📰 Sector Context</h3>
          <p>
            {sector?.sector_ticker || 'N/A'} {typeof sector?.sector_change_pct === 'number' ? `${sector.sector_change_pct > 0 ? '+' : ''}${sector.sector_change_pct}%` : ''}
          </p>
          <p>
            Relative: {typeof sector?.relative_performance_pct === 'number' ? `${sector.relative_performance_pct > 0 ? '+' : ''}${sector.relative_performance_pct}%` : 'N/A'}
          </p>
        </div>
        <div>
          <h3>📈 Technical Signals</h3>
          <ul>
            <li>RSI: {typeof technical?.rsi === 'number' ? technical.rsi.toFixed(2) : 'N/A'}</li>
            <li>MACD: {technical?.macd_signal || 'N/A'}</li>
            <li>Volume Ratio: {technical?.volume_ratio || 'N/A'}x</li>
            <li>Bollinger: {technical?.bollinger_position || 'N/A'}</li>
            <li>{technicalData?.summary || analysis?.signals?.technical?.summary || 'No breakout summary available'}</li>
          </ul>
        </div>
      </div>

      <div className="earnings-section">
        <h3>📊 Quarterly Earnings</h3>
        {!earnings ? (
          <p>Earnings data unavailable</p>
        ) : (
          <ul>
            <li>Recent release: {earningsData?.recent_release || earnings?.fired ? 'Yes' : 'No'}</li>
            <li>Quarter end: {earnings?.quarter_end || earnings?.calendar_date || 'N/A'}</li>
            <li>Total revenue: {typeof earnings?.total_revenue === 'number' ? earnings.total_revenue.toLocaleString() : 'N/A'}</li>
            <li>Net income: {typeof earnings?.net_income === 'number' ? earnings.net_income.toLocaleString() : 'N/A'}</li>
            <li>Operating income: {typeof earnings?.operating_income === 'number' ? earnings.operating_income.toLocaleString() : 'N/A'}</li>
            
            {/* BSE Filing PDF Link */}
            {earningsData?.bse_filing?.attachment_url && (
              <li style={{ marginTop: '8px' }}>
                <a 
                  href={earningsData.bse_filing.attachment_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 'bold' }}
                >
                  📄 View Official BSE PDF
                </a>
                <div style={{ fontSize: '11px', opacity: 0.7, marginTop: '2px' }}>
                  {earningsData.bse_filing.headline}
                </div>
              </li>
            )}
          </ul>
        )}
      </div>

      <style>{`
        .brief-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .reason-card {
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 10px;
          padding: 12px;
        }

        .reason-category {
          font-weight: 700;
          margin-bottom: 3px;
          color: var(--color-primary);
        }

        .reason-confidence {
          font-size: 12px;
          color: var(--color-warning);
          margin-bottom: 8px;
        }

        .grid-2 {
          margin-top: 10px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .grid-2 > div,
        .earnings-section {
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 10px;
          padding: 10px;
        }

        .earnings-section {
          margin-top: 12px;
        }

        .research-brief h3 {
          color: var(--color-primary);
        }

        .research-brief p,
        .research-brief li {
          color: var(--color-muted);
        }

        @media (max-width: 900px) {
          .grid-2 {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  )
}
