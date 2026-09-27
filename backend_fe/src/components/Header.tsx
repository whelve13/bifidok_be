import React from 'react';

interface HeaderProps {
  activeOfferingTitle?: string;
  onOpenNewOffer?: () => void;
  onOpenDoctor?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ activeOfferingTitle }) => {
  return (
    <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center sticky top-0 z-30 shadow-xs">
      <div className="flex items-center gap-4">
        <span className="font-bold text-slate-900 tracking-tight text-base leading-none">
          ORANGE SYSTEMS
        </span>

        {activeOfferingTitle && (
          <div className="flex items-center gap-2 ml-4 pl-4 border-l border-slate-200">
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
              Active Mandate:
            </span>
            <span className="text-xs font-semibold text-slate-800 bg-slate-100 px-2.5 py-1 rounded border border-slate-200 max-w-sm truncate">
              {activeOfferingTitle}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
