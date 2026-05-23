import apiClient from './client'
import type {
  AzureResource,
  ResourceClassification,
  DiscoveryResult,
  ApprovalRequest,
  TagApplicationResult,
  DashboardStats,
} from '../types'

export const resourcesApi = {
  // Discovery
  discover: async (): Promise<DiscoveryResult> => {
    const response = await apiClient.post('/api/resources/discover')
    return response.data
  },

  // Get all resources
  getResources: async (): Promise<AzureResource[]> => {
    const response = await apiClient.get('/api/resources')
    return response.data
  },

  // Get resource by ID
  getResource: async (resourceId: string): Promise<AzureResource> => {
    const response = await apiClient.get(`/api/resources/${encodeURIComponent(resourceId)}`)
    return response.data
  },

  // Get classifications (using /api/resources with filters)
  getClassifications: async (filters?: {
    status?: string
    minConfidence?: number
    maxConfidence?: number
    level1?: string
    level2?: string
    level3?: string
  }): Promise<ResourceClassification[]> => {
    const params: any = {}
    if (filters?.status) params.status = filters.status
    if (filters?.minConfidence !== undefined) params.min_confidence = filters.minConfidence
    if (filters?.maxConfidence !== undefined) params.max_confidence = filters.maxConfidence
    if (filters?.level1) params.level1 = filters.level1
    if (filters?.level2) params.level2 = filters.level2
    if (filters?.level3) params.level3 = filters.level3
    const response = await apiClient.get('/api/resources', { params })
    return response.data
  },

  // Get classification for specific resource
  getClassification: async (resourceId: string): Promise<ResourceClassification> => {
    const response = await apiClient.get(`/api/resources/${encodeURIComponent(resourceId)}`)
    return response.data
  },

  // Classify resources (using discover endpoint)
  classify: async (resourceIds: string[]): Promise<{ classified: number; errors: string[] }> => {
    const response = await apiClient.post('/api/resources/discover', { resource_ids: resourceIds })
    return response.data
  },

  // Approve/reject classifications
  approve: async (request: ApprovalRequest): Promise<{ updated: number }> => {
    const response = await apiClient.post('/api/resources/approve', request)
    return response.data
  },

  // Apply tags
  applyTags: async (resourceIds: string[]): Promise<TagApplicationResult[]> => {
    const response = await apiClient.post('/api/resources/apply', { resource_ids: resourceIds })
    return response.data
  },

  // Get dashboard stats
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get('/api/statistics')
    return response.data
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; timestamp: string }> => {
    const response = await apiClient.get('/')
    return response.data
  },
}

export default resourcesApi
