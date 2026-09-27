import React, { useState } from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Layers,
  Plus,
  Search,
  Sliders,
  Trash2,
  Wand2,
} from 'lucide-react';
import { CommercialOffering, CommercialWedge, SignalRule, SignalWeight } from '../types';
import { compileOfferingFromText, createCustomOffering } from '../services/api';

interface OfferConfiguratorProps {
  onOfferingCreated: (newOffering: CommercialOffering) => void;
  onCancel?: () => void;
}

export const OfferConfigurator: React.FC<OfferConfiguratorProps> = ({
  onOfferingCreated,
  onCancel,
}) => {
  const [nlpMandateInput, setNlpMandateInput] = useState('');
  const [isDecomposing, setIsDecomposing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Core Offering ICP State
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Enterprise IT Solutions');
  const [description, setDescription] = useState('');
  const [targetSectors, setTargetSectors] = useState<string[]>([
    'Enterprise Operations',
    'Logistics and Supply Chain',
    'Industrial Manufacturing',
  ]);
  const [sectorInput, setSectorInput] = useState('');
  const [minHeadcount, setMinHeadcount] = useState(250);
  const [requiresPhysical, setRequiresPhysical] = useState(false);

  // Configurable Signal Questions State
  const [signalRules, setSignalRules] = useState<SignalRule[]>([
    {
      question: 'Does the company mention process optimization, cost reduction, or automation initiatives in recent disclosures?',
      guidance_notes: 'Verified press statements, annual reports, or executive announcements.',
      weight: 'HIGH',
      is_negative: false,
    },
    {
      question: 'Is the organization actively hiring specialist engineering or operational leads?',
      guidance_notes: 'Public ATS career portal openings and recruitment velocity.',
      weight: 'MEDIUM',
      is_negative: false,
    },
    {
      question: 'Is the enterprise under active liquidation, insolvency, or bankruptcy restructuring?',
      guidance_notes: 'Official corporate registries indicating legal insolvency proceedings.',
      weight: 'DISQUALIFY',
      is_negative: true,
    },
  ]);

  // Disqualification Rules
  const [disqualifiers, setDisqualifiers] = useState<string[]>([
    'Enterprise under active bankruptcy, court liquidation, or insolvency',
    'Organization with zero relevant operational infrastructure',
  ]);
  const [disqInput, setDisqInput] = useState('');

  // Connector Queries
  const [newsKeywords, setNewsKeywords] = useState('automation, digital transformation, cloud, procurement');
  const [atsRoles, setAtsRoles] = useState('Process Lead, Automation Engineer, Cloud Architect');
  const [tenderKeywords, setTenderKeywords] = useState('tender, procurement, RFP, software');

  // Commercial Wedges
  const [wedges, setWedges] = useState<CommercialWedge[]>([
    {
      name: 'Turnkey Enterprise Modernization',
      target_archetype: 'Enterprise operations leaders executing modernization',
      value_driver: 'Accelerate operational throughput and reduce integration cycle time.',
    },
    {
      name: 'Managed Co-Delivery Squads',
      target_archetype: 'Internal digital and engineering teams with capacity backlogs',
      value_driver: 'Co-deliver production-ready architecture without vendor lock-in.',
    },
    {
      name: 'Strategic Pilot and Architecture Sprint',
      target_archetype: 'Corporate procurement and risk management leaders',
      value_driver: 'Validate unit economics and ROI within a focused 60-day trial.',
    },
  ]);

  // Handle NLP Decomposition
  const handleDecompose = async () => {
    if (!nlpMandateInput.trim()) return;
    setIsDecomposing(true);
    try {
      const res = await compileOfferingFromText(nlpMandateInput);
      if (res.offering_name) setTitle(res.offering_name);
      if (res.description) setDescription(res.description);
      if (res.signal_rules && res.signal_rules.length > 0) {
        setSignalRules(
          res.signal_rules.map((r: any) => ({
            question: r.question,
            guidance_notes: r.guidance_notes || '',
            weight: r.weight || 'MEDIUM',
            is_negative: Boolean(r.is_negative),
          }))
        );
      }
      if (res.disqualifiers && res.disqualifiers.length > 0) {
        setDisqualifiers(res.disqualifiers);
      }
      if (res.connector_queries) {
        if (res.connector_queries.news) setNewsKeywords(res.connector_queries.news.join(', '));
        if (res.connector_queries.ats) setAtsRoles(res.connector_queries.ats.join(', '));
        if (res.connector_queries.tenders) setTenderKeywords(res.connector_queries.tenders.join(', '));
      }
      if (res.target_sectors && res.target_sectors.length > 0) {
        setTargetSectors(res.target_sectors);
      }
    } catch (err) {
      console.error('Decomposition error:', err);
    } finally {
      setIsDecomposing(false);
    }
  };

  // Rule operations
  const handleAddRule = () => {
    setSignalRules([
      ...signalRules,
      {
        question: 'New custom business signal question',
        guidance_notes: 'Enter guidance notes for multi-source evidence extraction',
        weight: 'MEDIUM',
        is_negative: false,
      },
    ]);
  };

  const handleUpdateRule = (index: number, field: keyof SignalRule, value: any) => {
    const updated = [...signalRules];
    (updated[index] as any)[field] = value;
    setSignalRules(updated);
  };

  const handleDeleteRule = (index: number) => {
    setSignalRules(signalRules.filter((_, i) => i !== index));
  };

  // Sector chips
  const handleAddSector = () => {
    if (sectorInput.trim() && !targetSectors.includes(sectorInput.trim())) {
      setTargetSectors([...targetSectors, sectorInput.trim()]);
      setSectorInput('');
    }
  };

  const handleRemoveSector = (sec: string) => {
    setTargetSectors(targetSectors.filter((s) => s !== sec));
  };

  // Disqualifier chips
  const handleAddDisqualifier = () => {
    if (disqInput.trim()) {
      setDisqualifiers([...disqualifiers, disqInput.trim()]);
      setDisqInput('');
    }
  };

  const handleRemoveDisqualifier = (index: number) => {
    setDisqualifiers(disqualifiers.filter((_, i) => i !== index));
  };

  // Save new offering
  const handleSaveOffering = async () => {
    if (!title.trim()) {
      alert('Please enter an offering title.');
      return;
    }

    setIsSaving(true);
    try {
      const payload: Partial<CommercialOffering> = {
        title: title.trim(),
        category: category.trim(),
        description: description.trim() || `Enterprise commercial offering for ${title.trim()}.`,
        target_sectors: targetSectors,
        target_geographies: ['Europe', 'Global'],
        min_headcount: minHeadcount,
        requires_physical_presence: requiresPhysical,
        signal_rules: signalRules,
        disqualifiers: disqualifiers,
        target_wedges: wedges,
        connector_queries: {
          news: newsKeywords.split(',').map((k) => k.trim()).filter(Boolean),
          ats: atsRoles.split(',').map((k) => k.trim()).filter(Boolean),
          tenders: tenderKeywords.split(',').map((k) => k.trim()).filter(Boolean),
        },
      };

      const created = await createCustomOffering(payload);
      setSaveSuccess(true);
      setTimeout(() => {
        onOfferingCreated(created);
      }, 800);
    } catch (err) {
      console.error('Failed to create custom offering:', err);
      alert('Failed to save offering: ' + (err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Create and Configure Commercial Offering
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Zero preset constraint: define custom signal questions, assign weights, configure ICP criteria, and establish disqualification rules.
            </p>
          </div>
          {onCancel && (
            <button
              onClick={onCancel}
              className="text-xs font-semibold px-3 py-1.5 rounded border border-slate-200 hover:bg-slate-50 text-slate-700"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Module 1: Natural Language Mandate Auto-Compiler */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2 mb-2">
          <Wand2 className="w-4 h-4 text-orange-600" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Mandate Auto-Compiler (AI and NLP Synthesis)
          </h2>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Type any product, service, or commercial mandate in plain natural language. The system synthesizes structured signal questions, weights, connector queries, and disqualifiers.
        </p>

        <div className="flex gap-2.5">
          <input
            type="text"
            placeholder="e.g. Autonomous warehouse robotics for European logistics hubs, or Enterprise Zero-Trust Microsegmentation..."
            value={nlpMandateInput}
            onChange={(e) => setNlpMandateInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleDecompose()}
            className="flex-1 px-3.5 py-2 text-xs bg-slate-50 border border-slate-300 rounded focus:ring-1 focus:ring-orange-500 focus:outline-none"
          />
          <button
            onClick={handleDecompose}
            disabled={isDecomposing || !nlpMandateInput.trim()}
            className="px-4 py-2 text-xs font-semibold rounded bg-slate-900 hover:bg-slate-800 text-white transition-colors disabled:opacity-50"
          >
            {isDecomposing ? 'Synthesizing...' : 'Decompose Mandate'}
          </button>
        </div>
      </div>

      {/* Module 2: Ideal Customer Profile (ICP) Parameters */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Sliders className="w-4 h-4 text-orange-600" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Ideal Customer Profile (ICP) Definition
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Offering Title *
            </label>
            <input
              type="text"
              placeholder="e.g. Autonomous Warehouse Robotics"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded focus:outline-none focus:border-orange-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Service Category
            </label>
            <input
              type="text"
              placeholder="e.g. Industrial Automation, Cybersecurity, Cloud Infrastructure"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded focus:outline-none focus:border-orange-500"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block font-semibold text-slate-700 mb-1">
              Value Proposition Description
            </label>
            <textarea
              rows={2}
              placeholder="Describe what is being sold, the primary business challenge solved, and the measurable value proposition..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded focus:outline-none focus:border-orange-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Minimum Target Headcount
            </label>
            <input
              type="number"
              min={10}
              step={50}
              value={minHeadcount}
              onChange={(e) => setMinHeadcount(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded focus:outline-none focus:border-orange-500 font-mono"
            />
          </div>

          <div className="flex items-center pt-5">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={requiresPhysical}
                onChange={(e) => setRequiresPhysical(e.target.checked)}
                className="rounded text-orange-600 focus:ring-orange-500 w-4 h-4"
              />
              <span className="font-semibold text-slate-800">
                Requires Physical Footprint (Warehouses, Industrial Facilities, Campus Transit)
              </span>
            </label>
          </div>
        </div>

        {/* Sectors Tags */}
        <div className="pt-2 text-xs">
          <label className="block font-semibold text-slate-700 mb-1.5">
            Target Vertical Sectors
          </label>
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            {targetSectors.map((sec) => (
              <span
                key={sec}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 text-slate-800 border border-slate-200 text-xs"
              >
                <span>{sec}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveSector(sec)}
                  className="hover:text-rose-600"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2 max-w-sm">
            <input
              type="text"
              placeholder="Add vertical sector..."
              value={sectorInput}
              onChange={(e) => setSectorInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSector())}
              className="flex-1 px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded focus:outline-none"
            />
            <button
              type="button"
              onClick={handleAddSector}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-semibold"
            >
              Add
            </button>
          </div>
        </div>
      </div>

      {/* Module 3: Signal Questions and Weights Matrix */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-orange-600" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
              Configurable Signal Questions and Weights Matrix
            </h2>
          </div>
          <button
            type="button"
            onClick={handleAddRule}
            className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Question</span>
          </button>
        </div>

        <p className="text-xs text-slate-500">
          The AI engine searches public disclosures, procurement portals, news, and career pages against these explicit criteria.
        </p>

        <div className="space-y-3">
          {signalRules.map((rule, idx) => (
            <div
              key={idx}
              className="p-3.5 bg-slate-50 border border-slate-200 rounded-md text-xs space-y-2.5"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="font-mono font-bold text-slate-400 mt-1">
                  #{idx + 1}
                </span>
                <div className="flex-1">
                  <input
                    type="text"
                    value={rule.question}
                    onChange={(e) => handleUpdateRule(idx, 'question', e.target.value)}
                    placeholder="Enter signal question..."
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded focus:outline-none font-semibold text-slate-900"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteRule(idx)}
                  className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                  title="Remove rule"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pl-6">
                <div className="md:col-span-2">
                  <input
                    type="text"
                    value={rule.guidance_notes || ''}
                    onChange={(e) => handleUpdateRule(idx, 'guidance_notes', e.target.value)}
                    placeholder="Guidance notes for evidence citation extraction..."
                    className="w-full px-2.5 py-1 bg-white border border-slate-300 rounded focus:outline-none text-slate-600 text-[11px]"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <select
                    value={rule.weight}
                    onChange={(e) => handleUpdateRule(idx, 'weight', e.target.value as SignalWeight)}
                    className="px-2 py-1 bg-white border border-slate-300 rounded font-bold text-slate-800 text-xs"
                  >
                    <option value="HIGH">HIGH (35 Pts)</option>
                    <option value="MEDIUM">MEDIUM (20 Pts)</option>
                    <option value="LOW">LOW (10 Pts)</option>
                    <option value="DISQUALIFY">DISQUALIFY (Gate)</option>
                  </select>

                  <label className="flex items-center gap-1.5 cursor-pointer text-[11px] font-medium text-slate-600 select-none">
                    <input
                      type="checkbox"
                      checked={rule.is_negative}
                      onChange={(e) => handleUpdateRule(idx, 'is_negative', e.target.checked)}
                      className="rounded text-rose-600 focus:ring-rose-500"
                    />
                    <span>Negative Signal</span>
                  </label>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Module 4: Disqualification Rules */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
          <AlertTriangle className="w-4 h-4 text-rose-600" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Hard Disqualification and Negative Exclusion Rules
          </h2>
        </div>
        <p className="text-xs text-slate-500">
          Accounts that confirm any disqualification rule drop composite score to 0 and are locked from outreach generation.
        </p>

        <div className="space-y-2">
          {disqualifiers.map((dq, i) => (
            <div
              key={i}
              className="flex items-center justify-between p-2.5 bg-rose-50/60 border border-rose-200/80 rounded text-xs text-rose-900"
            >
              <span>{dq}</span>
              <button
                type="button"
                onClick={() => handleRemoveDisqualifier(i)}
                className="text-rose-400 hover:text-rose-700"
              >
                &times;
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-2 max-w-lg pt-1">
          <input
            type="text"
            placeholder="Add disqualification condition (e.g. active bankruptcy, competitor captive IT)..."
            value={disqInput}
            onChange={(e) => setDisqInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddDisqualifier())}
            className="flex-1 px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded focus:outline-none"
          />
          <button
            type="button"
            onClick={handleAddDisqualifier}
            className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
          >
            Add Rule
          </button>
        </div>
      </div>

      {/* Module 5: Multi-Source Connector Queries */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs space-y-4 text-xs">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
          <Search className="w-4 h-4 text-orange-600" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Live Connector Query Keywords
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Google News and Media Keywords
            </label>
            <input
              type="text"
              value={newsKeywords}
              onChange={(e) => setNewsKeywords(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded focus:outline-none font-mono text-[11px]"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Target ATS Hiring Roles
            </label>
            <input
              type="text"
              value={atsRoles}
              onChange={(e) => setAtsRoles(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded focus:outline-none font-mono text-[11px]"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Public Procurement and Tender Terms
            </label>
            <input
              type="text"
              value={tenderKeywords}
              onChange={(e) => setTenderKeywords(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded focus:outline-none font-mono text-[11px]"
            />
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-xs flex items-center justify-between">
        <div>
          {saveSuccess && (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Offering successfully compiled and activated in memory!</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-xs font-semibold rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-200"
            >
              Cancel
            </button>
          )}

          <button
            onClick={handleSaveOffering}
            disabled={isSaving || !title.trim()}
            className="flex items-center gap-2 px-5 py-2 text-xs font-bold rounded bg-orange-600 hover:bg-orange-700 text-white transition-colors shadow-xs disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            <span>{isSaving ? 'Compiling Offering...' : 'Confirm and Save Offering'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
