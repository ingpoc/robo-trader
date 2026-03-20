import {
  Area,
  AreaChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Tooltip as UITooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface ChartCardProps {
  title: string
  type: 'line' | 'pie' | 'area'
  data: Array<{ name: string; value: number; [key: string]: unknown }>
  height?: number
  showLegend?: boolean
  className?: string
  isLoading?: boolean
  detailed?: boolean
}

const COLORS = ['#0f766e', '#2563eb', '#7c3aed', '#ea580c', '#dc2626', '#4f46e5', '#0891b2', '#65a30d']

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ color: string; name: string; value: number }>; label?: string }) => {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  return (
    <div className="rounded-lg border border-border bg-background p-3 shadow-md">
      <p className="mb-1 text-sm font-medium text-foreground">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-sm text-muted-foreground">
            {entry.name}: <span className="font-semibold text-foreground">{entry.value}</span>
          </span>
        </div>
      ))}
    </div>
  )
}

export function ChartCard({
  title,
  type,
  data,
  height = 240,
  showLegend = false,
  className,
  isLoading = false,
}: ChartCardProps) {
  const isPositive = data.length > 1 && (data[data.length - 1]?.value ?? 0) >= (data[0]?.value ?? 0)

  if (isLoading) {
    return (
      <div className={`rounded-xl border border-border bg-card p-6 shadow-sm ${className || ''}`}>
        <div className="mb-6 h-5 w-40 animate-pulse rounded bg-muted" />
        <div className="h-[240px] animate-pulse rounded-lg bg-muted/70" />
      </div>
    )
  }

  return (
    <UITooltip>
      <TooltipTrigger asChild>
        <div className={`rounded-xl border border-border bg-card p-6 shadow-sm transition-shadow duration-200 hover:shadow-md ${className || ''}`}>
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-xl border border-border bg-muted p-3 text-muted-foreground">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold uppercase tracking-wide text-card-foreground">{title}</h3>
                {type === 'line' ? (
                  <div className={`mt-1 text-sm font-medium ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {isPositive ? 'Positive trend' : 'Negative trend'}
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={height}>
            {type === 'line' ? (
              <LineChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <defs>
                  <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0f766e" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#0f766e" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={{ stroke: '#e5e7eb' }} tickLine={{ stroke: '#e5e7eb' }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={{ stroke: '#e5e7eb' }} tickLine={{ stroke: '#e5e7eb' }} />
                <Tooltip content={<CustomTooltip />} />
                {showLegend ? <Legend /> : null}
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#0f766e"
                  strokeWidth={2.5}
                  dot={{ fill: '#0f766e', strokeWidth: 2, r: 4 }}
                  activeDot={{
                    r: 6,
                    stroke: '#0f766e',
                    strokeWidth: 2,
                    fill: '#ffffff',
                    style: { filter: 'drop-shadow(0 2px 4px rgba(15, 118, 110, 0.2))' },
                  }}
                  fill="url(#lineGradient)"
                  fillOpacity={1}
                />
              </LineChart>
            ) : type === 'area' ? (
              <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <defs>
                  <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={{ stroke: '#e5e7eb' }} tickLine={{ stroke: '#e5e7eb' }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={{ stroke: '#e5e7eb' }} tickLine={{ stroke: '#e5e7eb' }} />
                <Tooltip content={<CustomTooltip />} />
                {showLegend ? <Legend /> : null}
                <Area type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} fill="url(#areaGradient)" fillOpacity={1} />
              </AreaChart>
            ) : (
              <PieChart margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  label={({ name, percent }) => {
                    const numericPercent = typeof percent === 'number' ? percent : 0
                    return `${name}: ${(numericPercent * 100).toFixed(0)}%`
                  }}
                >
                  {data.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} style={{ filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.08))' }} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                {showLegend ? <Legend /> : null}
              </PieChart>
            )}
          </ResponsiveContainer>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p>Interactive chart showing {title.toLowerCase()}.</p>
      </TooltipContent>
    </UITooltip>
  )
}
