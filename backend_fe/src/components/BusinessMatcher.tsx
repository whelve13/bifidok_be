import React, { useState } from 'react';
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Layers,
  Search,
  Sparkles,
} from 'lucide-react';
import { BestOfferMatchResult, PerfectCustomerDossier } from '../types';
import { matchBestOffer } from '../services/api';

interface BusinessMatcherProps {
  onSelectDossier: (dossier: PerfectCustomerDossier) => void;
  onInspectConnectors: (companyName: string) => void;
}

export const BusinessMatcher: React.FC<BusinessMatcherProps> = ({
  onSelectDossier,
  onInspectConnectors,
}) => {
  const [companyInput, setCompanyInput] = useState('DHL Group');
  const [isLoading, setIsLoading] = useState(false);
  const [matchResult, setMatchResult] = useState<BestOfferMatchResult | null>(null);

  const sampleCompanies = [
    'DHL Group',
    'Siemens AG',
    'BASF SE',
    'Zalando SE',
    'Lufthansa Group',
    'Galeria Karstadt Kaufhof',
  ];

  const handleRunMatch = async (companyName: string = companyInput) => {
    if (!companyName.trim()) return;
    setIsLoading(true);
    try {
      const res = await matchBestOffer(companyName.trim());
      setMatchResult(res);
    } catch (err) {
      console.error('Match error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <Building2 className="w-5 h-5 text-orange-600" />
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Enterprise to Commercial Offer Matcher
          </h1>
        </div>
        <p className="text-xs text-slate-500">
          Evaluates a target enterprise across all candidate commercial offerings using trained local ML models, multi-source evidence harvesting, and operational fit analysis.
        </p>
      </div>

      {/* Input & Search Section */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-4">
        <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
          Target Enterprise Name or Domain
        </label>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Enter company name (e.g. DHL Group, Siemens AG, BASF SE, BMW)..."
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRunMatch()}
              className="w-full pl-10 pr-4 py-2.5 text-xs bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-orange-500 focus:outline-none font-semibold text-slate-900"
            />
          </div>

          <button
            onClick={() => handleRunMatch()}
            disabled={isLoading || !companyInput.trim()}
            className="flex items-center gap-2 px-6 py-2.5 text-xs font-bold rounded bg-orange-600 hover:bg-orange-700 text-white transition-colors shadow-xs disabled:opacity-50"
          >
            <span>{isLoading ? 'Evaluating Fit...' : 'Find Best Offer'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Quick presets badges */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
          <span className="text-slate-400 font-medium mr-1">Quick Select:</span>
          {sampleCompanies.map((c) => (
            <button
              key={c}
              onClick={() => {
                setCompanyInput(c);
                handleRunMatch(c);
              }}
              className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors"
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Matching Results */}
      {matchResult && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Top Recommendation Highlight Panel */}
          {matchResult.offerings_ranking.length > 0 && (
            <div className="p-6 bg-white border border-emerald-300 rounded-lg shadow-xs relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-emerald-500 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-bl">
                Top Commercial Match
              </div>

              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">
                    Highest Readiness Offering for {matchResult.company_name}
                  </div>
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight mt-1">
                    {matchResult.top_recommended_offering}
                  </h2>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-2xl font-extrabold font-mono text-emerald-600">
                      {matchResult.top_score.toFixed(1)}
                    </div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      {matchResult.top_tier}
                    </div>
                  </div>

                  <button
                    onClick={() => onSelectDossier(matchResult.offerings_ranking[0].dossier)}
                    className="px-4 py-2 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                  >
                    View Full Dossier
                  </button>
                </div>
              </div>

              <div className="mt-4 text-xs text-slate-600 space-y-2">
                <p className="font-medium text-slate-800">
                  {matchResult.recommendation_summary}
                </p>

                {matchResult.offerings_ranking[0].primary_commercial_wedge && (
                  <div className="p-3 bg-emerald-50/50 rounded border border-emerald-100 text-emerald-950 mt-2">
                    <span className="font-bold">Recommended Commercial Wedge: </span>
                    <span>
                      {matchResult.offerings_ranking[0].primary_commercial_wedge.name}
                    </span>
                    <div className="text-[11px] text-emerald-800 mt-0.5">
                      {matchResult.offerings_ranking[0].primary_commercial_wedge.value_driver}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Full Commercial Offerings Comparison Table */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800 uppercase tracking-wider">
                Candidate Commercial Offerings Comparison ({matchResult.offerings_ranking.length})
              </span>
              <button
                onClick={() => onInspectConnectors(matchResult.company_name)}
                className="flex items-center gap-1 font-semibold text-slate-600 hover:text-slate-900"
              >
                <span>Live Connector Telemetry</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4 w-12 text-center">Rank</th>
                    <th className="py-3 px-4">Commercial Offering</th>
                    <th className="py-3 px-4 text-center">Propensity</th>
                    <th className="py-3 px-4">Tier Status</th>
                    <th className="py-3 px-4">Primary Commercial Wedge</th>
                    <th className="py-3 px-4">Recommendation</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {matchResult.offerings_ranking.map((item, idx) => {
                    const isTop = idx === 0 && !item.is_disqualified;
                    const isDisq = item.is_disqualified;

                    return (
                      <tr
                        key={item.offering_key}
                        className={`hover:bg-slate-50 transition-colors ${
                          isTop ? 'bg-emerald-50/20' : ''
                        }`}
                      >
                        <td className="py-3 px-4 text-center font-mono font-bold text-slate-400">
                          #{idx + 1}
                        </td>

                        <td className="py-3 px-4">
                          <div className="font-bold text-slate-900">
                            {item.offering_title}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                            {item.estimated_scope}
                          </div>
                        </td>

                        <td className="py-3 px-4 text-center">
                          <span
                            className={`font-mono font-bold px-2 py-0.5 rounded border ${
                              isDisq
                                ? 'text-rose-700 bg-rose-50 border-rose-200'
                                : item.propensity_score >= 80
                                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                                : item.propensity_score >= 60
                                ? 'text-sky-700 bg-sky-50 border-sky-200'
                                : 'text-amber-700 bg-amber-50 border-amber-200'
                            }`}
                          >
                            {item.propensity_score.toFixed(1)}
                          </span>
                        </td>

                        <td className="py-3 px-4">
                          <span
                            className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                              isDisq
                                ? 'text-rose-700 bg-rose-50 border-rose-200'
                                : 'text-slate-700 bg-slate-100 border-slate-200'
                            }`}
                          >
                            {item.tier}
                          </span>
                        </td>

                        <td className="py-3 px-4">
                          <div className="font-medium text-slate-800 line-clamp-1">
                            {item.primary_commercial_wedge?.name || 'Standard Engagement'}
                          </div>
                          <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                            {item.primary_commercial_wedge?.value_driver}
                          </div>
                        </td>

                        <td className="py-3 px-4">
                          {isTop ? (
                            <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 text-[11px]">
                              TOP MATCH
                            </span>
                          ) : isDisq ? (
                            <span className="font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 text-[11px]">
                              DISQUALIFIED
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[11px]">
                              Alternative Offering
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => onSelectDossier(item.dossier)}
                            className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                          >
                            Dossier
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
