import React, { useState } from 'react';
import {
  AlertTriangle,
  Building,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileText,
  Mail,
  Send,
  Shield,
  UserCheck,
  X,
} from 'lucide-react';
import { PerfectCustomerDossier } from '../types';

interface DossierDrawerProps {
  dossier: PerfectCustomerDossier | null;
  onClose: () => void;
  onStageOutreach: (dossier: PerfectCustomerDossier) => void;
  onInspectConnectors: (companyName: string, domain?: string) => void;
}

export const DossierDrawer: React.FC<DossierDrawerProps> = ({
  dossier,
  onClose,
  onStageOutreach,
  onInspectConnectors,
}) => {
  const [copied, setCopied] = useState(false);

  if (!dossier) return null;

  const { company, score_breakdown, primary_commercial_wedge, evidence_citations, target_buying_committee } = dossier;
  const isDisq = dossier.is_disqualified;

  const handleCopyPitch = () => {
    navigator.clipboard.writeText(dossier.strategic_pitch_narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                {company.name}
              </h2>
              {company.is_solvent ? (
                <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Solvent
                </span>
              ) : (
                <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                  Disqualified / Insolvent
                </span>
              )}
            </div>

            <div className="text-xs font-mono text-slate-500 mt-1 flex flex-wrap items-center gap-3">
              <span>{company.domain}</span>
              {company.country && <span>Country: {company.country}</span>}
              {company.headcount && <span>Headcount: {company.headcount.toLocaleString()}</span>}
              {company.sector && <span>Sector: {company.sector}</span>}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-slate-700">
          {/* Disqualification Banner if applicable */}
          {isDisq && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-md text-rose-800">
              <div className="flex items-center gap-2 font-bold text-rose-900">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <span>Account Disqualified from Commercial Outreach</span>
              </div>
              <p className="mt-1 text-xs text-rose-700">
                {dossier.disqualification_reason || 'Verified negative disqualification trigger.'}
              </p>
            </div>
          )}

          {/* Propensity Score & Tier Banner */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Propensity Score for {dossier.offering_title}
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-3xl font-extrabold font-mono text-slate-900">
                  {dossier.propensity_score.toFixed(1)}
                </span>
                <span className="text-slate-400 font-mono text-sm">/ 100</span>
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 ml-2">
                  {dossier.tier}
                </span>
              </div>
            </div>

            <button
              onClick={() => onInspectConnectors(company.name, company.domain)}
              className="flex items-center gap-1 px-3 py-1.5 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 font-medium transition-colors"
            >
              <span>Live Connectors</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </button>
          </div>

          {/* Multi-Dimensional Intent & Readiness Score Matrix */}
          <div>
            <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider mb-2.5">
              Intent and Readiness Score Matrix
            </h3>
            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-3 bg-white border border-slate-200 rounded">
                <div className="text-slate-500 font-medium flex justify-between">
                  <span>Operational Fit</span>
                  <span className="font-mono font-bold text-slate-800">
                    {score_breakdown.operational_fit.toFixed(1)} / 35.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-orange-500 h-full"
                    style={{ width: `${(score_breakdown.operational_fit / 35) * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded">
                <div className="text-slate-500 font-medium flex justify-between">
                  <span>Timing and Urgency</span>
                  <span className="font-mono font-bold text-slate-800">
                    {score_breakdown.timing_urgency.toFixed(1)} / 30.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-orange-500 h-full"
                    style={{ width: `${(score_breakdown.timing_urgency / 30) * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded">
                <div className="text-slate-500 font-medium flex justify-between">
                  <span>Purchasing Scale</span>
                  <span className="font-mono font-bold text-slate-800">
                    {score_breakdown.purchasing_scale.toFixed(1)} / 20.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-orange-500 h-full"
                    style={{ width: `${(score_breakdown.purchasing_scale / 20) * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-3 bg-white border border-slate-200 rounded">
                <div className="text-slate-500 font-medium flex justify-between">
                  <span>Hiring Intent</span>
                  <span className="font-mono font-bold text-slate-800">
                    {score_breakdown.hiring_intent.toFixed(1)} / 15.0
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-orange-500 h-full"
                    style={{ width: `${(score_breakdown.hiring_intent / 15) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Primary Commercial Wedge & Rationale */}
          <div className="p-4 bg-orange-50/60 border border-orange-200/80 rounded-lg">
            <div className="text-[11px] font-bold text-orange-800 uppercase tracking-wider">
              Selected Commercial Wedge
            </div>
            <div className="text-sm font-bold text-slate-900 mt-1">
              {primary_commercial_wedge?.name || 'Turnkey Enterprise Modernization'}
            </div>
            <p className="text-xs text-slate-700 mt-1">
              {primary_commercial_wedge?.value_driver}
            </p>
            <div className="mt-3 pt-3 border-t border-orange-200/60 flex items-center justify-between text-xs">
              <span className="font-medium text-slate-600">Estimated Scope:</span>
              <span className="font-semibold text-slate-900">
                {dossier.estimated_commercial_scope}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-600 italic">
              {dossier.operational_rationale}
            </p>
          </div>

          {/* Harvested Evidence Citations */}
          <div>
            <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider mb-2.5">
              Verified Public Signals and Evidence Citations ({evidence_citations.length})
            </h3>
            <div className="space-y-2">
              {evidence_citations.length === 0 ? (
                <p className="text-slate-400 italic">No specific signal quotes extracted.</p>
              ) : (
                evidence_citations.map((ev, i) => (
                  <div key={i} className="p-3 bg-white border border-slate-200 rounded">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-slate-800 text-xs">
                        {ev.title}
                      </span>
                      <span className="font-mono text-[11px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-bold">
                        {(ev.confidence * 100).toFixed(0)}% Confidence
                      </span>
                    </div>
                    <blockquote className="text-xs text-slate-600 bg-slate-50 p-2 rounded border-l-2 border-orange-500 italic my-1.5">
                      "{ev.snippet}"
                    </blockquote>
                    <div className="text-[10px] text-slate-400 flex items-center justify-between">
                      <span>Source: {ev.source}</span>
                      <span className="uppercase tracking-wider font-semibold text-slate-500">
                        {ev.category}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Target Buying Committee */}
          {target_buying_committee && target_buying_committee.length > 0 && (
            <div>
              <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider mb-2.5">
                Target Buying Committee and Executive Hooks
              </h3>
              <div className="space-y-2.5">
                {target_buying_committee.map((persona, i) => (
                  <div key={i} className="p-3 bg-white border border-slate-200 rounded">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">{persona.title}</span>
                      <span className="text-[10px] text-slate-500 uppercase">
                        {persona.department}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 mt-1">
                      <strong className="text-slate-700">Mandate:</strong> {persona.mandate}
                    </div>
                    <div className="text-xs text-orange-900 bg-orange-50/70 p-2 rounded mt-1.5 border border-orange-100">
                      <strong className="text-orange-950">Tailored Hook:</strong> {persona.outreach_hook}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategic Pitch Narrative */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wider">
                Evidence-Grounded Strategic Pitch
              </h3>
              <button
                onClick={handleCopyPitch}
                className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 font-medium"
              >
                <Copy className="w-3 h-3" />
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre className="p-3.5 bg-slate-900 text-slate-100 rounded-md font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
              {dossier.strategic_pitch_narrative}
            </pre>
          </div>
        </div>

        {/* Drawer Footer Actions */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 transition-colors"
          >
            Close
          </button>

          {!isDisq && (
            <button
              onClick={() => {
                onStageOutreach(dossier);
                onClose();
              }}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded bg-orange-600 hover:bg-orange-700 text-white transition-colors shadow-xs"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Stage to Outreach Queue</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
