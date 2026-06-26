import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Search } from 'lucide-react';
import ThemeToggle from '../ThemeToggle';

export default function Navbar() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      let formattedQuery = query.trim().toUpperCase();
      if (!formattedQuery.endsWith('.NS')) {
        formattedQuery = `${formattedQuery}.NS`;
      }
      navigate(`/stock/${formattedQuery}`);
      setQuery('');
    }
  };

  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <header className="border-b border-border bg-bg/95 sticky top-0 z-50 backdrop-blur">
      <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
        <div 
          className="flex items-center gap-2 cursor-pointer"
          onClick={() => navigate('/')}
        >
          <div className="w-8 h-8 rounded bg-primary text-bg flex items-center justify-center font-bold text-xl tracking-tighter">
            S
          </div>
          <span className="font-bold text-lg tracking-tight hidden sm:block">Spike<span className="text-muted font-medium">Terminal</span></span>
        </div>

        {!isHome && (
          <form onSubmit={handleSearch} className="relative w-full max-w-sm ml-4">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search size={16} className="text-muted" />
            </div>
            <input 
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-surface border border-border rounded-md py-1.5 pl-10 pr-3 text-sm text-primary placeholder-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              placeholder="Search ticker (e.g. RELIANCE.NS)..."
            />
          </form>
        )}
        <div className="ml-auto flex items-center gap-4">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}