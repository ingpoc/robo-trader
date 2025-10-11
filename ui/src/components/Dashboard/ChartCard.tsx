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
} from 'recharts'

interface ChartCardProps {
  title: string
  type: 'line' | 'pie'
  data: Array<{ name: string; value: number }>
  height?: number
}

const COLORS = ['#171717', '#404040', '#737373', '#a3a3a3', '#d4d4d4']

export function ChartCard({ title, type, data, height = 240 }: ChartCardProps) {
  return (
    <div className="flex flex-col p-4 bg-white border border-gray-200 card-shadow">
      <div className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-2">
        {title}
      </div>
      <div className="flex-1" style={{ minHeight: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === 'line' ? (
            <LineChart data={data}>
              <defs>
                <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#171717" stopOpacity={0.1} />
                  <stop offset="100%" stopColor="#171717" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="name"
                tick={{ fill: '#737373', fontSize: 11 }}
                axisLine={{ stroke: '#e5e5e5' }}
              />
              <YAxis
                tick={{ fill: '#737373', fontSize: 11 }}
                axisLine={{ stroke: '#e5e5e5' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #d4d4d4',
                  borderRadius: '2px',
                  fontSize: '13px',
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#171717"
                strokeWidth={1.5}
                dot={false}
                fill="url(#lineGradient)"
                fillOpacity={1}
                activeDot={{
                  r: 4,
                  stroke: '#171717',
                  strokeWidth: 2,
                  fill: '#ffffff',
                }}
              />
            </LineChart>
          ) : (
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                label={(entry) => `${entry.value.toFixed(0)}%`}
                labelStyle={{ fontSize: '11px', fill: '#525252' }}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #d4d4d4',
                  borderRadius: '2px',
                  fontSize: '13px',
                }}
              />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
