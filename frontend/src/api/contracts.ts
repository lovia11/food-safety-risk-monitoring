export type ReviewStatus =
  | "pending"
  | "recommend_follow_up"
  | "no_further_action";

export type Review = {
  status: ReviewStatus;
  note: string;
  reviewedAt: string | null;
};

export type SamplingStatus = {
  inCurrentList: boolean;
  sourceSnapshotId: string | null;
  historicalCount: number;
};

export type SnapshotSummary = {
  snapshotId: string;
  productId: string;
  taskId: string;
  taskDisplayName: string;
  targetId: string | null;
  targetName: string | null;
  rank: number | null;
  productName: string;
  shopName: string;
  region: string;
  productUrl: string;
  collectedAt: string | null;
  status: string;
  detectedEffects: string[];
  reviewRequired: boolean | null;
  analysisSummary: string;
  paths: {
    run: string;
    product: string;
    meta: string | null;
    analysis: string | null;
  };
  counts: {
    originalImages: number;
    ocrImages: number;
  };
  review: Review;
  snapshotCount: number;
  sampling: SamplingStatus;
};

export type ProductPage = {
  products: SnapshotSummary[];
  count: number;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type FilterOption = {
  value: string;
  label: string;
};

export type TaskFilterOption = FilterOption & {
  targetId: string | null;
};

export type ProductFilterOptions = {
  tasks: TaskFilterOption[];
  targets: FilterOption[];
  effects: FilterOption[];
  reviewStatuses: FilterOption[];
  samplingStatuses: FilterOption[];
};

export type ProductQuery = {
  query: string;
  targetId: string;
  taskId: string;
  reviewStatus: string;
  effect: string;
  samplingStatus: string;
  collectedFrom: string;
  collectedTo: string;
  page: number;
  pageSize: number;
};

export type Evidence = {
  evidenceId: string;
  effect: string;
  text: string;
  matchedKeywords: string[];
  sourceType: string;
  sourceLabel: string;
  contentOrigin: string;
  sourcePath: string;
  lineNumber: number | null;
};

export type ProductAssets = {
  overview: string | null;
  screenshots: string[];
  originalImages: Array<{
    index: number | null;
    path: string | null;
    sourceUrl: string | null;
    width: number | null;
    height: number | null;
    ocrCandidate: boolean;
    acquisitionMethod: string | null;
  }>;
  ocrItems: Array<{
    image: string | null;
    imagePath: string | null;
    status: string | null;
    lineCount: number | null;
    characterCount: number | null;
    averageConfidence: number | null;
    textPath: string | null;
    jsonPath: string | null;
    error: string | null;
  }>;
  metaPath: string | null;
  analysisPath: string | null;
};

export type ProductContext = {
  product_category: string | null;
  product_form: string | null;
  confirmed_ingredient_contexts: string[];
  context_evidence: Array<Record<string, unknown>>;
};

export type FollowUpMethod = {
  method_id: string;
  method_no: string;
  method_name: string;
  method_type: string;
  method_status: string;
  determination_role: string;
  applicability_status: string;
  applicability_reason: string;
  source_name: string;
  source_reference: string;
  source_date: string | null;
};

export type SubstanceFollowUp = {
  substance_id: string;
  canonical_name: string;
  english_name: string;
  cas_no: string;
  regulatory_context_note: string;
  follow_up_status: string;
  suggested_methods: FollowUpMethod[];
  methods_needing_context: FollowUpMethod[];
  other_known_methods: FollowUpMethod[];
  reason: string;
};

export type RiskFinding = {
  risk_category: string;
  risk_labels: string[];
  possible_risk_summary: string;
  evidence_qualification:
    | "seller_managed_primary"
    | "user_generated_auxiliary_only";
  substance_follow_ups: SubstanceFollowUp[];
};

export type InspectionView = {
  available: boolean;
  recommendationStatus: "available" | "unavailable" | "error";
  context: ProductContext;
  riskFindings: RiskFinding[];
  unmappedEvidence: Array<Record<string, unknown>>;
  compositionGaps: Array<Record<string, unknown>>;
  knowledgeGaps: Array<Record<string, unknown>>;
  disclaimer: string;
  recommendationPath: string | null;
  contextPath: string | null;
  error: { message?: string } | null;
};

export type SnapshotWorkspace = {
  snapshot: Omit<SnapshotSummary, "review" | "sampling">;
  evidence: Evidence[];
  review: Review;
  assets: ProductAssets;
  inspection: InspectionView;
  sampling: SamplingStatus;
};

export type InspectionContextOptions = {
  product_categories: string[];
  product_forms: string[];
  ingredient_contexts: string[];
};
