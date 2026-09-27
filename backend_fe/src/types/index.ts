export type SignalWeight = 'HIGH' | 'MEDIUM' | 'LOW' | 'DISQUALIFY';

export interface SignalRule {
  question: string;
  guidance_notes?: string;
  weight: SignalWeight;
  is_negative: boolean;
}

export interface CommercialWedge {
  name: string;
  target_archetype: string;
  description?: string;
  value_driver: string;
}

export interface CommercialOffering {
  key: string;
  id: string;
  title: string;
  category: string;
  description: string;
  target_sectors: string[];
  target_geographies: string[];
  min_headcount: number;
  requires_physical_presence: boolean;
  target_wedges: CommercialWedge[];
  signal_rules: SignalRule[];
  connector_queries: {
    news?: string[];
    ats?: string[];
    tenders?: string[];
    developer?: string[];
    security?: string[];
  };
  disqualifiers: string[];
  is_custom: boolean;
}

export interface CompanyProfile {
  name: string;
  domain: string;
  legal_name?: string;
  country: string;
  headcount?: number;
  sector?: string;
  ticker?: string;
  description?: string;
  is_solvent: boolean;
}

export interface ScoreBreakdown {
  operational_fit: number;
  timing_urgency: number;
  purchasing_scale: number;
  hiring_intent: number;
  composite_score: number;
}

export interface ProspectEvidence {
  category: string;
  title: string;
  snippet: string;
  source: string;
  confidence: number;
  points_awarded?: number;
}

export interface DecisionMakerPersona {
  title: string;
  department: string;
  mandate: string;
  outreach_hook: string;
}

export interface PerfectCustomerDossier {
  company: CompanyProfile;
  offering_id: string;
  offering_title: string;
  propensity_score: number;
  tier: 'Tier 1 Prime Target' | 'Tier 2 Strategic Lead' | 'Tier 3 Review Needed' | 'Disqualified';
  is_disqualified: boolean;
  disqualification_reason?: string;
  score_breakdown: ScoreBreakdown;
  primary_commercial_wedge: CommercialWedge;
  operational_rationale: string;
  evidence_citations: ProspectEvidence[];
  target_buying_committee: DecisionMakerPersona[];
  estimated_commercial_scope: string;
  strategic_pitch_narrative: string;
}

export interface ProspectingUniverseResult {
  offering: {
    offering_id: string;
    title: string;
    category?: string;
    target_sectors?: string[];
    signal_keywords?: string[];
  };
  total_evaluated: number;
  tier1_count: number;
  tier2_count: number;
  ranked_customers: PerfectCustomerDossier[];
}

export interface BestOfferRankingItem {
  offering_key: string;
  offering_title: string;
  propensity_score: number;
  tier: string;
  is_disqualified: boolean;
  disqualification_reason?: string;
  primary_commercial_wedge?: CommercialWedge;
  operational_rationale: string;
  estimated_scope: string;
  score_breakdown: ScoreBreakdown;
  evidence_count: number;
  dossier: PerfectCustomerDossier;
}

export interface BestOfferMatchResult {
  company_name: string;
  evaluated_offerings_count: number;
  top_recommended_offering: string;
  top_score: number;
  top_tier: string;
  recommendation_summary: string;
  offerings_ranking: BestOfferRankingItem[];
}

export interface ConnectorReport {
  entity: Record<string, any>;
  connectors: {
    financials: {
      source: string;
      status: string;
      headcount?: number;
      operating_margin?: number;
      ticker?: string;
      sector?: string;
    };
    news: {
      source: string;
      status: string;
      items_count: number;
      top_articles: Array<{ title: string; link: string; date?: string; snippet?: string }>;
    };
    tenders: {
      source: string;
      status: string;
      active_tender_rfp: boolean;
      has_official_award: boolean;
      evidence: string[];
    };
    ats_hiring: {
      source: string;
      status: string;
      provider: string;
      matched_roles: string[];
      total_openings: number;
    };
    security: {
      source: string;
      status: string;
      grade: string;
      missing_headers: string[];
      exposed_subdomains: string[];
    };
    registry: {
      source: string;
      status: string;
      is_solvent: boolean;
      legal_status: string;
      registry: string;
    };
    developer: {
      source: string;
      status: string;
      repo_count: number;
      primary_language: string;
      hacker_news_stories: any[];
    };
    vulnerabilities: {
      source: string;
      status: string;
      cisa_kev_count: number;
      matches: string[];
    };
  };
}

export interface OutreachDraft {
  draft_id: string;
  recipient: string;
  subject: string;
  body: string;
  status: 'AWAITING_HUMAN_APPROVAL' | 'DISPATCHED';
  created_at: string;
  company_name?: string;
}

export interface MLModelMetadata {
  status: string;
  metadata?: {
    trained_at?: string;
    dataset_episodes_count?: number;
    training_data_source?: string;
    metrics?: Record<string, number>;
  };
  metrics?: Record<string, number>;
  feature_importances?: Record<string, number>;
  weights_dir?: string;
}

export interface DiagnosticsReport {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  timestamp: string;
  components: Record<string, {
    status: string;
    [key: string]: any;
  }>;
}
