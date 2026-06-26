import React from 'react'

export default function NewsPanel({ news }) {
  if (!news || news.length === 0) {
    return <div>No news available</div>
  }

  return (
    <div className="news-panel">
      <h3>📰 Top News & Analysis</h3>
      <div className="news-list">
        {news.map((article, idx) => (
          <div key={idx} className="news-item">
            <div className="news-header">
              <h4>
                <a href={article.link || article.url} target="_blank" rel="noopener noreferrer">
                  {article.title}
                </a>
              </h4>
            </div>
            <div className="news-meta">
              <span className="source">{article.source}</span>
              <span className={`sentiment ${article.sentiment_label || 'neutral'}`}>
                <strong>FinBERT Score:</strong> {article.sentiment_label || 'neutral'} ({typeof article.sentiment_score === 'number' ? article.sentiment_score.toFixed(2) : '0.00'})
              </span>
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .news-list {
          display: grid;
          gap: 10px;
        }

        .news-item {
          border: 1px solid var(--color-border);
          border-radius: 10px;
          padding: 10px;
          background: var(--color-surface);
        }

        .news-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 8px;
        }

        .news-header h4 {
          margin: 0;
          font-size: 15px;
          line-height: 1.4;
        }

        .news-header h4 a {
          color: var(--color-primary);
          text-decoration: none;
          transition: color 0.2s;
        }

        .news-header h4 a:hover {
          color: var(--color-accent);
          text-decoration: underline;
        }

        .news-meta {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          color: var(--color-muted);
        }

        .sentiment.positive {
          color: var(--color-positive);
        }

        .sentiment.negative {
          color: var(--color-negative);
        }

        .sentiment.neutral {
          color: var(--color-muted);
        }
      `}</style>
    </div>
  )
}
