import axios from 'axios'

// In local dev, Vite proxies /api to localhost:8000.
// In production, set VITE_API_URL to the deployed backend URL (e.g. https://stock-spike-backend.onrender.com/api)
const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Stocks API
export const stocksAPI = {
  list: () => apiClient.get('/stocks/'),
  getTopMovers: (lookbackDays = 1, topN = 5) =>
    apiClient.get('/stocks/top-movers', { params: { lookback_days: lookbackDays, top_n: topN } }),
  getAnalysis: (ticker, lookbackDays = 1) =>
    apiClient.get(`/stocks/${ticker}/analysis`, { params: { lookback_days: lookbackDays } }),
  getChartData: (ticker, lookbackDays = 1) =>
    apiClient.get(`/stocks/${ticker}/chart-data`, { params: { lookback_days: lookbackDays } }),
  getEarnings: (ticker) =>
    apiClient.get(`/stocks/${ticker}/earnings`),
  getNews: (ticker, limit = 10) =>
    apiClient.get(`/stocks/${ticker}/news`, { params: { limit } }),
  getNewsSummary: (ticker) =>
    apiClient.get(`/stocks/${ticker}/news-summary`),
  getSector: (ticker) =>
    apiClient.get(`/stocks/${ticker}/sector`),
  getTechnical: (ticker) =>
    apiClient.get(`/stocks/${ticker}/technical`),
  getClusters: () =>
    apiClient.get(`/stocks/clusters`),
}
