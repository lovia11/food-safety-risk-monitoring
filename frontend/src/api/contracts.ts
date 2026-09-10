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
  decisionStatus:
    | "current"
    | "reviewed_follow_up"
    | "no_further_action"
    | "pending"
    | "not_eligible";
};

export type PipelineReadiness = {
  detailCollected: boolean;
  ocrInputReady: boolean;
  ocrReady: boolean;
  analysisReady: boolean;
  reviewEligible: boolean;
  reason:
    | "eligible"
    | "detail_not_collected"
    | "ocr_input_missing"
    | "ocr_not_ready"
    | "analysis_not_ready";
};

export type SamplingMembership = {
  productId: string;
  sourceSnapshotId: string;
  sourceTaskId: string;
  addedFrom: "product_overview" | "inspection_workspace";
  addedAt: string;
  updatedAt: string;
  productName?: string;
  shopName?: string;
  collectedAt?: string | null;
  review?: Review;
};

export type SamplingMethodSummary = {
  methodId: string;
  methodNo: string;
  methodName: string;
  methodStatus: string;
  applicabilityStatus: string;
  applicabilityReason: string;
  sourceName: string;
  sourceReference: string;
};

export type SamplingItem = SamplingMembership & {
  ordinal: number;
  sourceTaskDisplayName: string;
  productName: string;
  productUrl: string;
  shopName: string;
  collectedAt: string | null;
  detectedEffects: string[];
  historicalCountBeforeExport: number;
  summary: {
    pageEffectClues: string[];
    riskDirections: string[];
    pageEvidenceQualification: string;
    riskEvidenceQualifications: string[];
    substances: string[];
    suggestedMethods: SamplingMethodSummary[];
    methodsNeedingContext: SamplingMethodSummary[];
    otherKnownMethods: SamplingMethodSummary[];
    legacyUnclassifiedMethods?: SamplingMethodSummary[];
    methods?: SamplingMethodSummary[];
    evidenceQualifications?: string[];
  };
  evidence: Evidence[];
  inspection: InspectionView;
  productContext: ProductContext;
  review: Review;
  recommendationGaps: {
    unmappedEvidence: Array<Record<string, unknown>>;
    compositionGaps: Array<Record<string, unknown>>;
    knowledgeGaps: Array<Record<string, unknown>>;
  };
  disclaimer: string;
  frozenAssets: FrozenSamplingAsset[];
};

export type SamplingList = {
  items: SamplingItem[];
  count: number;
};

export type FrozenSamplingAsset = {
  kind: string;
  sourcePath: string;
  frozenPath: string;
  sha256: string;
  url?: string | null;
};

export type HistoricalSamplingListMetadata = {
  listId: string;
  status: "exported";
  exportedAt: string;
  itemCount: number;
  snapshotPath: string;
  workbookPath: string;
  snapshotSha256: string;
  workbookSha256: string;
  createdAt: string;
  updatedAt: string;
  detailUrl: string;
  downloadUrl: string;
};

export type HistoricalSamplingListPage = {
  lists: HistoricalSamplingListMetadata[];
  count: number;
};

export type HistoricalSamplingList = {
  schemaVersion: number;
  listId: string;
  status: "exported";
  createdAt: string;
  exportedAt: string;
  itemCount: number;
  workbookFile: string;
  workbookSha256: string;
  disclaimer: string;
  items: SamplingItem[];
  downloadUrl: string;
};

export type ReviewDecisionResult = {
  snapshotId: string;
  productId: string;
  review: Review;
  membership: SamplingMembership | null;
  sampling: SamplingStatus;
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
    evidence: number;
    sellerManagedEvidence: number;
    ugcEvidence: number;
  };
  readiness: PipelineReadiness;
  representativeEvidence: {
    text: string;
    contentOrigin: string;
    sourceLabel: string;
  } | null;
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

export type TaskBusinessStatus =
  | "running"
  | "waiting_for_manual_action"
  | "awaiting_review"
  | "completed"
  | "partial_error"
  | "interrupted";

export type TaskArchiveSummary = {
  searchCandidates: number;
  detailCompleted: number;
  detailTarget: number;
  detailFailed: number;
  analysisCompleted: number;
  analysisTarget: number;
  analysisFailed: number;
  clueProducts: number;
  pendingReview: number;
  completedReview: number;
  recommendFollowUpCount: number;
  noFurtherActionCount: number;
  currentSamplingItems: number;
  errorCount: number;
};

export type TaskFlowStep = {
  key: "search" | "detail" | "analysis" | "review";
  label: string;
  state: "future" | "active" | "done" | "partial" | "failed";
  completed: number;
  target: number;
};

export type ManualActionState = {
  status: "waiting" | "resolved" | "idle";
  generation: number;
  reason: string | null;
  requestedAt: string | null;
  lastCheckedAt: string | null;
  attempt: number;
  canAcknowledge: boolean;
} | null;

export type TaskSummary = {
  id: string;
  taskId: string;
  displayName: string;
  taskType: "quick" | "monitor";
  targetId: string | null;
  targetName: string | null;
  keyword: string;
  createdAt: string | null;
  updatedAt: string | null;
  businessStatus: TaskBusinessStatus;
  businessStatusLabel: string;
  actionLabel: string;
  stage: string;
  message: string;
  active: boolean;
  resumable: boolean;
  manualAction: ManualActionState;
  flow: TaskFlowStep[];
  archiveSummary: TaskArchiveSummary;
  url: string;
};

export type TaskList = {
  tasks: TaskSummary[];
  activeTaskId: string | null;
};

export type TaskDetail = TaskSummary & {
  task: {
    id: string;
    keyword: string;
    stage: string;
    stageLabel: string;
    terminal: boolean;
    message: string;
  };
  statistics: Record<string, number>;
  runtime: {
    active: boolean;
    resumable: boolean;
    createdAt: string | null;
    request: {
      displayName: string | null;
      taskType: "quick" | "monitor";
      keyword: string;
      candidateLimit: number | null;
      detailLimit: number | null;
      targetId: string | null;
      targetName: string | null;
      perQueryCandidateLimit: number | null;
      searchQueries: MonitorQuery[];
    };
  };
};

export type MonitorQuery = {
  query_id: string;
  query_text: string;
  query_type: string;
  query_source: string;
  validation_status: string;
  query_note: string;
  order: number;
  enabled: boolean;
};

export type MonitorTarget = {
  target_id: string;
  standard_name: string;
  target_type: string;
  enabled: boolean;
  queries: MonitorQuery[];
};
