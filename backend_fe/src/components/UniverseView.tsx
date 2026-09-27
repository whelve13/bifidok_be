import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Building,
  CheckCircle2,
  ChevronRight,
  Download,
  ExternalLink,
  Filter,
  Layers,
  Network,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react';
import { CommercialOffering, PerfectCustomerDossier } from '../types';

interface UniverseViewProps {
  offerings: CommercialOffering[];
  selectedOfferingKey: string;
  onSelectOfferingKey: (key: string) => void;
  rankedCustomers: PerfectCustomerDossier[];
  isLoading: boolean;
  onRefreshUniverse: () => void;
  onSelectDossier: (dossier: PerfectCustomerDossier) => void;
  onInspectConnectors: (companyName: string, domain?: string) => void;
  onStageOutreach: (dossier: PerfectCustomerDossier) => void;
  onCreateNewOffer: () => void;
}

export const UniverseView: React.FC<UniverseViewProps> = ({
  offerings,
  selectedOfferingKey,
  onSelectOfferingKey,
  rankedCustomers,
  isLoading,
  onRefreshUniverse,
  onSelectDossier,
  onInspectConnectors,
  onStageOutreach,
  onCreateNewOffer,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [minScore, setMinScore] = useState<number>(0);
  const [sectorFilter, setSectorFilter] = useState<string>('ALL');
  const [solvencyFilter, setSolvencyFilter] = useState<'ALL' | 'SOLVENT' | 'DISQUALIFIED'>('ALL');

  const activeOffering = offerings.find(
    (o) => o.key === selectedOfferingKey || o.id === selectedOfferingKey
  ) || offerings[0];

  // Distinct sectors from current ranked customers
  const distinctSectors = useMemo(() => {
    const set = new Set<string>();
    rankedCustomers.forEach((c) => {
      if (c.company.sector) set.add(c.company.sector);
    });
    return Array.from(set);
  }, [rankedCustomers]);

  // Filtered customer list
  const filteredCustomers = useMemo(() => {
    return rankedCustomers.filter((c) => {
      if (minScore > 0 && c.propensity_score < minScore) return false;
      if (
        searchTerm &&
        !c.company.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !c.company.domain.toLowerCase().includes(searchTerm.toLowerCase())
      ) {
        return false;
      }
      if (sectorFilter !== 'ALL' && c.company.sector !== sectorFilter) {
        return false;
      }
      if (solvencyFilter === 'SOLVENT' && !c.company.is_solvent) return false;
      if (solvencyFilter === 'DISQUALIFIED' && !c.is_disqualified) return false;
      return true;
    });
  }, [rankedCustomers, minScore, searchTerm, sectorFilter, solvencyFilter]);

  // Aggregate stats
  const totalCount = rankedCustomers.length;
  const tier1Count = rankedCustomers.filter((c) => c.tier === 'Tier 1 Prime Target' && !c.is_disqualified).length;
  const tier2Count = rankedCustomers.filter((c) => c.tier === 'Tier 2 Strategic Lead' && !c.is_disqualified).length;
  const disqualifiedCount = rankedCustomers.filter((c) => c.is_disqualified).length;

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(filteredCustomers, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `prospect_universe_${selectedOfferingKey}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6">
      {/* Top Bar: Offering Selection & Action Buttons */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
            Target Commercial Offering
          </label>
          <div className="flex items-center gap-3">
            <select
              value={selectedOfferingKey}
              onChange={(e) => onSelectOfferingKey(e.target.value)}
              className="px-3.5 py-2 text-sm font-semibold text-slate-900 bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-orange-500 focus:outline-none min-w-[280px]"
            >
              {offerings.map((off) => (
                <option key={off.key} value={off.key}>
                  {off.title} {off.is_custom ? '(Custom)' : ''}
                </option>
              ))}
            </select>

            <button
              onClick={onCreateNewOffer}
              className="text-xs font-semibold px-3 py-2 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors"
            >
              + Create Custom Mandate
            </button>
          </div>
          {activeOffering && (
            <p className="text-xs text-slate-500 mt-2 line-clamp-1">
              {activeOffering.description}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 self-stretch md:self-auto justify-end">
          <button
            onClick={onRefreshUniverse}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors"
            title="Scan live public signals and recalculate propensity"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Scanning...' : 'Rescan Universe'}</span>
          </button>

          <button
            onClick={handleExportJson}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors"
            title="Export ranked customer universe to JSON"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Total Evaluated
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 mt-1">
            {totalCount}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Public multi-source candidate universe
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
          <div className="text-xs font-medium text-emerald-600 uppercase tracking-wider flex items-center justify-between">
            <span>Tier 1 Prime Targets</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-600 mt-1">
            {tier1Count}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Propensity score 80 or higher
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
          <div className="text-xs font-medium text-amber-600 uppercase tracking-wider flex items-center justify-between">
            <span>Tier 2 Strategic</span>
            <span className="w-2 h-2 rounded-full bg-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-600 mt-1">
            {tier2Count}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Propensity score 60 to 79
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs">
          <div className="text-xs font-medium text-rose-600 uppercase tracking-wider flex items-center justify-between">
            <span>Disqualified / Locked</span>
            <span className="w-2 h-2 rounded-full bg-rose-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-600 mt-1">
            {disqualifiedCount}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Insolvency or negative signal gate
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 flex-1 min-w-[240px]">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by enterprise name or domain (e.g. DHL, Siemens)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-orange-500 focus:outline-none"
            />
          </div>

          {distinctSectors.length > 0 && (
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded focus:outline-none text-slate-700"
            >
              <option value="ALL">All Sectors</option>
              {distinctSectors.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>
          )}

          <select
            value={solvencyFilter}
            onChange={(e) => setSolvencyFilter(e.target.value as any)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded focus:outline-none text-slate-700"
          >
            <option value="ALL">All Solvency States</option>
            <option value="SOLVENT">Active / Solvent Only</option>
            <option value="DISQUALIFIED">Disqualified Only</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-500 font-medium">Min Score:</span>
          <input
            type="range"
            min="0"
            max="95"
            step="5"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-24 accent-orange-600"
          />
          <span className="font-mono font-bold text-slate-700 w-8 text-right">
            {minScore}
          </span>
        </div>
      </div>

      {/* Main Enterprise Data Grid */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4 w-12 text-center">Rank</th>
                <th className="py-3 px-4">Enterprise Account</th>
                <th className="py-3 px-4 text-center">Propensity Score</th>
                <th className="py-3 px-4">Tier Status</th>
                <th className="py-3 px-4">Primary Commercial Wedge</th>
                <th className="py-3 px-4 text-center">Solvency</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCustomers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No enterprise accounts matching your search or filters.
                  </td>
                </tr>
              ) : (
                filteredCustomers.map((dossier, idx) => {
                  const score = dossier.propensity_score;
                  const isDisq = dossier.is_disqualified;

                  let scoreBadgeColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
                  let tierColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';

                  if (isDisq) {
                    scoreBadgeColor = 'text-rose-700 bg-rose-50 border-rose-200';
                    tierColor = 'text-rose-700 bg-rose-50 border-rose-200';
                  } else if (score < 60) {
                    scoreBadgeColor = 'text-amber-700 bg-amber-50 border-amber-200';
                    tierColor = 'text-amber-700 bg-amber-50 border-amber-200';
                  } else if (score < 80) {
                    scoreBadgeColor = 'text-sky-700 bg-sky-50 border-sky-200';
                    tierColor = 'text-sky-700 bg-sky-50 border-sky-200';
                  }

                  return (
                    <tr
                      key={dossier.company.domain || idx}
                      className="hover:bg-slate-50 transition-colors group cursor-pointer"
                      onClick={() => onSelectDossier(dossier)}
                    >
                      <td className="py-3 px-4 text-center font-mono font-bold text-slate-400">
                        #{idx + 1}
                      </td>

                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900 group-hover:text-orange-600 transition-colors">
                          {dossier.company.name}
                        </div>
                        <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>{dossier.company.domain}</span>
                          {dossier.company.headcount && (
                            <span className="text-slate-500">
                              ({dossier.company.headcount.toLocaleString()} HC)
                            </span>
                          )}
                          {dossier.company.country && (
                            <span className="px-1 bg-slate-100 rounded text-slate-600 uppercase text-[10px]">
                              {dossier.company.country}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center gap-1.5">
                          <span
                            className={`font-mono font-bold text-sm px-2 py-0.5 rounded border ${scoreBadgeColor}`}
                          >
                            {score.toFixed(1)}
                          </span>
                        </div>
                        <div className="w-16 bg-slate-100 h-1.5 rounded-full overflow-hidden mx-auto mt-1.5">
                          <div
                            className={`h-full ${
                              isDisq
                                ? 'bg-rose-500'
                                : score >= 80
                                ? 'bg-emerald-500'
                                : score >= 60
                                ? 'bg-sky-500'
                                : 'bg-amber-500'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(5, score))}%` }}
                          />
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 text-[11px] font-semibold rounded border ${tierColor}`}
                        >
                          {dossier.tier}
                        </span>
                        {isDisq && (
                          <div className="text-[10px] text-rose-600 truncate max-w-xs mt-0.5">
                            {dossier.disqualification_reason}
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-800 line-clamp-1">
                          {dossier.primary_commercial_wedge?.name || 'Turnkey Enterprise Modernization'}
                        </div>
                        <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                          {dossier.primary_commercial_wedge?.value_driver}
                        </div>
                      </td>

                      <td className="py-3 px-4 text-center">
                        {dossier.company.is_solvent ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Solvent</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                            <AlertTriangle className="w-3 h-3 text-rose-600" />
                            <span>Insolvent</span>
                          </span>
                        )}
                      </td>

                      <td
                        className="py-3 px-4 text-right space-x-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => onSelectDossier(dossier)}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                          title="View complete account sales dossier"
                        >
                          Dossier
                        </button>
                        <button
                          onClick={() => onInspectConnectors(dossier.company.name, dossier.company.domain)}
                          className="px-2 py-1 text-xs rounded border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors"
                          title="Inspect live 8-source connector signals"
                        >
                          <Network className="w-3 h-3" />
                        </button>
                        {!isDisq && (
                          <button
                            onClick={() => onStageOutreach(dossier)}
                            className="px-2 py-1 text-xs font-semibold rounded bg-orange-600 hover:bg-orange-700 text-white transition-colors"
                            title="Stage pitch draft for human review"
                          >
                            Pitch
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
