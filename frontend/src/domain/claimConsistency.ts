import type {
  ClaimConsistencyAssessment,
  ClaimConsistencyRelation,
  ClaimConsistencyStatus,
  ClaimConsistencyState,
  ClaimSignalDTO,
  ClaimMentionDTO,
  Evidence,
  OfficialFunctionResolution,
  PerClaimConsistencyAssessment,
} from "../api/contracts";
import type { StatusTone } from "./presentation";

export type ClaimConsistencyPresentation = {
  code: ClaimConsistencyStatus | ClaimConsistencyState;
  label: string;
  description: string;
  tone: StatusTone;
  showIdentityAction: boolean;
  showOfficialFunctions: boolean;
  showRelations: boolean;
};

export type ClaimConsistencyRelationPresentation = {
  label: string;
  description: string;
  tone: StatusTone;
};

export type OfficialFunctionViewModel = {
  rawText: string;
  currentName: string | null;
  resolutionStatus: "resolved" | "unresolved";
  resolutionLabel: string;
  showRawText: boolean;
};

export type ClaimConsistencyRelationViewModel = {
  assessment: PerClaimConsistencyAssessment;
  displayLabel: string;
  mentionCount: number;
  pageTraceAvailable: boolean;
  presentation: ClaimConsistencyRelationPresentation;
};

const completeStatePresentation: Record<
  ClaimConsistencyState,
  Omit<ClaimConsistencyPresentation, "code">
> = {
  identity_not_verified: {
    label: "保健食品身份尚未核验",
    description: "先核验保健食品身份，核验后才能与官方功能记录比较。",
    tone: "neutral",
    showIdentityAction: true,
    showOfficialFunctions: false,
    showRelations: false,
  },
  claim_not_generated: {
    label: "页面宣传线索尚未生成",
    description: "先完成页面宣传线索分析，再进行官方功能比较。",
    tone: "neutral",
    showIdentityAction: false,
    showOfficialFunctions: false,
    showRelations: false,
  },
  claim_analysis_error: {
    label: "页面宣传线索分析失败",
    description: "页面宣传线索分析失败，本次官方功能比较暂不可用。",
    tone: "neutral",
    showIdentityAction: false,
    showOfficialFunctions: false,
    showRelations: false,
  },
  framework_unresolved: {
    label: "官方功能框架暂无法确定",
    description: "官方功能信息暂不完整，需人工核对。",
    tone: "warning",
    showIdentityAction: false,
    showOfficialFunctions: true,
    showRelations: false,
  },
  official_function_unresolved: {
    label: "当前比较结果不完整",
    description: "部分官方功能名称暂无法确认，当前比较结果不完整。",
    tone: "warning",
    showIdentityAction: false,
    showOfficialFunctions: true,
    showRelations: true,
  },
  no_page_claims: {
    label: "未发现可比较的页面宣传表达",
    description: "本次未识别到可与官方功能记录比较的页面宣传。",
    tone: "neutral",
    showIdentityAction: false,
    showOfficialFunctions: true,
    showRelations: false,
  },
  assessed: {
    label: "逐项主题比较已生成",
    description: "已完成页面宣传主题与官方功能记录的逐项比较。",
    tone: "info",
    showIdentityAction: false,
    showOfficialFunctions: true,
    showRelations: true,
  },
};

export function claimConsistencyPresentation(
  status: ClaimConsistencyStatus,
  assessment: ClaimConsistencyAssessment | null,
): ClaimConsistencyPresentation {
  if (status === "not_generated") {
    return {
      code: "not_generated",
      label: "尚未生成保健功能一致性比较",
      description: "该页面尚未生成保健功能比较结果。",
      tone: "neutral",
      showIdentityAction: false,
      showOfficialFunctions: false,
      showRelations: false,
    };
  }
  if (status === "error" || !assessment) {
    return {
      code: "error",
      label: "保健功能一致性分析失败",
      description: "本次保健功能比较失败。",
      tone: "danger",
      showIdentityAction: false,
      showOfficialFunctions: false,
      showRelations: false,
    };
  }
  return {
    code: assessment.state,
    ...completeStatePresentation[assessment.state],
  };
}

export const claimConsistencyRelationPresentation: Record<
  ClaimConsistencyRelation,
  ClaimConsistencyRelationPresentation
> = {
  function_topic_recorded: {
    label: "找到官方功能对应主题",
    description: "该页面宣传主题在产品官方功能记录中有对应主题。",
    tone: "info",
  },
  function_topic_not_recorded: {
    label: "当前官方记录中未找到对应项",
    description: "当前核验的官方功能记录中未找到对应主题。",
    tone: "warning",
  },
  no_governed_function_mapping: {
    label: "暂无官方功能主题对应规则",
    description: "该宣传主题目前没有可用的对应规则，暂不比较。",
    tone: "neutral",
  },
  mapping_unresolved: {
    label: "暂无法确定对应关系",
    description: "现有信息不足，暂无法确定该宣传主题的对应关系。",
    tone: "warning",
  },
};

const frameworkLabels: Record<string, string> = {
  "hf-framework-non-nutrient-cn-2023": "非营养素补充剂（2023年版）",
  "hf-framework-nutrient-supplement-cn-2023": "营养素补充剂（2023年版）",
};

export function healthFunctionFrameworkLabel(frameworkId: string | null) {
  if (!frameworkId) return "暂无法确定";
  return frameworkLabels[frameworkId] || "已记录的官方功能框架";
}

function resolutionLabel(resolution: OfficialFunctionResolution) {
  if (resolution.resolutionStatus === "unresolved") {
    return "名称暂无法确认";
  }
  if (resolution.resolutionSource === "official_transition_alias") {
    return "官方新旧功能名称衔接";
  }
  if (resolution.resolutionSource === "explicit_governed_mapping") {
    return "官方名称对应";
  }
  return "当前官方功能名称";
}

export function officialFunctionViewModels(
  assessment: ClaimConsistencyAssessment,
): OfficialFunctionViewModel[] {
  const queues = new Map<string, OfficialFunctionResolution[]>();
  for (const resolution of [
    ...assessment.resolvedHealthFunctions,
    ...assessment.unresolvedOfficialFunctions,
  ]) {
    const queue = queues.get(resolution.rawOfficialFunction) || [];
    queue.push(resolution);
    queues.set(resolution.rawOfficialFunction, queue);
  }
  return assessment.rawOfficialFunctions.map((rawText) => {
    const resolution = queues.get(rawText)?.shift();
    if (!resolution) {
      return {
        rawText,
        currentName: null,
        resolutionStatus: "unresolved",
        resolutionLabel: "名称暂无法确认",
        showRawText: true,
      };
    }
    return {
      rawText,
      currentName: resolution.healthFunctionOfficialName,
      resolutionStatus: resolution.resolutionStatus,
      resolutionLabel: resolutionLabel(resolution),
      showRawText:
        resolution.resolutionStatus === "unresolved"
        || resolution.healthFunctionOfficialName !== rawText,
    };
  });
}

export function claimConsistencyRelationViewModels(
  assessment: ClaimConsistencyAssessment,
  signals: ClaimSignalDTO[],
  mentions: ClaimMentionDTO[] = [],
  evidence: Evidence[] = [],
): ClaimConsistencyRelationViewModel[] {
  const signalsById = new Map(
    signals.map((signal) => [signal.claimSignalId, signal]),
  );
  const mentionsById = new Map(
    mentions.map((mention) => [mention.claimMentionId, mention]),
  );
  const evidenceIds = new Set(evidence.map((item) => item.evidenceId));
  return assessment.perClaimAssessments.map((item) => {
    const signal = signalsById.get(item.claimSignalId);
    return {
      assessment: item,
      displayLabel: signal?.displayLabel || "页面宣传主题",
      mentionCount: item.claimMentionIds.length,
      pageTraceAvailable: Boolean(
        signal
        && item.claimMentionIds.some((mentionId) => {
          const mention = mentionsById.get(mentionId);
          return Boolean(mention && evidenceIds.has(mention.evidenceId));
        }),
      ),
      presentation: claimConsistencyRelationPresentation[item.relation],
    };
  });
}

export function claimConsistencyCountSummary(
  assessment: ClaimConsistencyAssessment,
) {
  const { summary } = assessment;
  const parts: string[] = [];
  if (summary.functionTopicRecordedCount > 0) {
    parts.push(`${summary.functionTopicRecordedCount} 类找到官方功能对应主题`);
  }
  if (summary.functionTopicNotRecordedCount > 0) {
    parts.push(`${summary.functionTopicNotRecordedCount} 类未在当前官方功能记录中找到对应项`);
  }
  if (summary.noMappingCount > 0) {
    parts.push(`${summary.noMappingCount} 类暂无对应规则`);
  }
  if (summary.mappingUnresolvedCount > 0) {
    parts.push(`${summary.mappingUnresolvedCount} 类暂无法确定对应关系`);
  }
  return `${summary.claimSignalCount} 类页面宣传主题${parts.length ? `：${parts.join("，")}` : ""}。`;
}

export function hasClaimAttentionGovernanceGap(
  assessment: ClaimConsistencyAssessment,
) {
  return assessment.gaps.includes(
    "claim_expression_attention_dataset_pending_manual_governance",
  );
}
