import { z } from 'zod';

// Progressive disclosure schemas for token efficiency
export const CategorySchema = z.object({
  name: z.string(),
  description: z.string(),
  tools: z.array(z.string()),
  token_efficiency: z.string(),
  use_cases: z.array(z.string())
});

export const ToolInputSchema = z.object({
  tool_name: z.string(),
  args: z.record(z.string(), z.any())
});

// Core tool schemas
export const AnalyzeLogsSchema = z.object({
  patterns: z.array(z.string()).min(1).describe("Error patterns to search for (e.g., ['database is locked', 'timeout'])"),
  time_window: z.string().optional().default("1h").describe("Time window to analyze (e.g., '1h', '24h')"),
  max_examples: z.number().optional().default(3).describe("Maximum examples per pattern"),
  group_by: z.string().optional().default("error_type").describe("How to group results")
});

export const QueryPortfolioSchema = z.object({
  filters: z.array(z.string()).optional().default([]).describe("Filters to apply (e.g., ['stale_analysis', 'error_conditions'])"),
  limit: z.number().optional().default(20).describe("Maximum results to return"),
  aggregation_only: z.boolean().optional().default(true).describe("Return only aggregated insights")
});

export const DiagnoseLocksSchema = z.object({
  time_window: z.string().optional().default("24h").describe("Time window for lock analysis"),
  include_code_references: z.boolean().optional().default(true).describe("Include source code references"),
  suggest_fixes: z.boolean().optional().default(true).describe("Suggest specific fixes")
});

export const CheckHealthSchema = z.object({
  components: z.array(z.string()).optional().default(["database", "queues", "api_endpoints", "disk_space", "backup_status"]).describe("Components to check"),
  verbose: z.boolean().optional().default(false).describe("Include detailed status")
});

export const VerifyConfigSchema = z.object({
  checks: z.array(z.string()).optional().default(["database_paths", "api_endpoints", "queue_settings", "security_settings"]).describe("Configuration checks to perform"),
  include_suggestions: z.boolean().optional().default(true).describe("Include improvement suggestions")
});

// New monitoring tool schemas
export const QueueStatusSchema = z.object({
  use_cache: z.boolean().optional().default(true).describe("Use cached data if available (60s TTL)"),
  include_details: z.boolean().optional().default(false).describe("Include detailed queue information")
});

export const CoordinatorStatusSchema = z.object({
  use_cache: z.boolean().optional().default(true).describe("Use cached data if available (45s TTL)"),
  check_critical_only: z.boolean().optional().default(false).describe("Check only critical coordinators")
});

export const TaskExecutionMetricsSchema = z.object({
  use_cache: z.boolean().optional().default(true).describe("Use cached data if available (120s TTL)"),
  time_window_hours: z.number().optional().default(24).describe("Time window for metrics analysis (hours)"),
  include_trends: z.boolean().optional().default(true).describe("Include error trend analysis")
});

// Response schemas for consistent output
export const ToolResponseSchema = z.object({
  success: z.boolean(),
  data: z.any().optional(),
  error: z.string().optional(),
  token_efficiency: z.string().optional(),
  execution_time_ms: z.number().optional()
});

export type ToolResponse = z.infer<typeof ToolResponseSchema>;
export type AnalyzeLogsInput = z.infer<typeof AnalyzeLogsSchema>;
export type QueryPortfolioInput = z.infer<typeof QueryPortfolioSchema>;
export type DiagnoseLocksInput = z.infer<typeof DiagnoseLocksSchema>;
export type CheckHealthInput = z.infer<typeof CheckHealthSchema>;
export type VerifyConfigInput = z.infer<typeof VerifyConfigSchema>;
export type QueueStatusInput = z.infer<typeof QueueStatusSchema>;
export type CoordinatorStatusInput = z.infer<typeof CoordinatorStatusSchema>;
export type TaskExecutionMetricsInput = z.infer<typeof TaskExecutionMetricsSchema>;