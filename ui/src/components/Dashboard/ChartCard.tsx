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

export function ChartCard({ title, type, data, height = 200 }: ChartCardProps) {
  return (
    <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      <div style={{ height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === 'line' ? (
            <LineChart data={data}>
              <XAxis
                dataKey="name"
                tick={{ fill: '#737373', fontSize: 12 }}
                axisLine={{ stroke: '#e5e5e5' }}
              />
              <YAxis
                tick={{ fill: '#737373', fontSize: 12 }}
                axisLine={{ stroke: '#e5e5e5' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e5e5',
                  borderRadius: '4px',
                  fontSize: '14px',
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#171717"
                strokeWidth={2}
                dot={false}
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
                outerRadius={80}
                label={(entry) => `${entry.name}: ${entry.value}%`}
                labelStyle={{ fontSize: '12px', fill: '#737373' }}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e5e5',
                  borderRadius: '4px',
                  fontSize: '14px',
                }}
              />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
