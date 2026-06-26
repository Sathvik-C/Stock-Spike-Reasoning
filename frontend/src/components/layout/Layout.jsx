import React from 'react';
import Navbar from './Navbar';
import { Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div className="bg-bg text-primary min-h-screen flex flex-col font-sans">
      <Navbar />
      <main className="flex-grow pb-24">
        <Outlet />
      </main>
    </div>
  );
}