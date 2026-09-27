import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, RefreshCw, X, XCircle } from 'lucide-react';
import { DiagnosticsReport } from '../types';
import { getSystemHealth } from '../services/api';

interface DoctorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DoctorModal: React.FC<DoctorModalProps> = ({ isOpen, onClose }) => {
  const [diag, setDiag] = useState<DiagnosticsReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchDoctor = async () => {
    setIsLoading(true);
    try {
      const res = await getSystemHealth();
      setDiag(res);
    } catch (err) {
      console.error('Doctor fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDoctor();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150 text-xs">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-orange-600" />
            <h2 className="font-bold text-slate-900 text-sm uppercase tracking-wider">
              System Preflight Diagnostics
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded border border-slate-200">
            <div>
              <span className="text-[11px] font-bold uppercase text-slate-500 block">
                Overall Platform Status
              </span>
              <span className="font-bold text-sm text-slate-900">
                {diag?.status || 'HEALTHY'}
              </span>
            </div>
            <button
              onClick={fetchDoctor}
              disabled={isLoading}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-white border border-slate-200 text-slate-700 hover:bg-slate-100"
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Rerun Probes</span>
            </button>
          </div>

          <div className="space-y-2">
            <div className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">
              Subsystem Probes
            </div>

            {diag?.components &&
              Object.entries(diag.components).map(([compName, details]) => {
                const isUp = details.status === 'UP' || details.status === 'CONFIGURED';

                return (
                  <div
                    key={compName}
                    className="p-3 rounded border border-slate-200 bg-white flex items-center justify-between"
                  >
                    <div>
                      <div className="font-bold text-slate-900 capitalize">
                        {compName}
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        {details.dialect && `Dialect: ${details.dialect} | `}
                        {details.company_count !== undefined &&
                          `Companies: ${details.company_count} | `}
                        {details.active_count !== undefined &&
                          `Active Connectors: ${details.active_count} | `}
                        Status: {details.status}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {isUp ? (
                        <span className="flex items-center gap-1 font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>UP</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 text-[11px]">
                          <XCircle className="w-3.5 h-3.5 text-amber-600" />
                          <span>DEGRADED</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-slate-900 text-white font-semibold text-xs hover:bg-slate-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
