import React, { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  AlertTriangle,
  CheckCircle,
  Zap,
} from 'lucide-react'
import type { QueuePerformanceMetrics, QueueType } from '@/types/queue'

interface QueuePerformanceMetricsProps {
  metrics: QueuePerformanceMetrics[]
  selectedQueue?: QueueType
  onQueueSelect: (queueType: QueueType) => void
  isLoading?: boolean
}

const MetricCard: React.FC<{
  title: string
  value: string | number
  change?: number
  icon: React.ReactNode
  color: string
  subtitle?: string
}> = ({ title, value, change, icon, color, subtitle }) => (
  <Card className="card-base p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-warmgray-600">{title}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        {subtitle && <p className="text-xs text-warmgray-500 mt-1">{subtitle}</p>}
        {change !== undefined && (
          <div className={`flex items-center mt-1 text-xs ${
            change >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {change >= 0 ? (
              <TrendingUp className="w-3 h-3 mr-1" />
            ) : (
              <TrendingDown className="w-3 h-3 mr-1" />
            )}
            {Math.abs(change).toFixed(1)}%
          </div>
        )}
      </div>
      <div className={`p-2 rounded-lg bg-warmgray-100 ${color.replace('text-', 'text-').replace('-600', '-500')}`}>
        {icon}
      </div>
    </div>
  </Card>
)

const PerformanceChart: React.FC<{
  data: number[]
  title: string
  color: string
}> = ({ data, title, color }) => {
  const maxValue = Math.max(...data, 1)
  const minValue = Math.min(...data, 0)

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-warmgray-700">{title}</h4>
      <div className="flex items-end space-x-1 h-16">
        {data.slice(-10).map((value, index) => {
          const height = ((value - minValue) / (maxValue - minValue)) * 100
          return (
            <div
              key={index}
              className={`flex-1 rounded-sm ${color}`}
              style={{ height: `${Math.max(height, 4)}%` }}
            />
          )
        })}
      </div>
      <div className="flex justify-between text-xs text-warmgray-500">
        <span>{minValue.toFixed(1)}</span>
        <span>{maxValue.toFixed(1)}</span>
      </div>
    </div>
  )
}

export const QueuePerformanceMetrics: React.FC<QueuePerformanceMetricsProps> = ({
  metrics,
  selectedQueue,
  onQueueSelect,
  isLoading = false,
}) => {
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('24h')

  const currentMetrics = selectedQueue
    ? metrics.find(m => m.queue_type === selectedQueue)
    : metrics[0]

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="card-base p-4">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-warmgray-200 rounded w-3/4"></div>
              <div className="h-8 bg-warmgray-200 rounded w-1/2"></div>
              <div className="h-3 bg-warmgray-200 rounded w-1/4"></div>
            </div>
          </Card>
        ))}
      </div>
    )
  }

  if (!currentMetrics) {
    return (
      <Card className="card-base">
        <div className="p-12 text-center">
          <BarChart3 className="w-12 h-12 text-warmgray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-warmgray-900 mb-2">No Metrics Available</h3>
          <p className="text-warmgray-600">Performance metrics will appear here once data is available.</p>
        </div>
      </Card>
    )
  }

  const throughputChange = currentMetrics.throughput_trend.length > 1
    ? ((currentMetrics.tasks_per_second - currentMetrics.throughput_trend[currentMetrics.throughput_trend.length - 2]) / currentMetrics.throughput_trend[currentMetrics.throughput_trend.length - 2]) * 100
    : 0

  const latencyChange = currentMetrics.latency_trend.length > 1
    ? ((currentMetrics.average_execution_time_ms - currentMetrics.latency_trend[currentMetrics.latency_trend.length - 2]) / currentMetrics.latency_trend[currentMetrics.latency_trend.length - 2]) * 100
    : 0

  const errorChange = currentMetrics.error_trend.length > 1
    ? ((currentMetrics.error_rate_percentage - currentMetrics.error_trend[currentMetrics.error_trend.length - 2]) / currentMetrics.error_trend[currentMetrics.error_trend.length - 2]) * 100
    : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-warmgray-900">Performance Metrics</h2>

        <div className="flex items-center gap-4">
          <Select value={timeRange} onValueChange={(value) => setTimeRange(value as typeof timeRange)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="6h">Last 6 Hours</SelectItem>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
            </SelectContent>
          </Select>

          {selectedQueue && (
            <Badge variant="outline">
              {selectedQueue.replace('_', ' ')}
            </Badge>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Tasks Processed"
          value={currentMetrics.total_tasks_processed.toLocaleString()}
          icon={<CheckCircle className="w-5 h-5" />}
          color="text-green-600"
          subtitle={`Last ${timeRange}`}
        />

        <MetricCard
          title="Throughput"
          value={`${currentMetrics.tasks_per_second.toFixed(2)}/s`}
          change={throughputChange}
          icon={<Zap className="w-5 h-5" />}
          color="text-blue-600"
          subtitle="Tasks per second"
        />

        <MetricCard
          title="Avg Latency"
          value={`${currentMetrics.average_execution_time_ms.toFixed(0)}ms`}
          change={latencyChange}
          icon={<Clock className="w-5 h-5" />}
          color="text-purple-600"
          subtitle="Execution time"
        />

        <MetricCard
          title="Error Rate"
          value={`${currentMetrics.error_rate_percentage.toFixed(2)}%`}
          change={errorChange}
          icon={<AlertTriangle className="w-5 h-5" />}
          color={currentMetrics.error_rate_percentage > 5 ? "text-red-600" : "text-yellow-600"}
          subtitle="Failure percentage"
        />
      </div>

      {/* System Resources */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="card-base p-6">
          <h3 className="text-lg font-semibold text-warmgray-900 mb-4">System Resources</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-warmgray-600">Memory Usage</span>
                <span className="font-medium">{currentMetrics.memory_usage_mb.toFixed(1)} MB</span>
              </div>
              <Progress value={(currentMetrics.memory_usage_mb / 1024) * 100} className="h-2" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-warmgray-600">CPU Usage</span>
                <span className="font-medium">{currentMetrics.cpu_usage_percentage.toFixed(1)}%</span>
              </div>
              <Progress value={currentMetrics.cpu_usage_percentage} className="h-2" />
            </div>
          </div>
        </Card>

        <Card className="card-base p-6">
          <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Health Indicators</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-warmgray-600">Throughput Stability</span>
              <Badge variant={Math.abs(throughputChange) < 10 ? 'success' : 'warning'}>
                {Math.abs(throughputChange) < 10 ? 'Stable' : 'Variable'}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-warmgray-600">Latency Performance</span>
              <Badge variant={currentMetrics.average_execution_time_ms < 5000 ? 'success' : 'warning'}>
                {currentMetrics.average_execution_time_ms < 5000 ? 'Good' : 'Slow'}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-warmgray-600">Error Rate</span>
              <Badge variant={currentMetrics.error_rate_percentage < 5 ? 'success' : 'error'}>
                {currentMetrics.error_rate_percentage < 5 ? 'Low' : 'High'}
              </Badge>
            </div>
          </div>
        </Card>
      </div>

      {/* Trend Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="card-base p-6">
          <PerformanceChart
            data={currentMetrics.throughput_trend}
            title="Throughput Trend"
            color="bg-blue-500"
          />
        </Card>

        <Card className="card-base p-6">
          <PerformanceChart
            data={currentMetrics.latency_trend}
            title="Latency Trend"
            color="bg-purple-500"
          />
        </Card>

        <Card className="card-base p-6">
          <PerformanceChart
            data={currentMetrics.error_trend}
            title="Error Rate Trend"
            color="bg-red-500"
          />
        </Card>
      </div>

      {/* Queue Selection */}
      <Card className="card-base p-6">
        <h3 className="text-lg font-semibold text-warmgray-900 mb-4">Select Queue</h3>
        <div className="flex flex-wrap gap-2">
          {metrics.map((metric) => (
            <Button
              key={metric.queue_type}
              variant={selectedQueue === metric.queue_type ? 'default' : 'outline'}
              size="sm"
              onClick={() => onQueueSelect(metric.queue_type)}
            >
              {metric.queue_type.replace('_', ' ')}
            </Button>
          ))}
        </div>
      </Card>
    </div>
  )
}