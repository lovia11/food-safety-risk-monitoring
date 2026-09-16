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
  claimAnalysisStatus?: ClaimAnalysisStatus;
  claimSignals?: ClaimSignalDTO[];
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
  thumbnailUrl: string | null;
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
  claimAnalysisStatus: ClaimAnalysisStatus;
  claimSignalSummaries: ClaimSignalSummaryDTO[];
  claimConsistencyStatus: ClaimConsistencyStatus;
  claimConsistency?: ClaimConsistencyAssessment | null;
  reviewRequired: boolean | null;
  analysisSummary: string;
  healthFoodIdentityState: HealthFoodIdentityState;
  paths: {
    run: string;
    product: string;
    meta: string | null;
    analysis: string | null;
    claimAnalysis: string | null;
    claimConsistency: string | null;
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
  claimTypes: FilterOption[];
  reviewStatuses: FilterOption[];
  samplingStatuses: FilterOption[];
};

export type ProductQuery = {
  query: string;
  targetId: string;
  taskId: string;
  reviewStatus: string;
  effect: string;
  claimType: string;
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

export type ClaimAnalysisStatus = "not_generated" | "complete" | "error";

export type ClaimConsistencyStatus = "not_generated" | "complete" | "error";

export type ClaimConsistencyState =
  | "identity_not_verified"
  | "claim_not_generated"
  | "claim_analysis_error"
  | "framework_unresolved"
  | "official_function_unresolved"
  | "no_page_claims"
  | "assessed";

export type OfficialFunctionResolution = {
  rawOfficialFunction: string;
  resolutionStatus: "resolved" | "unresolved";
  resolutionSource:
    | "current_official_name"
    | "official_transition_alias"
    | "explicit_governed_mapping"
    | null;
  frameworkId: string | null;
  healthFunctionId: string | null;
  healthFunctionOfficialName: string | null;
};

export type ClaimConsistencyRelation =
  | "function_topic_recorded"
  | "function_topic_not_recorded"
  | "no_governed_function_mapping"
  | "mapping_unresolved";

export type PerClaimConsistencyAssessment = {
  claimSignalId: string;
  claimType: string;
  claimMentionIds: string[];
  evidenceIds: string[];
  relation: ClaimConsistencyRelation;
  mappingId: string | null;
  healthFunctionId: string | null;
  healthFunctionOfficialName: string | null;
  frameworkId: string | null;
  supportingResolvedOfficialFunctions: OfficialFunctionResolution[];
  gaps: string[];
};

export type ClaimConsistencyAssessment = {
  schemaVersion: number;
  assessmentVersion: string;
  snapshotId: string;
  state: ClaimConsistencyState;
  claimTaxonomyVersion: string;
  healthFunctionDatasetVersion: string;
  claimHealthFunctionMappingVersion: string;
  healthFoodRegistryIdentifier: string | null;
  healthFoodRegistryRecordReferenceOrHash: string | null;
  healthFoodRegistryRetrievedAt: string | null;
  healthFoodRegistrySourceName: string | null;
  healthFoodRegistrySourceReference: string | null;
  healthFoodRegistryRawArtifactPath: string | null;
  registryFrameworkId: string | null;
  registryFrameworkResolutionSource:
    | "explicit_registry_framework"
    | "resolved_official_functions"
    | null;
  rawOfficialFunctions: string[];
  resolvedHealthFunctions: OfficialFunctionResolution[];
  unresolvedOfficialFunctions: OfficialFunctionResolution[];
  claimSignalIds: string[];
  claimMentionIds: string[];
  perClaimAssessments: PerClaimConsistencyAssessment[];
  mentionAttentions: never[];
  summary: {
    claimSignalCount: number;
    functionTopicRecordedCount: number;
    functionTopicNotRecordedCount: number;
    noMappingCount: number;
    mappingUnresolvedCount: number;
    unresolvedOfficialFunctionCount: number;
    attentionMentionCount: number;
  };
  gaps: string[];
  generatedAt: string;
};

export type ClaimMentionDTO = {
  claimMentionId: string;
  snapshotId: string;
  claimType: string;
  expressionId: string;
  rawText: string;
  normalizedText: string;
  matchedExpression: string;
  evidenceId: string;
  sourceScope: "seller_managed";
  sourceAssetType: string;
  sourceLocator: {
    sourcePath: string;
    lineNumber: number | null;
  };
  extractionMethod: "exact_literal_occurrence";
  taxonomyVersion: string;
  createdAt: string;
};

export type ClaimSignalDTO = {
  claimSignalId: string;
  snapshotId: string;
  claimType: string;
  displayLabel: string;
  mentionIds: string[];
  evidenceIds: string[];
  taxonomyVersion: string;
  status: "normalized";
  createdAt: string;
};

export type ClaimSignalSummaryDTO = {
  claimSignalId: string;
  claimType: string;
  displayLabel: string;
  mentionCount: number;
  taxonomyVersion: string;
  status: "normalized";
};

export type ProductFact = {
  factId: string;
  snapshotId: string;
  factType: "declared_origin";
  normalizedValue: string;
  rawValue: string;
  sourceType: "dom_parameter" | "ocr_detail_image" | string;
  contentOrigin: "seller_managed" | string;
  sourcePath: string;
  sourceText: string;
  extractionMethod: string;
  verificationState: "extracted" | string;
  createdAt: string;
};

export type DeclaredOrigin = {
  state: "none" | "single" | "conflict";
  values: string[];
  sources: ProductFact[];
};

export type HealthFoodIdentityState =
  | "no_indicator"
  | "candidate_indicator_only"
  | "candidate_identifier"
  | "identifier_ambiguous"
  | "registry_lookup_unavailable"
  | "registry_record_not_found"
  | "registry_record_found_identity_unverified"
  | "verified_match"
  | "identity_mismatch"
  | "conflict";

export type HealthFoodIdentitySource = {
  sourceType: string;
  sourcePath: string;
  sourceText: string;
  contentOrigin: "seller_managed";
  extractionMethod: string;
};

export type HealthFoodClue = HealthFoodIdentitySource & {
  clueId: string;
  clueType: string;
  text: string;
};

export type HealthFoodIdentifierCandidate = HealthFoodIdentitySource & {
  candidateId: string;
  rawValue: string;
  normalizedValue: string;
  identifierType: string;
  formatState: "valid_current" | "legacy_identifier_candidate" | "ambiguous_ocr" | "invalid";
};

export type HealthFoodRegistryRecord = {
  identifier: string;
  identifierType: string;
  productName: string | null;
  registrantOrFiler: string | null;
  registrantAddress: string | null;
  issueOrFilingDate: string | null;
  validUntil: string | null;
  status: string | null;
  officialHealthFunctions: string[];
  functionalOrMarkerIngredients: string[];
  suitablePopulation: string | null;
  unsuitablePopulation: string | null;
  specification: string | null;
  sourceName: string;
  sourceReference: string;
  retrievedAt: string;
  rawArtifactHash: string;
  rawArtifactPath: string | null;
};

export type HealthFoodIdentity = {
  state: HealthFoodIdentityState;
  clues: HealthFoodClue[];
  identifiers: HealthFoodIdentifierCandidate[];
  registryRecord: HealthFoodRegistryRecord | null;
  productMatch: {
    state: "not_assessed" | "unverified" | "strong_match" | "mismatch" | "conflict";
    pageProductNames: Array<HealthFoodIdentitySource & { value: string }>;
    officialProductName: string | null;
    titleAuxiliary: string | null;
    matchingRule: string;
  };
  verification: {
    status: "not_attempted" | "found" | "not_found" | "unavailable" | "malformed";
    queriedIdentifier: string | null;
    queriedAt: string | null;
    error: string | null;
    rawArtifactPath?: string | null;
    rawArtifactSha256?: string | null;
  };
  officialSource: { name: string; reference: string };
  gaps: string[];
  diagnostics: Record<string, unknown>;
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
  claimAnalysisStatus: ClaimAnalysisStatus;
  claimMentions: ClaimMentionDTO[];
  claimSignals: ClaimSignalDTO[];
  claimConsistencyStatus: ClaimConsistencyStatus;
  claimConsistency: ClaimConsistencyAssessment | null;
  productFacts: ProductFact[];
  declaredOrigin: DeclaredOrigin;
  healthFoodIdentity: HealthFoodIdentity;
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
  dataset_id: string;
  dataset_status: string;
  standard_name: string;
  target_type: string;
  source_name: string;
  source_reference: string;
  source_date: string | null;
  enabled: boolean;
  queries: MonitorQuery[];
  availability: "operational" | "query_pending" | "paused";
  availability_reason: string | null;
  validated_query_count: number;
  candidate_query_count: number;
  validated_queries: MonitorQuery[];
};

export type MonitorCoverage = {
  reference_target_count: number;
  targets_with_query_count: number;
  operational_target_count: number;
  enabled_query_count: number;
  validated_query_count: number;
  disabled_query_count: number;
  candidate_query_count: number;
  paused_target_count: number;
};

export type MonitorTargetList = {
  targets: MonitorTarget[];
  count: number;
  scope: "operational" | "reference";
  coverage: MonitorCoverage;
};

export type KnowledgeSourceTrace = {
  datasetId: string;
  datasetVersion: string;
  datasetStatus: string;
  sourceName: string | null;
  sourceReference: string | null;
  sourceDate: string | null;
};

export type KnowledgePage<T> = {
  items: T[];
  count: number;
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
};

export type KnowledgeSummary = {
  counts: {
    referenceMonitorTargets: number;
    operationalMonitorTargets: number;
    queryPendingMonitorTargets: number;
    pausedMonitorTargets: number;
    healthFunctions: number;
    inspectionMethods: number;
    recommendationReadyMethods: number;
    referenceOnlyMethods: number;
    substances: number;
    riskMappings: number;
    groupMappings: number;
    regulatoryDocuments: number;
  };
  authorities: {
    monitorReferences: KnowledgeSourceTrace[];
    healthFunctions: Pick<
      KnowledgeSourceTrace,
      "datasetId" | "datasetVersion" | "datasetStatus"
    >;
    inspection: KnowledgeSourceTrace | null;
    riskMappings: KnowledgeSourceTrace | null;
  };
  metricBoundary: string;
};

export type KnowledgeMonitorTarget = {
  targetId: string;
  standardName: string;
  targetType: string;
  availability: "operational" | "query_pending" | "paused";
  availabilityReason: string | null;
  validatedSearchQueryCount: number;
  hasValidatedSearchQuery: boolean;
  searchQueries: MonitorQuery[];
  source: KnowledgeSourceTrace;
  knowledgeGaps: string[];
  interpretation: string;
};

export type HealthFunctionAlias = {
  aliasId: string;
  aliasText: string;
  aliasType: "official_transition_name";
  status: string;
  sourceName: string;
  sourceReference: string;
  sourceDate: string;
};

export type KnowledgeHealthFunction = {
  functionId: string;
  frameworkId: string;
  frameworkType: "non_nutrient" | "nutrient_supplement";
  frameworkName: string;
  frameworkCoverageStatus: string;
  officialName: string;
  ordinal: number;
  status: string;
  jurisdiction: string;
  frameworkVersion: string;
  effectiveDate: string | null;
  transitionAliases: HealthFunctionAlias[];
  source: KnowledgeSourceTrace;
  knowledgeGaps: string[];
  interpretation: string;
};

export type KnowledgeSubstanceGroupMembership = {
  membershipId: string;
  groupIdentity: string;
  groupLabel: string;
  membershipScope: string;
  completenessContext: "partial" | "complete";
  sourceBasis: string;
  sourceReference: string;
  status: string;
  datasetId: string;
  datasetVersion: string;
};

export type KnowledgeSubstance = {
  substanceId: string;
  canonicalName: string;
  englishName: string | null;
  casNo: string | null;
  groupMetadata: {
    state: "recorded" | "not_recorded";
    memberships: KnowledgeSubstanceGroupMembership[];
  };
  regulatoryContext: {
    availability: "recorded" | "not_recorded";
    count: number;
    contexts: Array<{
      contextId: string;
      status: string;
      productScope: string;
      jurisdiction: string;
      validFrom: string | null;
      validTo: string | null;
      sourceName: string;
      sourceReference: string;
      sourceDate: string | null;
      note: string;
    }>;
  };
  methodCoverageCount: number;
  recommendationReadyMethodCount: number;
  note: string;
  source: KnowledgeSourceTrace;
  knowledgeGaps: string[];
  interpretation: string;
};

export type KnowledgeRiskMapping = {
  mappingId: string;
  riskCategory: string;
  riskLabel: string;
  targetType: "substance" | "substance_group";
  target: {
    substanceId: string | null;
    label: string;
    casNo: string | null;
    groupLabel: string | null;
  };
  evidenceGrade: "A" | "B" | "C";
  basisType: string;
  productScope: string;
  temporalStatus: "current" | "historical";
  sourceBasisText: string;
  note: string;
  groupResolution: {
    status: "unresolved" | "partial" | "complete";
    memberCount: number;
  } | null;
  source: KnowledgeSourceTrace;
  knowledgeGaps: string[];
  interpretation: string;
};

export type MethodKnowledgeDepth =
  | "reference_only"
  | "analyte_verified"
  | "applicability_verified"
  | "recommendation_ready";

export type KnowledgeRegulatoryDocumentSummary = {
  documentId: string;
  documentType: string;
  documentNo: string | null;
  title: string;
  publisher: string;
  publishedDate: string | null;
  effectiveDate: string | null;
  status: string;
  sourceReference: string;
  jurisdiction: string;
  supersedes: string[];
  supersededBy: string[];
};

export type KnowledgeInspectionMethod = {
  methodId: string;
  methodNo: string;
  methodName: string;
  methodType: string;
  methodStatus: "current" | "superseded" | "revoked" | "verification_pending";
  knowledgeDepth: MethodKnowledgeDepth;
  publisher: string;
  publishedDate: string | null;
  effectiveDate: string | null;
  replacesMethodNo: string | null;
  replacedByMethodNo: string | null;
  analyteCount: number;
  applicability: {
    availability: "recorded" | "not_recorded";
    count: number;
    includeCount: number;
    conditionalCount: number;
    excludeCount: number;
  };
  regulatoryDocument: KnowledgeRegulatoryDocumentSummary | null;
  note: string;
  source: KnowledgeSourceTrace;
  knowledgeGaps: string[];
  interpretation: string;
};

export type KnowledgeRegulatoryDocument = KnowledgeRegulatoryDocumentSummary & {
  linkedMethodCount: number;
  source: KnowledgeSourceTrace;
  knowledgeGaps: string[];
};
