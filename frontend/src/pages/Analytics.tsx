import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import resourcesApi from '../api/resources'

const LEVEL_1_COLORS = ['#2563eb', '#16a34a', '#9333ea', '#ea580c', '#0891b2', '#be123c']
const LEVEL_2_COLORS = [
  '#0ea5e9', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444',
  '#14b8a6', '#84cc16', '#f97316', '#6366f1', '#ec4899'
]

type Slice = {
  label: string
  count: number
  percent: number
  color: string
}

function buildSlices(data: Record<string, number>, palette: string[], maxItems?: number): Slice[] {
  const entries = Object.entries(data || {})
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])

  const slicedEntries = maxItems ? entries.slice(0, maxItems) : entries
  const total = slicedEntries.reduce((sum, [, count]) => sum + count, 0)

  if (total === 0) return []

  return slicedEntries.map(([label, count], idx) => ({
    label,
    count,
    percent: (count / total) * 100,
    color: palette[idx % palette.length],
  }))
}

function pieGradient(slices: Slice[]): string {
  if (slices.length === 0) return 'conic-gradient(#e5e7eb 0deg 360deg)'

  let running = 0
  const segments = slices.map((slice) => {
    const start = running
    const end = running + (slice.percent * 3.6)
    running = end
    return `${slice.color} ${start}deg ${end}deg`
  })

  return `conic-gradient(${segments.join(', ')})`
}

export default function Analytics() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: resourcesApi.getStats,
  })

  const legacyStats = stats as (typeof stats & {
    by_level_1?: Record<string, number>
    by_level_2?: Record<string, number>
  }) | undefined

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  // Normalize stats to support both legacy and current backend payload shapes.
  const totalResources = stats?.totalResources ?? stats?.total ?? 0
  const classifiedCount = stats?.classified ?? stats?.total ?? 0
  const pendingCount = stats?.pending ?? 0
  const approvedCount = stats?.approved ?? 0
  const appliedCount = stats?.applied ?? 0
  const byLevel1 = stats?.byLevel1 ?? legacyStats?.by_level_1 ?? {}
  const byLevel2 = stats?.byLevel2 ?? legacyStats?.by_level_2 ?? {}

  const level1Slices = buildSlices(byLevel1, LEVEL_1_COLORS)
  const level2Slices = buildSlices(byLevel2, LEVEL_2_COLORS, 10)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analytics</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Insights and metrics for your resource tagging operations
        </p>
      </div>

      {/* Level 1 Pie */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Workload Level 1 Classification
        </h3>
          {level1Slices.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No Level 1 data available.</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px,1fr] items-center">
              <div className="mx-auto h-52 w-52 rounded-full relative" style={{ background: pieGradient(level1Slices) }}>
                <div className="absolute inset-10 rounded-full bg-white dark:bg-gray-900 flex items-center justify-center border border-gray-200 dark:border-gray-700">
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">L1</span>
                </div>
              </div>
              <div className="space-y-2">
                {level1Slices.map((slice) => (
                  <div key={slice.label} className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
                      <Link
                        to={`/resources?level1=${encodeURIComponent(slice.label)}`}
                        className="text-primary-700 dark:text-primary-400 hover:underline truncate"
                        title={`Show ${slice.label} resources`}
                      >
                        {slice.label}
                      </Link>
                    </div>
                    <span className="text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {slice.count} ({slice.percent.toFixed(1)}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
      </div>

      {/* Level 2 Pie */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Top 10 Level 2 Categories
          </h3>
          {level2Slices.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No Level 2 data available.</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px,1fr] items-center">
              <div className="mx-auto h-52 w-52 rounded-full relative" style={{ background: pieGradient(level2Slices) }}>
                <div className="absolute inset-10 rounded-full bg-white dark:bg-gray-900 flex items-center justify-center border border-gray-200 dark:border-gray-700">
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">L2 Top 10</span>
                </div>
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {level2Slices.map((slice) => (
                  <div key={slice.label} className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
                      <span className="text-gray-700 dark:text-gray-300 truncate">{slice.label}</span>
                    </div>
                    <span className="text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {slice.count} ({slice.percent.toFixed(1)}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      {/* Status Pipeline */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-6">
          Resource Status Pipeline
        </h3>
        <div className="flex items-center justify-between">
          {[
            { label: 'Total', count: totalResources, color: 'bg-gray-500' },
            { label: 'Classified', count: classifiedCount, color: 'bg-blue-500' },
            { label: 'Pending', count: pendingCount, color: 'bg-yellow-500' },
            { label: 'Approved', count: approvedCount, color: 'bg-green-500' },
            { label: 'Applied', count: appliedCount, color: 'bg-purple-500' },
          ].map((stage, idx, arr) => (
            <div key={stage.label} className="flex items-center">
              <div className="text-center">
                <div className={`mx-auto h-16 w-16 rounded-full ${stage.color} flex items-center justify-center`}>
                  <span className="text-2xl font-bold text-white">{stage.count}</span>
                </div>
                <p className="mt-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  {stage.label}
                </p>
              </div>
              {idx < arr.length - 1 && (
                <div className="mx-4 h-0.5 w-12 bg-gray-300 dark:bg-gray-600" />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
