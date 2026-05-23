import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, X, Loader2, AlertCircle, Tag as TagIcon, Filter, XCircle } from 'lucide-react'
import resourcesApi from '../api/resources'
import type { ResourceClassification } from '../types'

export default function Validation() {
  const [selectedClassifications, setSelectedClassifications] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<'pending' | 'approved' | 'applied'>('pending')
  const [filters, setFilters] = useState({
    minConfidence: '',
    level1: '',
    level2: '',
    level3: '',
  })
  const [showFilters, setShowFilters] = useState(false)
  const queryClient = useQueryClient()

  const { data: classifications, isLoading } = useQuery({
    queryKey: ['classifications', activeTab, filters],
    queryFn: () => resourcesApi.getClassifications({
      status: activeTab,
      minConfidence: filters.minConfidence ? parseFloat(filters.minConfidence) : undefined,
      level1: filters.level1 || undefined,
      level2: filters.level2 || undefined,
      level3: filters.level3 || undefined,
    }),
  })

  const approveMutation = useMutation({
    mutationFn: resourcesApi.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['classifications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSelectedClassifications([])
    },
  })

  const applyTagsMutation = useMutation({
    mutationFn: resourcesApi.applyTags,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['classifications'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  // Get unique values for filters
  const uniqueValues = useMemo(() => {
    if (!classifications) return { level1: [], level2: [], level3: [] }
    
    const level1Set = new Set<string>()
    const level2Set = new Set<string>()
    const level3Set = new Set<string>()
    
    classifications.forEach(c => {
      level1Set.add(c.level1)
      level2Set.add(c.level2)
      level3Set.add(c.level3)
    })
    
    return {
      level1: Array.from(level1Set).sort(),
      level2: Array.from(level2Set).sort(),
      level3: Array.from(level3Set).sort(),
    }
  }, [classifications])

  const handleSelectAll = () => {
    if (classifications) {
      setSelectedClassifications(classifications.map(c => c.resourceId))
    }
  }

  const handleDeselectAll = () => {
    setSelectedClassifications([])
  }

  const clearFilters = () => {
    setFilters({
      minConfidence: '',
      level1: '',
      level2: '',
      level3: '',
    })
  }

  const hasActiveFilters = filters.minConfidence || filters.level1 || filters.level2 || filters.level3

  const handleApprove = () => {
    if (selectedClassifications.length > 0) {
      approveMutation.mutate({
        resourceIds: selectedClassifications,
        approved: true,
      })
    }
  }

  const handleReject = () => {
    if (selectedClassifications.length > 0) {
      approveMutation.mutate({
        resourceIds: selectedClassifications,
        approved: false,
      })
    }
  }

  const handleApplyTags = () => {
    if (selectedClassifications.length > 0) {
      applyTagsMutation.mutate(selectedClassifications)
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400'
    if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) return 'badge-green'
    if (confidence >= 0.6) return 'badge-yellow'
    return 'badge-red'
  }

  if (isLoading) {
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
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Classification Validation
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Review and approve resource classifications before applying tags
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary flex items-center gap-2"
        >
          <Filter className="h-4 w-4" />
          {showFilters ? 'Hide Filters' : 'Show Filters'}
          {hasActiveFilters && (
            <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200">
              Active
            </span>
          )}
        </button>
      </div>

      {/* Status Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => {
              setActiveTab('pending')
              setSelectedClassifications([])
            }}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'pending'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Pending
          </button>
          <button
            onClick={() => {
              setActiveTab('approved')
              setSelectedClassifications([])
            }}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'approved'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Approved
          </button>
          <button
            onClick={() => {
              setActiveTab('applied')
              setSelectedClassifications([])
            }}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'applied'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Applied
          </button>
        </nav>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Filters</h3>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                <XCircle className="h-4 w-4" />
                Clear All
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Minimum Confidence
              </label>
              <select
                value={filters.minConfidence}
                onChange={(e) => setFilters({ ...filters, minConfidence: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              >
                <option value="">All</option>
                <option value="0.8">High (≥80%)</option>
                <option value="0.6">Medium (≥60%)</option>
                <option value="0.4">Low (≥40%)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Level 1
              </label>
              <select
                value={filters.level1}
                onChange={(e) => setFilters({ ...filters, level1: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              >
                <option value="">All</option>
                {uniqueValues.level1.map(value => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Level 2
              </label>
              <select
                value={filters.level2}
                onChange={(e) => setFilters({ ...filters, level2: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              >
                <option value="">All</option>
                {uniqueValues.level2.map(value => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Level 3
              </label>
              <select
                value={filters.level3}
                onChange={(e) => setFilters({ ...filters, level3: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              >
                <option value="">All</option>
                {uniqueValues.level3.map(value => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Actions Bar */}
      {classifications && classifications.length > 0 && (
        <div className="card bg-gray-50 dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedClassifications.length === classifications.length && classifications.length > 0}
                  onChange={(e) => {
                    if (e.target.checked) {
                      handleSelectAll()
                    } else {
                      handleDeselectAll()
                    }
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {selectedClassifications.length > 0 
                    ? `${selectedClassifications.length} of ${classifications.length} selected`
                    : `Select all ${classifications.length} items`
                  }
                </span>
              </div>
              {selectedClassifications.length > 0 && (
                <button
                  onClick={handleDeselectAll}
                  className="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  Clear selection
                </button>
              )}
            </div>
            {selectedClassifications.length > 0 && (
              <div className="flex gap-3">
                {/* Show Approve/Reject only for pending tab */}
                {activeTab === 'pending' && (
                  <>
                    <button
                      onClick={handleReject}
                      disabled={approveMutation.isPending}
                      className="btn-danger flex items-center gap-2"
                    >
                      <X className="h-4 w-4" />
                      Reject ({selectedClassifications.length})
                    </button>
                    <button
                      onClick={handleApprove}
                      disabled={approveMutation.isPending}
                      className="btn-success flex items-center gap-2"
                    >
                      <Check className="h-4 w-4" />
                      Approve ({selectedClassifications.length})
                    </button>
                  </>
                )}
                {/* Show Apply Tags only for approved tab */}
                {activeTab === 'approved' && (
                  <button
                    onClick={handleApplyTags}
                    disabled={applyTagsMutation.isPending}
                    className="btn-primary flex items-center gap-2"
                  >
                    <TagIcon className="h-4 w-4" />
                    Apply Tags ({selectedClassifications.length})
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {classifications && classifications.length === 0 ? (
        <div className="card text-center py-12">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
            No {activeTab} classifications
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {activeTab === 'pending' && 'All resources have been reviewed.'}
            {activeTab === 'approved' && 'No resources are waiting to have tags applied.'}
            {activeTab === 'applied' && 'No tags have been applied yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {classifications?.map((classification) => (
            <div key={classification.resourceId} className="card">
              <div className="flex items-start gap-4">
                <input
                  type="checkbox"
                  checked={selectedClassifications.includes(classification.resourceId)}
                  onChange={() => {
                    setSelectedClassifications((prev) =>
                      prev.includes(classification.resourceId)
                        ? prev.filter((id) => id !== classification.resourceId)
                        : [...prev, classification.resourceId]
                    )
                  }}
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {classification.resourceId.split('/').pop()}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {classification.resourceId}
                      </p>
                    </div>
                    <span className={`${getConfidenceBadge(classification.confidence)}`}>
                      {(classification.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        Level 1
                      </label>
                      <p className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                        {classification.level1}
                      </p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        Level 2
                      </label>
                      <p className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                        {classification.level2}
                      </p>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                        Level 3
                      </label>
                      <p className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                        {classification.level3}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                      Reasoning
                    </label>
                    <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                      {classification.reasoning}
                    </p>
                  </div>

                  <div className="mt-4">
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-2 block">
                      Proposed Tags
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(classification.proposedTags).map(([key, value]) => (
                        <span
                          key={key}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
                        >
                          {key}: {value}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                    Classified at: {new Date(classification.createdAt).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
