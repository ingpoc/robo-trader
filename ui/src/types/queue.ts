// Queue Management Types
export type QueueType = 'PORTFOLIO_SCHEDULER' | 'DATA_FETCHER_SCHEDULER' | 'AI_ANALYSIS_QUEUE';

export type TaskStatus = 'pending' | 'executing' | 'completed' | 'failed' | 'cancelled';

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export interface TaskMetadata {
  [key: string]: string | number | boolean | string[] | undefined;
}

export interface QueueTask {
  id: string;
  queue_type: QueueType;
  task_type: string;
  status: TaskStatus;
  priority: TaskPriority;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  execution_time_ms?: number;
  metadata: TaskMetadata;
}

export interface QueueStatus {
  queue_type: QueueType;
  name: string;
  description: string;
  is_active: boolean;
  total_tasks: number;
  pending_tasks: number;
  executing_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  average_execution_time_ms: number;
  throughput_per_minute: number;
  error_rate_percentage: number;
  last_activity_at?: string;
  configuration: QueueConfiguration;
}

export interface QueueConfiguration {
  queue_type: QueueType;
  enabled: boolean;
  max_concurrent_tasks: number;
  max_retries: number;
  timeout_seconds: number;
  priority_weights: Record<TaskPriority, number>;
  scheduling_frequency_seconds: number;
  batch_size: number;
  circuit_breaker_enabled: boolean;
  circuit_breaker_threshold: number;
  circuit_breaker_timeout_seconds: number;
}

export interface TaskExecutionHistory {
  id: string;
  queue_type: QueueType;
  task_type: string;
  status: TaskStatus;
  priority: TaskPriority;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  execution_time_ms?: number;
  error_message?: string;
  retry_count: number;
  metadata: TaskMetadata;
}

export interface QueuePerformanceMetrics {
  queue_type: QueueType;
  timestamp: string;
  total_tasks_processed: number;
  tasks_per_second: number;
  average_execution_time_ms: number;
  error_rate_percentage: number;
  throughput_trend: number[];
  latency_trend: number[];
  error_trend: number[];
  memory_usage_mb: number;
  cpu_usage_percentage: number;
}

export interface QueueManagementState {
  queues: QueueStatus[];
  selectedQueue?: QueueType;
  tasks: QueueTask[];
  executionHistory: TaskExecutionHistory[];
  performanceMetrics: QueuePerformanceMetrics[];
  stats?: Partial<QueueStats>;
  isLoading: boolean;
  error?: string;
  lastUpdated: string;
}

export interface QueueTriggerRequest {
  queue_type: QueueType;
  task_type?: string;
  priority?: TaskPriority;
  metadata?: TaskMetadata;
}

export interface QueueConfigurationUpdate {
  queue_type: QueueType;
  configuration: Partial<QueueConfiguration>;
}

export interface TaskFilter {
  queue_type?: QueueType;
  status?: TaskStatus[];
  priority?: TaskPriority[];
  task_type?: string[];
  date_range?: {
    start: string;
    end: string;
  };
}

export interface QueueStats {
  total_queues: number;
  active_queues: number;
  total_pending_tasks: number;
  total_executing_tasks: number;
  total_failed_tasks: number;
  system_health_score: number;
  average_throughput: number;
  overall_error_rate: number;
}

// WebSocket event types for real-time updates
export type QueueWebSocketEventData =
  | QueueStatus
  | QueueTask
  | QueuePerformanceMetrics
  | { queue_type: QueueType; old_config: QueueConfiguration; new_config: QueueConfiguration };

export interface QueueWebSocketEvent {
  type: 'queue_status_update' | 'task_status_update' | 'performance_metrics_update' | 'configuration_change';
  data: QueueWebSocketEventData;
  timestamp: string;
  // Backend sends queues object with all queue statuses
  queues?: Record<string, { running?: boolean; status?: string; details?: Record<string, unknown> }>;
  // Backend sends stats object with aggregate statistics
  stats?: Partial<QueueStats>;
}

export interface QueueStatusUpdateEvent extends QueueWebSocketEvent {
  type: 'queue_status_update';
  data: QueueStatus;
}

export interface TaskStatusUpdateEvent extends QueueWebSocketEvent {
  type: 'task_status_update';
  data: QueueTask;
}

export interface PerformanceMetricsUpdateEvent extends QueueWebSocketEvent {
  type: 'performance_metrics_update';
  data: QueuePerformanceMetrics;
}

export interface ConfigurationChangeEvent extends QueueWebSocketEvent {
  type: 'configuration_change';
  data: {
    queue_type: QueueType;
    old_config: QueueConfiguration;
    new_config: QueueConfiguration;
  };
}