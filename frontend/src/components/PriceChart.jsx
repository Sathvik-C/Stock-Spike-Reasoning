import React from 'react'
import Plot from 'react-plotly.js'

export default function PriceChart({ ticker, chartData }) {
  if (!chartData || chartData.length === 0) {
    return <div>Loading chart...</div>
  }

  const dates = chartData.map((d) => d.date)
  const closes = chartData.map((d) => d.close)

  const firstClose = closes[0]
  const lastClose = closes[closes.length - 1]
  const isUp = typeof firstClose === 'number' && typeof lastClose === 'number' && lastClose >= firstClose
  const lineColor = isUp ? '#059669' : '#dc2626'

  return (
    <div className="price-chart">
      <h3>📊 {ticker} Price Movement</h3>
      <Plot
        data={[
          {
            x: dates,
            y: closes,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Close',
            line: { color: lineColor, width: 2.5 },
            marker: { color: lineColor, size: 5 },
          },
        ]}
        layout={{
          title: `${ticker} Price Chart (Daily)`,
          xaxis: {
            title: 'Date',
            showgrid: false,
            type: 'date',
          },
          yaxis: {
            title: 'Price (₹)',
            autorange: true,
            fixedrange: false,
          },
          hovermode: 'x unified',
          autosize: true,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { l: 50, r: 50, t: 50, b: 50 },
          showlegend: false,
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%', height: '400px' }}
      />
    </div>
  )
}
