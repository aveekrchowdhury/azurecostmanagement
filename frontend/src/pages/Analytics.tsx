import { useQuery } from '@tanstack/react-query'
import { Loader2, TrendingUp, PieChart as PieChartIcon } from 'lucide-react'
import resourcesApi from '../api/resources'

export default function Analytics() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: resourcesApi.getStats,
  })

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
  const failedCount = stats?.failed ?? 0

  // Approved resources may transition to applied/failed, so include them in approval lineage.
  const approvedLineageCount = approvedCount + appliedCount + failedCount
  const reviewedCount = Math.max(classifiedCount - pendingCount, 0)

  const classificationRate = totalResources > 0
    ? ((classifiedCount / totalResources) * 100).toFixed(1)
    : '0'
  const approvalRate = reviewedCount > 0
    ? ((approvedLineageCount / reviewedCount) * 100).toFixed(1)
    : '0'
  const applicationRate = approvedLineageCount > 0
    ? ((appliedCount / approvedLineageCount) * 100).toFixed(1)
    : '0'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analytics</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Insights and metrics for your resource tagging operations
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0 rounded-md bg-blue-100 dark:bg-blue-900/20 p-3">
              <TrendingUp className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dt className="truncate text-sm font-medium text-gray-500 dark:text-gray-400">
                Classification Rate
              </dt>
              <dd className="text-3xl font-semibold text-gray-900 dark:text-white">
                {classificationRate}%
              </dd>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0 rounded-md bg-green-100 dark:bg-green-900/20 p-3">
              <PieChartIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dt className="truncate text-sm font-medium text-gray-500 dark:text-gray-400">
                Approval Rate
              </dt>
              <dd className="text-3xl font-semibold text-gray-900 dark:text-white">
                {approvalRate}%
              </dd>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0 rounded-md bg-purple-100 dark:bg-purple-900/20 p-3">
              <TrendingUp className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dt className="truncate text-sm font-medium text-gray-500 dark:text-gray-400">
                Application Rate
              </dt>
              <dd className="text-3xl font-semibold text-gray-900 dark:text-white">
                {applicationRate}%
              </dd>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Breakdown */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Level 1 Breakdown */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Workload Level 1 Breakdown
          </h3>
          <div className="space-y-4">
            {stats?.byLevel1 && Object.entries(stats.byLevel1).map(([level, count]) => {
              const percentage = totalResources > 0 ? (count / totalResources * 100).toFixed(1) : '0'
              return (
                <div key={level} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {level}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {count} ({percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-primary-500 to-primary-600 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Level 2 Top Categories */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Top 10 Level 2 Categories
          </h3>
          <div className="space-y-4">
            {stats?.byLevel2 && Object.entries(stats.byLevel2)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 10)
              .map(([level, count]) => {
                const percentage = totalResources > 0 ? (count / totalResources * 100).toFixed(1) : '0'
                return (
                  <div key={level} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {level}
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {count} ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-green-500 to-green-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
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
