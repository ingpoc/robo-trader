import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Area,
  AreaChart,
} from 'recharts'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Tooltip as UITooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'

interface ChartCardProps {
  title: string
  type: 'line' | 'pie' | 'area'
  data: Array<{ name: string; value: number; [key: string]: any }>
  height?: number
  showLegend?: boolean
  className?: string
  isLoading?: boolean
}

const COLORS = [
  '#b87333', // copper accent
  '#6eb897', // emerald success
  '#b87333', // copper warning
  '#b87566', // rose error
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
]

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white/95 backdrop-blur-sm border border-warmgray-300 rounded-lg shadow-md p-3">
        <p className="text-sm font-medium text-warmgray-900 mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-warmgray-700">
              {entry.name}: <span className="font-semibold">{entry.value}</span>
            </span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export function ChartCard({
  title,
  type,
  data,
  height = 240,
  showLegend = false,
  className
}: ChartCardProps) {
  const isPositive = data.length > 1 && data[data.length - 1]?.value > data[0]?.value

  const chartContent = (
    <div className={`flex flex-col p-6 bg-gradient-to-br from-white/95 to-warmgray-50/70 backdrop-blur-sm border-0 shadow-md hover:shadow-lg rounded-xl transition-all duration-300 ring-1 ring-warmgray-300/50 animate-scale-in hover:animate-hover-lift ${className || ''}`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-copper-100 to-copper-200 rounded-xl shadow-sm">
            <svg className="w-5 h-5 text-copper-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-warmgray-900 font-serif uppercase tracking-wider">
            {title}
          </h3>
        </div>
        {type === 'line' && data.length > 1 && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold shadow-sm ${
            isPositive
              ? 'bg-gradient-to-r from-emerald-100 to-emerald-200 text-emerald-800 border border-emerald-300'
              : 'bg-gradient-to-r from-rose-100 to-rose-200 text-rose-800 border border-rose-300'
          }`}>
            {isPositive ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
              </svg>
            )}
            <span className="tabular-nums">
              {isPositive ? '+' : ''}
              {((data[data.length - 1].value - data[0].value) / data[0].value * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      <div
        className="flex-1"
        style={{ minHeight: `${height}px` }}
        role="img"
        aria-label={`${title} chart`}
      >
        <ResponsiveContainer width="100%" height="100%">
          {type === 'line' ? (
            <LineChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <defs>
                <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#b87333" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#b87333" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="name"
                tick={{ fill: '#9d928a', fontSize: 12 }}
                axisLine={{ stroke: '#e8e3de' }}
                tickLine={{ stroke: '#e8e3de' }}
              />
              <YAxis
                tick={{ fill: '#9d928a', fontSize: 12 }}
                axisLine={{ stroke: '#e8e3de' }}
                tickLine={{ stroke: '#e8e3de' }}
              />
              <Tooltip content={<CustomTooltip />} />
              {showLegend && <Legend />}
              <Line
                type="monotone"
                dataKey="value"
                stroke="#b87333"
                strokeWidth={2.5}
                dot={{ fill: '#b87333', strokeWidth: 2, r: 4 }}
                activeDot={{
                  r: 6,
                  stroke: '#b87333',
                  strokeWidth: 2,
                  fill: '#ffffff',
                  style: { filter: 'drop-shadow(0 2px 4px rgba(184, 115, 51, 0.2))' }
                }}
                fill="url(#lineGradient)"
                fillOpacity={1}
              />
            </LineChart>
          ) : type === 'area' ? (
            <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6eb897" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#6eb897" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="name"
                tick={{ fill: '#9d928a', fontSize: 12 }}
                axisLine={{ stroke: '#e8e3de' }}
                tickLine={{ stroke: '#e8e3de' }}
              />
              <YAxis
                tick={{ fill: '#9d928a', fontSize: 12 }}
                axisLine={{ stroke: '#e8e3de' }}
                tickLine={{ stroke: '#e8e3de' }}
              />
              <Tooltip content={<CustomTooltip />} />
              {showLegend && <Legend />}
              <Area
                type="monotone"
                dataKey="value"
                stroke="#6eb897"
                strokeWidth={2}
                fill="url(#areaGradient)"
                fillOpacity={1}
              />
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
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    style={{ filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))' }}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              {showLegend && <Legend />}
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )

  return (
    <UITooltip>
      <TooltipTrigger asChild>
        {chartContent}
      </TooltipTrigger>
      <TooltipContent>
        <p>Interactive chart showing {title.toLowerCase()}. Hover over data points for detailed information.</p>
      </TooltipContent>
    </UITooltip>
  )
}
