import React from 'react';
import {
  Building2,
  Cpu,
  Layers,
  Mail,
  Network,
  Radar,
  Sliders,
} from 'lucide-react';

export type NavTab =
  | 'universe'
  | 'matcher'
  | 'configurator'
  | 'connectors'
  | 'outreach'
  | 'ml_engine';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  queueCount?: number;
  customOfferCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  queueCount = 0,
  customOfferCount = 0,
}) => {
  const navItems = [
    {
      id: 'universe' as NavTab,
      label: 'Prospect Universe',
      description: 'Account ranking and signal scoring',
      icon: Radar,
    },
    {
      id: 'matcher' as NavTab,
      label: 'Business Matcher',
      description: 'Find best offer for enterprise',
      icon: Building2,
    },
    {
      id: 'configurator' as NavTab,
      label: 'Commercial Offers',
      description: 'Zero preset offer configurator',
      icon: Sliders,
      badge: customOfferCount > 0 ? `${customOfferCount} Custom` : undefined,
    },
    {
      id: 'connectors' as NavTab,
      label: 'Connector Audit',
      description: '8 source live OSINT telemetry',
      icon: Network,
    },
    {
      id: 'outreach' as NavTab,
      label: 'HitL Outreach Queue',
      description: 'Human approval and pitch review',
      icon: Mail,
      badge: queueCount > 0 ? `${queueCount}` : undefined,
      badgeColor: 'bg-orange-100 text-orange-700',
    },
    {
      id: 'ml_engine' as NavTab,
      label: 'Local ML Engine',
      description: 'Models, weights, and training',
      icon: Cpu,
    },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col justify-between shrink-0 select-none">
      <div className="p-4">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 mb-2">
          Navigation Modules
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-left transition-colors ${
                  isActive
                    ? 'bg-orange-600 text-white font-semibold'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`w-4 h-4 shrink-0 ${
                      isActive ? 'text-white' : 'text-slate-400'
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="text-sm truncate leading-tight">
                      {item.label}
                    </div>
                    <div
                      className={`text-[11px] truncate leading-tight mt-0.5 ${
                        isActive ? 'text-orange-100' : 'text-slate-400'
                      }`}
                    >
                      {item.description}
                    </div>
                  </div>
                </div>

                {item.badge && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ml-2 ${
                      isActive
                        ? 'bg-white text-orange-700'
                        : item.badgeColor || 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-800 text-xs text-slate-400">
        <div className="flex items-center justify-between mb-1">
          <span className="font-semibold text-slate-300">Model Runtime:</span>
          <span className="font-mono text-emerald-400">LightGBM v4</span>
        </div>
        <div className="flex items-center justify-between mb-1">
          <span className="font-semibold text-slate-300">Protocol:</span>
          <span className="font-mono text-slate-400">Model Context (MCP)</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-300">Tenant:</span>
          <span className="font-mono text-orange-400">Orange Systems Cloud</span>
        </div>
      </div>
    </aside>
  );
};
