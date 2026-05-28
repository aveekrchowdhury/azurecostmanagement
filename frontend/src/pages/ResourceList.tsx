import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Search, Loader2, Tag as TagIcon, CheckCircle } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import resourcesApi from '../api/resources'
import type { ResourceClassification } from '../types'

export default function ResourceList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedResources, setSelectedResources] = useState<string[]>([])
  const [searchParams] = useSearchParams()
  const level1Filter = searchParams.get('level1') || ''
  const queryClient = useQueryClient()

  const { data: resources, isLoading: resourcesLoading } = useQuery<ResourceClassification[]>({
    queryKey: ['resources'],
    queryFn: resourcesApi.getResources,
  })

  const { data: classifications, isLoading: classificationsLoading } = useQuery<ResourceClassification[]>({
    queryKey: ['classifications', level1Filter],
    queryFn: () => resourcesApi.getClassifications({
      level1: level1Filter || undefined,
    }),
  })

  const discoverMutation = useMutation({
    mutationFn: resourcesApi.discover,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resources'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const classifyMutation = useMutation({
    mutationFn: resourcesApi.classify,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['classifications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSelectedResources([])
    },
  })

  const filteredResources = resources
    ?.filter((resource) => {
      const lookupResourceId = resource.resourceId ?? resource.id
      if (!level1Filter) return true
      return classifications?.some((c) => c.resourceId === lookupResourceId || c.id === lookupResourceId)
    })
    .filter((resource) =>
      resource.resourceName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      resource.resourceType.toLowerCase().includes(searchTerm.toLowerCase()) ||
      resource.resourceGroup.toLowerCase().includes(searchTerm.toLowerCase())
    )

  const getClassificationForResource = (resourceId: string): ResourceClassification | undefined => {
    return classifications?.find((c) => c.resourceId === resourceId || c.id === resourceId)
  }

  const handleSelectAll = () => {
    if (selectedResources.length === filteredResources?.length) {
      setSelectedResources([])
    } else {
      setSelectedResources(filteredResources?.map((r) => r.id) || [])
    }
  }

  const handleClassifySelected = () => {
    if (selectedResources.length > 0) {
      classifyMutation.mutate(selectedResources)
    }
  }

  if (resourcesLoading || classificationsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Resources</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Manage and classify your Azure resources
          </p>
          {level1Filter && (
            <p className="mt-1 text-sm text-primary-700 dark:text-primary-400">
              Showing resources for Workload Level 1: <span className="font-semibold">{level1Filter}</span>{' '}
              <Link to="/resources" className="underline">
                Clear filter
              </Link>
            </p>
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => discoverMutation.mutate()}
            disabled={discoverMutation.isPending}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${discoverMutation.isPending ? 'animate-spin' : ''}`} />
            {discoverMutation.isPending ? 'Discovering...' : 'Discover Resources'}
          </button>
          {selectedResources.length > 0 && (
            <button
              onClick={handleClassifySelected}
              disabled={classifyMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              <TagIcon className="h-4 w-4" />
              Classify Selected ({selectedResources.length})
            </button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search resources..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Resources Table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedResources.length === filteredResources?.length && filteredResources.length > 0}
                    onChange={handleSelectAll}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Resource Group
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Location
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredResources?.map((resource) => {
                const lookupResourceId = resource.resourceId ?? resource.id
                const classification = getClassificationForResource(lookupResourceId)
                return (
                  <tr key={resource.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedResources.includes(lookupResourceId)}
                        onChange={() => {
                          setSelectedResources((prev) =>
                            prev.includes(lookupResourceId)
                              ? prev.filter((id) => id !== lookupResourceId)
                              : [...prev, lookupResourceId]
                          )
                        }}
                        className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                      {resource.resourceName}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {resource.resourceType.split('/').pop()}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {resource.resourceGroup}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {resource.location}
                    </td>
                    <td className="px-6 py-4">
                      {classification ? (
                        <div className="flex items-center gap-2">
                          {classification.status === 'applied' && (
                            <span className="badge-green flex items-center gap-1">
                              <CheckCircle className="h-3 w-3" />
                              Applied
                            </span>
                          )}
                          {classification.status === 'approved' && (
                            <span className="badge-blue">Approved</span>
                          )}
                          {classification.status === 'pending' && (
                            <span className="badge-yellow">Pending</span>
                          )}
                          {classification.status === 'rejected' && (
                            <span className="badge-red">Rejected</span>
                          )}
                        </div>
                      ) : (
                        <span className="badge-gray">Not Classified</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
