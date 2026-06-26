export interface SourcePointer {
  url: string;
  timestamp_or_section?: string | number | null;
  author?: string | null;
}

export interface QueryResult {
  unit_id: string;
  claim: string;
  type: string;
  applicability: string;
  confidence: number;
  source: SourcePointer;
  related: { unit_id: string; relationship: string }[];
  relevance_score: number;
}

export interface QuarantineUnit {
  id: string;
  claim: string;
  type: string;
  domains: string[];
  applicability: string;
  confidence: number;
  source_url?: string;
  source_span?: string;
  validation_failures?: string[];
  partition: string;
}

export interface IngestResponse {
  workflow_id: string;
  document_id: string | null;
  status: string;
}

export interface IngestStatus {
  workflow_id: string;
  status: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface Gap {
  concept: string;
  reference_count: number;
}

export interface Contradiction {
  a_id: string;
  a_claim: string;
  b_id: string;
  b_claim: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  neo4j?: string;
}
