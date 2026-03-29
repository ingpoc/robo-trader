import express, { type Request, type Response } from "express";
import { z } from "zod";
import { Codex, type ModelReasoningEffort } from "@openai/codex-sdk";

type JsonSchema = Record<string, unknown>;

const app = express();
app.use(express.json({ limit: "2mb" }));

const host = process.env.CODEX_RUNTIME_HOST ?? "127.0.0.1";
const port = Number(process.env.CODEX_RUNTIME_PORT ?? "8765");
const defaultModel = process.env.CODEX_MODEL ?? "gpt-5.4";
const defaultWorkdir = process.env.CODEX_WORKDIR ?? process.cwd();
const lightReasoning = (process.env.CODEX_REASONING_LIGHT ?? "low") as ModelReasoningEffort;
const deepReasoning = (process.env.CODEX_REASONING_DEEP ?? "medium") as ModelReasoningEffort;

const codex = new Codex();

type RuntimeHealthSnapshot = {
  status: "ready" | "degraded" | "blocked";
  provider: "codex";
  authenticated: boolean;
  usage_limited: boolean;
  message: string;
  checked_at: string;
  model: string;
  reasoning_profile: string;
  mode: "local_runtime_service";
};

let runtimeHealth: RuntimeHealthSnapshot = {
  status: "degraded",
  provider: "codex",
  authenticated: false,
  usage_limited: false,
  message: "Codex runtime sidecar is reachable, but no explicit AI request has validated auth/quota in this session yet.",
  checked_at: new Date().toISOString(),
  model: defaultModel,
  reasoning_profile: lightReasoning,
  mode: "local_runtime_service",
};

const structuredRunRequestSchema = z.object({
  system_prompt: z.string().min(1),
  prompt: z.string().min(1),
  output_schema: z.record(z.unknown()),
  model: z.string().optional(),
  reasoning: z.enum(["minimal", "low", "medium", "high", "xhigh"]).optional(),
  working_directory: z.string().optional(),
  web_search_enabled: z.boolean().optional(),
  web_search_mode: z.enum(["disabled", "cached", "live"]).optional(),
  network_access_enabled: z.boolean().optional(),
  timeout_seconds: z.number().positive().max(300).optional(),
  session_id: z.string().optional(),
});

const batchResearchRequestSchema = z.object({
  symbols: z.array(z.string().min(1)).min(1),
  company_names: z.record(z.string()).optional(),
  research_brief: z.string().optional(),
  model: z.string().optional(),
  reasoning: z.enum(["minimal", "low", "medium", "high", "xhigh"]).optional(),
  timeout_seconds: z.number().positive().max(300).optional(),
});

const discoveryScoutRequestSchema = z.object({
  account_id: z.string().optional(),
  criteria: z.record(z.unknown()).default({}),
  memory_context: z.record(z.unknown()).default({}),
  limit: z.number().int().min(1).max(10).default(5),
  model: z.string().optional(),
  reasoning: z.enum(["minimal", "low", "medium", "high", "xhigh"]).optional(),
  timeout_seconds: z.number().positive().max(300).optional(),
});

const promptOptimizationRequestSchema = z.object({
  data_type: z.string().min(1),
  current_prompt: z.string().min(1),
  retrieved_data: z.string().default(""),
  missing_elements: z.array(z.record(z.unknown())).default([]),
  redundant_elements: z.array(z.string()).default([]),
  quality_feedback: z.string().default(""),
  attempt_number: z.number().int().positive().default(1),
  model: z.string().optional(),
  reasoning: z.enum(["minimal", "low", "medium", "high", "xhigh"]).optional(),
  timeout_seconds: z.number().positive().max(300).optional(),
});

const providerMetadataSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    provider: { type: "string" },
    model: { type: "string" },
    reasoning: { type: "string" },
    run_id: { type: "string" },
    checked_at: { type: "string" },
    mode: { type: "string" },
  },
  required: ["provider", "model", "reasoning", "run_id", "checked_at", "mode"],
} satisfies JsonSchema;

const researchCitationSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    source_type: { type: "string" },
    label: { type: "string" },
    reference: { type: "string" },
    tier: { type: "string", enum: ["primary", "secondary", "derived"] },
    freshness: { type: "string" },
    timestamp: { type: "string" },
  },
  required: ["source_type", "label", "reference", "tier", "freshness", "timestamp"],
} satisfies JsonSchema;

const researchSourceSummarySchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    source_type: { type: "string" },
    label: { type: "string" },
    tier: { type: "string", enum: ["primary", "secondary", "derived"] },
    timestamp: { type: "string" },
    freshness: { type: "string" },
    detail: { type: "string" },
  },
  required: ["source_type", "label", "tier", "timestamp", "freshness", "detail"],
} satisfies JsonSchema;

const batchResearchEntrySchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    symbol: { type: "string" },
    research_timestamp: { type: "string" },
    summary: { type: "string" },
    research_summary: { type: "string" },
    news: { type: "string" },
    financial_data: { type: "string" },
    filings: { type: "string" },
    market_context: { type: "string" },
    sources: { type: "array", items: { type: "string" } },
    source_summary: { type: "array", items: researchSourceSummarySchema },
    evidence_citations: { type: "array", items: researchCitationSchema },
    evidence: { type: "array", items: { type: "string" } },
    risks: { type: "array", items: { type: "string" } },
    errors: { type: "array", items: { type: "string" } },
    external_evidence_status: { type: "string", enum: ["fresh", "partial", "missing"] },
  },
  required: [
    "symbol",
    "research_timestamp",
    "summary",
    "research_summary",
    "news",
    "financial_data",
    "filings",
    "market_context",
    "sources",
    "source_summary",
    "evidence_citations",
    "evidence",
    "risks",
    "errors",
    "external_evidence_status",
  ],
} satisfies JsonSchema;

const batchResearchResultSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    results: {
      type: "array",
      items: batchResearchEntrySchema,
    },
  },
  required: ["results"],
} satisfies JsonSchema;

const discoveryScoutCandidateSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    symbol: { type: "string" },
    company_name: { type: "string" },
    sector: { type: "string" },
    discovery_reason: { type: "string" },
    opportunity_score: { type: "number" },
    research_timestamp: { type: "string" },
    summary: { type: "string" },
    research_summary: { type: "string" },
    news: { type: "string" },
    financial_data: { type: "string" },
    filings: { type: "string" },
    market_context: { type: "string" },
    source_summary: { type: "array", items: researchSourceSummarySchema },
    evidence_citations: { type: "array", items: researchCitationSchema },
    evidence: { type: "array", items: { type: "string" } },
    risks: { type: "array", items: { type: "string" } },
    errors: { type: "array", items: { type: "string" } },
  },
  required: [
    "symbol",
    "company_name",
    "sector",
    "discovery_reason",
    "opportunity_score",
    "research_timestamp",
    "summary",
    "research_summary",
    "news",
    "financial_data",
    "filings",
    "market_context",
    "source_summary",
    "evidence_citations",
    "evidence",
    "risks",
    "errors",
  ],
} satisfies JsonSchema;

const discoveryScoutResultSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    market_state_summary: { type: "string" },
    favored_sectors: { type: "array", items: { type: "string" } },
    caution_sectors: { type: "array", items: { type: "string" } },
    key_insights: { type: "array", items: { type: "string" } },
    candidates: { type: "array", items: discoveryScoutCandidateSchema },
  },
  required: ["market_state_summary", "favored_sectors", "caution_sectors", "key_insights", "candidates"],
} satisfies JsonSchema;

const promptOptimizationResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    quality_score: { type: "number" },
    missing_elements: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          element: { type: "string" },
          description: { type: "string" },
          importance: { type: "string" },
        },
        required: ["element", "description", "importance"],
      },
    },
    redundant_elements: { type: "array", items: { type: "string" } },
    feedback: { type: "string" },
    strengths: { type: "array", items: { type: "string" } },
    improvements_needed: { type: "array", items: { type: "string" } },
    improved_prompt: { type: "string" },
    improvements_made: { type: "array", items: { type: "string" } },
    removed_redundancy: { type: "array", items: { type: "string" } },
    focus_areas: { type: "array", items: { type: "string" } },
    expected_improvement: { type: "string" },
  },
  required: [
    "quality_score",
    "missing_elements",
    "redundant_elements",
    "feedback",
    "strengths",
    "improvements_needed",
    "improved_prompt",
    "improvements_made",
    "removed_redundancy",
    "focus_areas",
    "expected_improvement",
  ],
} satisfies JsonSchema;

const runtimeValidationResultSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    validation_status: { type: "string" },
    checked_at: { type: "string" },
  },
  required: ["validation_status", "checked_at"],
} satisfies JsonSchema;

function isoNow(): string {
  return new Date().toISOString();
}

function providerMetadata(runId: string, model: string, reasoning: string) {
  return {
    provider: "codex",
    model,
    reasoning,
    run_id: runId,
    checked_at: isoNow(),
    mode: "local_runtime_service",
  };
}

function sourceTierFromType(sourceType: string): "primary" | "secondary" | "derived" {
  const normalized = (sourceType || "").trim().toLowerCase();
  if (["exchange_disclosure", "company_filing", "company_ir"].includes(normalized)) {
    return "primary";
  }
  if (["reputable_financial_news", "claude_web_news", "codex_web_research"].includes(normalized)) {
    return "secondary";
  }
  return "derived";
}

function normalizeResearchEntry(entry: Record<string, unknown>): Record<string, unknown> {
  const sourceSummary = Array.isArray(entry.source_summary) ? entry.source_summary : [];
  const evidenceCitations = Array.isArray(entry.evidence_citations) ? entry.evidence_citations : [];
  const errors = Array.isArray(entry.errors) ? entry.errors.filter((item) => typeof item === "string") : [];
  const normalizedSourceSummary = sourceSummary
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const record = item as Record<string, unknown>;
      return {
        ...record,
        tier: typeof record.tier === "string" ? record.tier : sourceTierFromType(String(record.source_type ?? "")),
      };
    });
  const normalizedEvidenceCitations = evidenceCitations
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const record = item as Record<string, unknown>;
      return {
        ...record,
        tier: typeof record.tier === "string" ? record.tier : sourceTierFromType(String(record.source_type ?? "")),
      };
    });

  let externalEvidenceStatus = String(entry.external_evidence_status ?? "").trim().toLowerCase();
  if (!["fresh", "partial", "missing"].includes(externalEvidenceStatus)) {
    if (normalizedSourceSummary.length === 0 && normalizedEvidenceCitations.length === 0) {
      externalEvidenceStatus = "missing";
    } else if (errors.length > 0) {
      externalEvidenceStatus = "partial";
    } else {
      externalEvidenceStatus = "fresh";
    }
  }

  return {
    ...entry,
    source_summary: normalizedSourceSummary,
    evidence_citations: normalizedEvidenceCitations,
    errors,
    external_evidence_status: externalEvidenceStatus,
  };
}

function mergeUsageMetrics(primaryUsage: unknown, secondaryUsage: unknown): unknown {
  if (!primaryUsage || typeof primaryUsage !== "object" || Array.isArray(primaryUsage)) {
    return primaryUsage ?? secondaryUsage ?? null;
  }
  const merged: Record<string, unknown> = { ...(primaryUsage as Record<string, unknown>) };
  if (!secondaryUsage || typeof secondaryUsage !== "object" || Array.isArray(secondaryUsage)) {
    return merged;
  }
  for (const [key, value] of Object.entries(secondaryUsage as Record<string, unknown>)) {
    if (typeof value === "number" && typeof merged[key] === "number") {
      merged[key] = Number(merged[key]) + value;
      continue;
    }
    if (!(key in merged)) {
      merged[key] = value;
    }
  }
  return merged;
}

function mergeResearchEntries(
  fastFactsResults: Array<Record<string, unknown>>,
  enrichmentResults: Array<Record<string, unknown>>,
): Array<Record<string, unknown>> {
  const merged = new Map<string, Record<string, unknown>>();
  for (const rawEntry of fastFactsResults) {
    const entry = normalizeResearchEntry(rawEntry);
    merged.set(String(entry.symbol ?? ""), entry);
  }

  for (const rawEntry of enrichmentResults) {
    const entry = normalizeResearchEntry(rawEntry);
    const symbol = String(entry.symbol ?? "");
    const existing = merged.get(symbol);
    if (!existing) {
      merged.set(symbol, entry);
      continue;
    }

    const mergedEntry: Record<string, unknown> = { ...existing };
    for (const field of ["summary", "research_summary", "news", "financial_data", "filings", "market_context"] as const) {
      if (String(entry[field] ?? "").trim()) {
        mergedEntry[field] = entry[field];
      }
    }
    for (const field of ["sources", "evidence", "risks"] as const) {
      const existingValues = Array.isArray(mergedEntry[field]) ? mergedEntry[field] as unknown[] : [];
      const incomingValues = Array.isArray(entry[field]) ? entry[field] as unknown[] : [];
      mergedEntry[field] = Array.from(new Set([...existingValues, ...incomingValues].filter(Boolean)));
    }
    mergedEntry.source_summary = Array.from(
      new Map(
        [
          ...(Array.isArray(mergedEntry.source_summary) ? mergedEntry.source_summary : []),
          ...(Array.isArray(entry.source_summary) ? entry.source_summary : []),
        ]
          .filter((item) => item && typeof item === "object")
          .map((item) => [`${String((item as Record<string, unknown>).source_type ?? "")}:${String((item as Record<string, unknown>).label ?? "")}:${String((item as Record<string, unknown>).timestamp ?? "")}`, item]),
      ).values(),
    );
    mergedEntry.evidence_citations = Array.from(
      new Map(
        [
          ...(Array.isArray(mergedEntry.evidence_citations) ? mergedEntry.evidence_citations : []),
          ...(Array.isArray(entry.evidence_citations) ? entry.evidence_citations : []),
        ]
          .filter((item) => item && typeof item === "object")
          .map((item) => [`${String((item as Record<string, unknown>).source_type ?? "")}:${String((item as Record<string, unknown>).reference ?? "")}`, item]),
      ).values(),
    );
    const errorSet = new Set<string>([
      ...((Array.isArray(mergedEntry.errors) ? mergedEntry.errors : []) as string[]),
      ...((Array.isArray(entry.errors) ? entry.errors : []) as string[]),
    ]);
    mergedEntry.errors = Array.from(errorSet);

    const externalEvidenceStatus =
      String(existing.external_evidence_status ?? "") === "missing" && String(entry.external_evidence_status ?? "") === "fresh"
        ? "partial"
        : String(entry.external_evidence_status ?? existing.external_evidence_status ?? "partial");
    mergedEntry.external_evidence_status = externalEvidenceStatus;
    merged.set(symbol, normalizeResearchEntry(mergedEntry));
  }

  return Array.from(merged.values()).map((entry) => normalizeResearchEntry(entry));
}

function updateRuntimeHealth(snapshot: Partial<RuntimeHealthSnapshot>) {
  runtimeHealth = {
    ...runtimeHealth,
    ...snapshot,
    checked_at: isoNow(),
  };
}

function extractJsonPayload(text: string): unknown {
  const trimmed = (text || "").trim();
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fenced?.[1]) {
    return JSON.parse(fenced[1]);
  }

  const objectStart = trimmed.search(/[\[{]/);
  if (objectStart >= 0) {
    const candidate = trimmed.slice(objectStart);
    return JSON.parse(candidate);
  }

  return JSON.parse(trimmed);
}

function classifyRuntimeError(
  error: unknown,
): Pick<RuntimeHealthSnapshot, "status" | "authenticated" | "usage_limited" | "message"> {
  const message = String((error as { message?: string })?.message ?? error ?? "Unknown Codex runtime failure").trim();
  const lowered = message.toLowerCase();
  const usageLimited =
    lowered.includes("usage limit") ||
    lowered.includes("rate limit") ||
    lowered.includes("quota") ||
    lowered.includes("spending cap");
  const authenticated = !(
    lowered.includes("login") ||
    lowered.includes("sign in") ||
    lowered.includes("not authenticated") ||
    lowered.includes("auth required")
  );
  return {
    status: usageLimited ? "degraded" : "blocked",
    authenticated,
    usage_limited: usageLimited,
    message,
  };
}

function normalizeOutputSchema(schema: JsonSchema): JsonSchema {
  return normalizeSchemaNode(structuredClone(schema)) as JsonSchema;
}

function normalizeSchemaNode(node: unknown): unknown {
  if (Array.isArray(node)) {
    return node.map(normalizeSchemaNode);
  }

  if (!node || typeof node !== "object") {
    return node;
  }

  const normalized = Object.fromEntries(
    Object.entries(node as Record<string, unknown>).map(([key, value]) => [key, normalizeSchemaNode(value)]),
  ) as Record<string, unknown>;

  if ("$defs" in normalized && normalized.$defs && typeof normalized.$defs === "object") {
    normalized.$defs = Object.fromEntries(
      Object.entries(normalized.$defs as Record<string, unknown>).map(([key, value]) => [key, normalizeSchemaNode(value)]),
    );
  }

  const properties = normalized.properties;
  const isObjectSchema =
    normalized.type === "object" ||
    (!!properties && typeof properties === "object" && !Array.isArray(properties)) ||
    "additionalProperties" in normalized;

  if (isObjectSchema) {
    const propertyMap =
      properties && typeof properties === "object" && !Array.isArray(properties)
        ? (properties as Record<string, unknown>)
        : {};
    normalized.type = "object";
    normalized.properties = Object.fromEntries(
      Object.entries(propertyMap).map(([key, value]) => [key, normalizeSchemaNode(value)]),
    );
    normalized.additionalProperties = false;
    normalized.required = Object.keys(normalized.properties as Record<string, unknown>);
  }

  if ("items" in normalized) {
    normalized.items = normalizeSchemaNode(normalized.items);
  }
  if (Array.isArray(normalized.anyOf)) {
    normalized.anyOf = normalized.anyOf.map(normalizeSchemaNode);
  }
  if (Array.isArray(normalized.allOf)) {
    normalized.allOf = normalized.allOf.map(normalizeSchemaNode);
  }
  if (Array.isArray(normalized.oneOf)) {
    normalized.oneOf = normalized.oneOf.map(normalizeSchemaNode);
  }

  return normalized;
}

async function runStructured(request: z.infer<typeof structuredRunRequestSchema>) {
  const model = request.model ?? defaultModel;
  const reasoning = request.reasoning ?? lightReasoning;
  const timeoutMs = Math.round((request.timeout_seconds ?? 90) * 1000);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const thread = codex.startThread({
      model,
      approvalPolicy: "never",
      sandboxMode: "read-only",
      skipGitRepoCheck: true,
      workingDirectory: request.working_directory ?? defaultWorkdir,
      modelReasoningEffort: reasoning,
      networkAccessEnabled: request.network_access_enabled ?? request.web_search_enabled ?? false,
      webSearchEnabled: request.web_search_enabled ?? false,
      webSearchMode: request.web_search_enabled ? request.web_search_mode ?? "live" : "disabled",
    });
    const turn = await thread.run(
      `${request.system_prompt}\n\n${request.prompt}`,
      {
        outputSchema: normalizeOutputSchema(request.output_schema),
        signal: controller.signal,
      },
    );
    const parsed = extractJsonPayload(turn.finalResponse);
    updateRuntimeHealth({
      status: "ready",
      authenticated: true,
      usage_limited: false,
      message: "Codex runtime is reachable.",
      model,
      reasoning_profile: reasoning,
    });
    return {
      output: parsed,
      provider_metadata: providerMetadata(thread.id ?? request.session_id ?? crypto.randomUUID(), model, reasoning),
      usage: turn.usage,
      raw_response: turn.finalResponse,
    };
  } catch (error) {
    const classified = classifyRuntimeError(error);
    updateRuntimeHealth({
      status: classified.status,
      authenticated: classified.authenticated,
      usage_limited: classified.usage_limited,
      message: classified.message,
      model,
      reasoning_profile: reasoning,
    });
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function validateRuntime(request?: {
  model?: string;
  reasoning?: ModelReasoningEffort;
  timeout_seconds?: number;
}) {
  const result = await runStructured({
    system_prompt: "Return only valid JSON for Robo Trader runtime validation.",
    prompt: [
      "Perform a minimal Codex runtime validation for Robo Trader.",
      "Return exactly one JSON object confirming the runtime executed successfully.",
      "Set validation_status to ok.",
    ].join("\n"),
    output_schema: runtimeValidationResultSchema,
    model: request?.model ?? defaultModel,
    reasoning: request?.reasoning ?? lightReasoning,
    timeout_seconds: request?.timeout_seconds ?? 20,
    web_search_enabled: false,
    network_access_enabled: false,
  });

  return {
    ...runtimeHealth,
    provider_metadata: result.provider_metadata,
    validation: result.output,
    usage: result.usage,
  };
}

async function runBatchResearch(request: z.infer<typeof batchResearchRequestSchema>) {
  const model = request.model ?? defaultModel;
  const reasoning = request.reasoning ?? deepReasoning;
  const totalTimeoutSeconds = request.timeout_seconds ?? 120;
  const fastFactsTimeoutSeconds = Math.max(12, Math.min(Math.floor(totalTimeoutSeconds * 0.65), totalTimeoutSeconds - 5));
  const startedAtMs = Date.now();

  const fastFactsPrompt = [
    "You are Robo Trader's external market researcher.",
    "Stage: fast_facts.",
    "Gather only the most decision-relevant fresh facts for each requested Indian equity symbol.",
    "For each symbol, aim to return one fresh catalyst or material news item, one filing/disclosure if available, one recent fundamentals datapoint if available, and one concrete risk.",
    "Prefer exchange filings, company announcements, investor-relations pages, and reputable financial press.",
    "Return partial but truthful results when evidence is thin. Do not wait for exhaustive enrichment.",
    "Do not invent prices, catalysts, analyst targets, or filings.",
    "Return JSON only.",
    "",
    `Research brief: ${request.research_brief ?? "Gather fresh company news, fundamentals, filings, and market context for swing-trading screening."}`,
    "",
    `Symbols: ${request.symbols.join(", ")}`,
    `Company names: ${JSON.stringify(request.company_names ?? {})}`,
    "",
    "For every symbol include:",
    "- summary",
    "- research_summary",
    "- news",
    "- financial_data",
    "- filings",
    "- market_context",
    "- sources",
    "- source_summary",
    "- evidence_citations",
    "- evidence",
    "- risks",
    "- errors",
    "- external_evidence_status",
    "",
    "Use tier values:",
    "- primary: exchange filings, company disclosures, company IR",
    "- secondary: reputable financial press",
    "- derived: synthesized internal references",
    "",
    "Mark external_evidence_status as fresh when you found enough fresh evidence, partial when some evidence is missing but still useful, and missing when no real evidence is available.",
  ].join("\n");

  const fastFactsResult = await runStructured({
    system_prompt: "Return only valid JSON for Robo Trader batch market research fast facts.",
    prompt: fastFactsPrompt,
    output_schema: batchResearchResultSchema,
    model,
    reasoning,
    timeout_seconds: fastFactsTimeoutSeconds,
    web_search_enabled: true,
    web_search_mode: "live",
    network_access_enabled: true,
  });

  const fastFactsResults = Array.isArray((fastFactsResult.output as { results?: unknown[] }).results)
    ? ((fastFactsResult.output as { results: Array<Record<string, unknown>> }).results || []).map((entry) => normalizeResearchEntry(entry))
    : [];

  const elapsedSeconds = (Date.now() - startedAtMs) / 1000;
  const remainingSeconds = Math.max(totalTimeoutSeconds - elapsedSeconds, 0);
  if (remainingSeconds < 12) {
    return {
      output: {
        results: fastFactsResults.map((entry) =>
          normalizeResearchEntry({
            ...entry,
            external_evidence_status:
              String(entry.external_evidence_status ?? "") === "fresh" ? "partial" : entry.external_evidence_status,
          }),
        ),
      },
      provider_metadata: {
        ...fastFactsResult.provider_metadata,
        research_stage: "fast_facts_only",
      },
      usage: fastFactsResult.usage,
      raw_response: fastFactsResult.raw_response,
    };
  }

  const enrichmentPrompt = [
    "You are Robo Trader's external market researcher.",
    "Stage: optional_enrichment.",
    "You already have a fast_facts pass. Only enrich what is still missing or weak.",
    "Do not repeat generic background. Add only higher-signal fresh evidence, better citations, or clearer risks.",
    "Return JSON only.",
    "",
    `Research brief: ${request.research_brief ?? "Gather fresh company news, fundamentals, filings, and market context for swing-trading screening."}`,
    "",
    `Symbols: ${request.symbols.join(", ")}`,
    `Company names: ${JSON.stringify(request.company_names ?? {})}`,
    "",
    "For every symbol include the same schema as fast_facts, but only fill fields when you genuinely improved them.",
    "Keep source tiers accurate.",
  ].join("\n");

  try {
    const enrichmentResult = await runStructured({
      system_prompt: "Return only valid JSON for Robo Trader batch market research optional enrichment.",
      prompt: enrichmentPrompt,
      output_schema: batchResearchResultSchema,
      model,
      reasoning,
      timeout_seconds: remainingSeconds,
      web_search_enabled: true,
      web_search_mode: "live",
      network_access_enabled: true,
    });
    const enrichmentResults = Array.isArray((enrichmentResult.output as { results?: unknown[] }).results)
      ? ((enrichmentResult.output as { results: Array<Record<string, unknown>> }).results || []).map((entry) => normalizeResearchEntry(entry))
      : [];
    return {
      output: {
        results: mergeResearchEntries(fastFactsResults, enrichmentResults),
      },
      provider_metadata: {
        ...fastFactsResult.provider_metadata,
        research_stage: "fast_facts_plus_enrichment",
      },
      usage: mergeUsageMetrics(fastFactsResult.usage, enrichmentResult.usage),
      raw_response: enrichmentResult.raw_response,
    };
  } catch (error) {
    const classified = classifyRuntimeError(error);
    return {
      output: {
        results: fastFactsResults.map((entry) =>
          normalizeResearchEntry({
            ...entry,
            errors: Array.from(
              new Set([
                ...((Array.isArray(entry.errors) ? entry.errors : []) as string[]),
                `optional_enrichment: ${classified.message}`,
              ]),
            ),
            external_evidence_status:
              String(entry.external_evidence_status ?? "") === "fresh" ? "partial" : entry.external_evidence_status,
          }),
        ),
      },
      provider_metadata: {
        ...fastFactsResult.provider_metadata,
        research_stage: "fast_facts_partial",
      },
      usage: fastFactsResult.usage,
      raw_response: fastFactsResult.raw_response,
    };
  }
}

async function runDiscoveryScout(request: z.infer<typeof discoveryScoutRequestSchema>) {
  const model = request.model ?? defaultModel;
  const reasoning = request.reasoning ?? deepReasoning;
  const prompt = [
    "You are Robo Trader's discovery scout for Indian equities.",
    "Study the current Indian market state, sector rotation, business news, filings, and fundamental momentum.",
    "Find a very small list of dark-horse swing-trade candidates with strong or improving fundamentals.",
    "Avoid default crowded mega-cap names unless the current evidence is unusually compelling.",
    "Do not walk a static universe or emit generic blue-chip lists.",
    "Return only valid JSON.",
    "",
    `Account scope: ${request.account_id ?? "paper-trading operator"}`,
    `Requested limit: ${request.limit}`,
    `Criteria: ${JSON.stringify(request.criteria ?? {})}`,
    `Memory context: ${JSON.stringify(request.memory_context ?? {})}`,
    "",
    "Output requirements:",
    "- market_state_summary: concise current market posture in India",
    "- favored_sectors: up to 4 sectors/themes benefiting from current conditions",
    "- caution_sectors: up to 4 sectors/themes to avoid",
    "- key_insights: short bullets describing what discovery is leaning into or avoiding",
    "- candidates: up to the requested limit",
    "",
    "Each candidate must include:",
    "- symbol",
    "- company_name",
    "- sector",
    "- discovery_reason",
    "- opportunity_score (0-100)",
    "- research_timestamp",
    "- summary",
    "- research_summary",
    "- news",
    "- financial_data",
    "- filings",
    "- market_context",
    "- source_summary",
    "- evidence_citations",
    "- evidence",
    "- risks",
    "- errors",
    "",
    "Candidate standards:",
    "- prefer underfollowed, improving, or newly re-rating names",
    "- require a concrete why-now and at least one fundamental reason",
    "- if evidence is weak, omit the candidate instead of padding the list",
    "- use source_type 'codex_web_research' in source summaries and citations",
    "- keep fields concise and factual",
  ].join("\n");

  return await runStructured({
    system_prompt: "Return only valid JSON for Robo Trader discovery scouting.",
    prompt,
    output_schema: discoveryScoutResultSchema,
    model,
    reasoning,
    timeout_seconds: request.timeout_seconds ?? 90,
    web_search_enabled: true,
    web_search_mode: "live",
    network_access_enabled: true,
  });
}

app.get("/health", async (_req: Request, res: Response) => {
  res.json(runtimeHealth);
});

app.post("/v1/runtime/validate", async (_req: Request, res: Response) => {
  try {
    const result = await validateRuntime();
    res.json(result);
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      ...runtimeHealth,
      status: classified.status,
      authenticated: classified.authenticated,
      usage_limited: classified.usage_limited,
      message: classified.message,
      provider: "codex",
    });
  }
});

app.post("/v1/structured/run", async (req: Request, res: Response) => {
  const parsed = structuredRunRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid structured run request", detail: parsed.error.flatten() });
    return;
  }
  try {
    const result = await runStructured(parsed.data);
    res.json(result);
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      error: "Codex runtime request failed",
      detail: classified.message,
      usage_limited: classified.usage_limited,
      provider: "codex",
    });
  }
});

app.post("/v1/research/focused", async (req: Request, res: Response) => {
  const parsed = structuredRunRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid focused research request", detail: parsed.error.flatten() });
    return;
  }
  try {
    const result = await runStructured(parsed.data);
    res.json({
      research: result.output,
      provider_metadata: result.provider_metadata,
      usage: result.usage,
    });
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      error: "Focused research failed",
      detail: classified.message,
      usage_limited: classified.usage_limited,
      provider: "codex",
    });
  }
});

app.post("/v1/research/batch", async (req: Request, res: Response) => {
  const parsed = batchResearchRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid batch research request", detail: parsed.error.flatten() });
    return;
  }
  try {
    const result = await runBatchResearch(parsed.data);
    const rawResults = Array.isArray((result.output as { results?: unknown[] }).results)
      ? (result.output as { results: Array<Record<string, unknown>> }).results
      : [];
    const results = Object.fromEntries(
      rawResults
        .filter((entry) => entry && typeof entry === "object")
        .map((entry) => [String(entry.symbol ?? ""), entry]),
    );
    res.json({
      results,
      provider_metadata: result.provider_metadata,
      usage: result.usage,
    });
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      error: "Batch research failed",
      detail: classified.message,
      usage_limited: classified.usage_limited,
      provider: "codex",
    });
  }
});

app.post("/v1/research/discovery-scout", async (req: Request, res: Response) => {
  const parsed = discoveryScoutRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid discovery scout request", detail: parsed.error.flatten() });
    return;
  }
  try {
    const result = await runDiscoveryScout(parsed.data);
    res.json({
      ...((result.output as Record<string, unknown>) ?? {}),
      provider_metadata: result.provider_metadata,
      usage: result.usage,
    });
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      error: "Discovery scout failed",
      detail: classified.message,
      usage_limited: classified.usage_limited,
      provider: "codex",
    });
  }
});

app.post("/v1/prompt-optimization/analyze", async (req: Request, res: Response) => {
  const parsed = promptOptimizationRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid prompt optimization request", detail: parsed.error.flatten() });
    return;
  }
  const request = parsed.data;
  const prompt = [
    `You are Robo Trader's research-brief optimizer for ${request.data_type} data.`,
    "Evaluate the retrieved data quality for trading usefulness, then rewrite the brief to improve the next fetch.",
    "Return JSON only.",
    "",
    "Current brief:",
    request.current_prompt,
    "",
    "Retrieved data:",
    request.retrieved_data || "[no data returned]",
    "",
    "Known missing elements:",
    JSON.stringify(request.missing_elements, null, 2),
    "",
    "Known redundant elements:",
    JSON.stringify(request.redundant_elements, null, 2),
    "",
    "Quality feedback:",
    request.quality_feedback || "[none]",
    "",
    `Attempt number: ${request.attempt_number}`,
  ].join("\n");

  try {
    const result = await runStructured({
      system_prompt: "Return only valid JSON for Robo Trader prompt optimization.",
      prompt,
      output_schema: promptOptimizationResponseSchema,
      model: request.model ?? defaultModel,
      reasoning: request.reasoning ?? deepReasoning,
      timeout_seconds: request.timeout_seconds ?? 90,
      web_search_enabled: false,
      network_access_enabled: false,
    });
    res.json({
      optimization: result.output,
      provider_metadata: result.provider_metadata,
      usage: result.usage,
    });
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      error: "Prompt optimization failed",
      detail: classified.message,
      usage_limited: classified.usage_limited,
      provider: "codex",
    });
  }
});

app.post("/v1/improvement/review", async (req: Request, res: Response) => {
  const parsed = structuredRunRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid improvement review request", detail: parsed.error.flatten() });
    return;
  }
  try {
    const result = await runStructured(parsed.data);
    res.json({
      review: result.output,
      provider_metadata: result.provider_metadata,
      usage: result.usage,
    });
  } catch (error) {
    const classified = classifyRuntimeError(error);
    res.status(classified.usage_limited ? 429 : 503).json({
      error: "Improvement review failed",
      detail: classified.message,
      usage_limited: classified.usage_limited,
      provider: "codex",
    });
  }
});

app.listen(port, host, () => {
  console.log(`Codex runtime listening on http://${host}:${port}`);
});
