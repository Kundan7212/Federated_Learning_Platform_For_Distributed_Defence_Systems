import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard, FlaskConical, Play, Shield, LogOut,
  Menu, X, Cpu, ChevronRight, BookOpen,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';

const NAV = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard'   },
  { to: '/experiments', icon: FlaskConical,    label: 'Experiments' },
  { to: '/training',    icon: Play,            label: 'New Training' },
  { to: '/privacy',     icon: Shield,          label: 'Privacy'     },
  { to: '/algorithms',  icon: BookOpen,        label: 'Algorithms'  },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-[#030712] overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className={clsx(
          'flex flex-col bg-[#0a0f1e] border-r border-[#1e293b] transition-all duration-300 flex-shrink-0',
          collapsed ? 'w-16' : 'w-64',
        )}
      >
        {/* Logo */}
        <div
          className={clsx(
            'flex items-center border-b border-[#1e293b]',
            collapsed ? 'flex-col gap-2 px-2 py-4' : 'gap-3 px-4 py-5',
          )}
        >
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
            <Cpu size={16} className="text-cyan-400" />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <p className="text-xs font-bold text-cyan-400 tracking-widest uppercase">Defence FL</p>
              <p className="text-[10px] text-slate-500 tracking-wider">Intelligence Platform</p>
            </div>
          )}
          <button
            onClick={() => setCollapsed(c => !c)}
            className={clsx(
              'text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0',
              !collapsed && 'ml-auto',
            )}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={16} /> : <Menu size={16} />}
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx('nav-item', isActive && 'active', collapsed && 'justify-center px-2')
              }
              title={collapsed ? label : undefined}
            >
              <Icon size={18} className="flex-shrink-0" />
              {!collapsed && <span className="text-sm font-medium">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-[#1e293b] p-3">
          <div className={clsx('flex items-center gap-3', collapsed && 'justify-center')}>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-600 to-blue-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
              {user?.username?.[0]?.toUpperCase() ?? 'U'}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{user?.username}</p>
                <p className="text-xs text-slate-500 truncate">{user?.email}</p>
              </div>
            )}
            <button
              onClick={logout}
              className="text-slate-500 hover:text-red-400 transition-colors flex-shrink-0"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-14 border-b border-[#1e293b] bg-[#0a0f1e]/80 backdrop-blur-sm flex items-center px-6 gap-4 flex-shrink-0">
          {/* Animated status dot */}
          <div className="flex items-center gap-2 ml-auto">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-xs text-slate-500">SYSTEM ONLINE</span>
          </div>
          <div className="h-4 w-px bg-[#1e293b]" />
          <span className="text-xs font-mono text-slate-500">
            {new Date().toLocaleTimeString('en-GB', { hour12: false })}
          </span>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto hex-bg">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
