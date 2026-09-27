import React, { useState } from 'react';
import {
  AlertTriangle,
  Building,
  CheckCircle2,
  Code,
  DollarSign,
  Globe,
  Lock,
  Network,
  Newspaper,
  RefreshCw,
  Search,
  ShieldAlert,
  Users,
} from 'lucide-react';
import { ConnectorReport } from '../types';
import { getLiveConnectorSignals } from '../services/api';

interface ConnectorHubProps {
  initialCompanyName?: string;
  initialDomain?: string;
}

export const ConnectorHub: React.FC<ConnectorHubProps> = ({
  initialCompanyName = 'DHL Group',
  initialDomain = 'dhl.com',
}) => {
  const [companyName, setCompanyName] = useState(initialCompanyName);
  const [domain, setDomain] = useState(initialDomain);
  const [report, setReport] = useState<ConnectorReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleFetchConnectors = async (cName: string = companyName, cDom: string = domain) => {
    if (!cName.trim()) return;
    setIsLoading(true);
    try {
      const data = await getLiveConnectorSignals(cName.trim(), cDom.trim() || undefined);
      setReport(data);
    } catch (err) {
      console.error('Connector harvest error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  React.useEffect(() => {
    if (initialCompanyName) {
      handleFetchConnectors(initialCompanyName, initialDomain);
    }
  }, [initialCompanyName, initialDomain]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <Network className="w-5 h-5 text-orange-600" />
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Live Multi-Source Connector Telemetry Hub
          </h1>
        </div>
        <p className="text-xs text-slate-500">
          Probes all 8 live corporate intelligence connectors without persistence bloat: financial statements, breaking press catalysts, European TED tenders, public ATS career boards, security posture, official registries, GitHub OSINT, and CISA KEV vulnerabilities.
        </p>
      </div>

      {/* Target Company Controls */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-xs flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
            Enterprise Name
          </label>
          <input
            type="text"
            placeholder="e.g. DHL Group, Siemens AG, BASF SE..."
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-orange-500 focus:outline-none font-semibold text-slate-900"
          />
        </div>

        <div className="w-64 min-w-[160px]">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
            Domain Hint (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. dhl.com, siemens.com..."
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-orange-500 focus:outline-none font-mono text-slate-700"
          />
        </div>

        <div className="self-end">
          <button
            onClick={() => handleFetchConnectors()}
            disabled={isLoading || !companyName.trim()}
            className="flex items-center gap-2 px-5 py-2 text-xs font-bold rounded bg-slate-900 hover:bg-slate-800 text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Harvesting Signals...' : 'Probe All 8 Connectors'}</span>
          </button>
        </div>
      </div>

      {/* Connector Report Grid */}
      {report && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Target Entity: <strong className="text-slate-800">{report.entity.name}</strong> ({report.entity.domain})
            </span>
            <span className="font-mono text-[11px]">Zero Raw Document Persistence Policy</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Connector 1: Yahoo Finance */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <DollarSign className="w-4 h-4 text-emerald-600" />
                  <span>1. Financial Disclosures</span>
                </div>
                <span className="text-[10px] font-mono uppercase bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                  {report.connectors.financials.source}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-slate-600 pt-1">
                <div>
                  <span className="text-slate-400 block">Headcount:</span>
                  <span className="font-mono font-bold text-slate-800">
                    {report.connectors.financials.headcount?.toLocaleString() || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Operating Margin:</span>
                  <span className="font-mono font-bold text-slate-800">
                    {report.connectors.financials.operating_margin
                      ? `${(report.connectors.financials.operating_margin * 100).toFixed(1)}%`
                      : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Market Ticker:</span>
                  <span className="font-mono font-bold text-slate-800">
                    {report.connectors.financials.ticker || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Verified Sector:</span>
                  <span className="font-semibold text-slate-800">
                    {report.connectors.financials.sector || 'Industrial'}
                  </span>
                </div>
              </div>
            </div>

            {/* Connector 2: Google News RSS */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <Newspaper className="w-4 h-4 text-sky-600" />
                  <span>2. Google News Pan-European RSS</span>
                </div>
                <span className="text-[10px] font-mono uppercase bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                  {report.connectors.news.items_count} Catalysts
                </span>
              </div>
              <div className="space-y-1.5 pt-1">
                {report.connectors.news.top_articles.length === 0 ? (
                  <p className="text-slate-400 italic">No recent news items matching trigger keywords.</p>
                ) : (
                  report.connectors.news.top_articles.slice(0, 2).map((item, i) => (
                    <div key={i} className="p-2 bg-slate-50 rounded border border-slate-100">
                      <div className="font-semibold text-slate-800 line-clamp-1">{item.title}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5 flex justify-between">
                        <span>{item.date || 'Recent'}</span>
                        <a
                          href={item.link}
                          target="_blank"
                          rel="noreferrer"
                          className="text-orange-600 hover:underline"
                        >
                          Source Link
                        </a>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Connector 3: European TED Tenders */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <Globe className="w-4 h-4 text-indigo-600" />
                  <span>3. European Public Procurement Tenders (TED)</span>
                </div>
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                    report.connectors.tenders.active_tender_rfp
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {report.connectors.tenders.status}
                </span>
              </div>
              <div className="space-y-1.5 pt-1">
                {report.connectors.tenders.evidence.length === 0 ? (
                  <p className="text-slate-400 italic">No active European procurement notices detected.</p>
                ) : (
                  report.connectors.tenders.evidence.map((ev, i) => (
                    <div key={i} className="p-2 bg-slate-50 rounded border border-slate-100 font-mono text-[11px] text-slate-700">
                      {ev}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Connector 4: Public ATS Hiring */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <Users className="w-4 h-4 text-amber-600" />
                  <span>4. Public ATS Career Portals (Greenhouse / Lever)</span>
                </div>
                <span className="text-[10px] font-mono uppercase bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                  {report.connectors.ats_hiring.total_openings} Total Openings
                </span>
              </div>
              <div className="space-y-1.5 pt-1">
                <div className="text-[11px] text-slate-500">
                  Provider: <strong className="text-slate-700">{report.connectors.ats_hiring.provider}</strong>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {report.connectors.ats_hiring.matched_roles.length === 0 ? (
                    <span className="text-slate-400 italic">No matching specialist roles found.</span>
                  ) : (
                    report.connectors.ats_hiring.matched_roles.map((role, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 text-[11px]">
                        {role}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Connector 5: Security Posture */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <Lock className="w-4 h-4 text-purple-600" />
                  <span>5. Mozilla Observatory and DNS Telemetry</span>
                </div>
                <span className="font-mono font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded">
                  {report.connectors.security.status}
                </span>
              </div>
              <div className="space-y-1 pt-1">
                <div className="text-slate-500">
                  Missing Security Headers:{' '}
                  <span className="font-mono text-slate-700">
                    {report.connectors.security.missing_headers.join(', ') || 'None'}
                  </span>
                </div>
                <div className="text-slate-500">
                  Exposed Subdomains:{' '}
                  <span className="font-mono text-slate-700">
                    {report.connectors.security.exposed_subdomains.join(', ') || 'None audited'}
                  </span>
                </div>
              </div>
            </div>

            {/* Connector 6: Official Registries */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <Building className="w-4 h-4 text-emerald-600" />
                  <span>6. Corporate Registries (EU Gazettes / North Data)</span>
                </div>
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                    report.connectors.registry.is_solvent
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}
                >
                  {report.connectors.registry.status}
                </span>
              </div>
              <div className="space-y-1 pt-1">
                <div className="text-slate-500">
                  Legal Status: <strong className="text-slate-800">{report.connectors.registry.legal_status}</strong>
                </div>
                <div className="text-slate-500">
                  Registry: <span className="font-mono text-slate-700">{report.connectors.registry.registry}</span>
                </div>
              </div>
            </div>

            {/* Connector 7: Developer OSINT */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <Code className="w-4 h-4 text-cyan-600" />
                  <span>7. GitHub Developer OSINT and Tech Stack</span>
                </div>
                <span className="text-[10px] font-mono uppercase bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                  {report.connectors.developer.status}
                </span>
              </div>
              <div className="space-y-1 pt-1">
                <div className="text-slate-500">
                  Primary Stack: <strong className="text-slate-800">{report.connectors.developer.primary_language}</strong>
                </div>
                <div className="text-slate-500">
                  Public Repositories:{' '}
                  <span className="font-mono font-bold text-slate-800">{report.connectors.developer.repo_count}</span>
                </div>
              </div>
            </div>

            {/* Connector 8: CISA KEV Vulnerabilities */}
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs text-xs space-y-2">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2 font-bold text-slate-900">
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  <span>8. CISA Known Exploited Vulnerabilities (KEV)</span>
                </div>
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                    report.connectors.vulnerabilities.cisa_kev_count > 0
                      ? 'bg-rose-50 text-rose-700 border border-rose-200'
                      : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  }`}
                >
                  {report.connectors.vulnerabilities.status}
                </span>
              </div>
              <div className="space-y-1 pt-1">
                <div className="text-slate-500">
                  Active Weaponized CVEs:{' '}
                  <span className="font-mono font-bold text-slate-800">
                    {report.connectors.vulnerabilities.cisa_kev_count}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
