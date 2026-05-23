export interface AzureResource {
  id: string
  name: string
  type: string
  location: string
  resourceGroup: string
  subscriptionId: string
  tags: Record<string, string>
  properties: Record<string, any>
}

export interface ResourceClassification {
  id: string
  partitionKey: string
  resourceId: string
  resourceName: string
  resourceType: string
  resourceGroup: string
  subscriptionId: string
  location: string
  level1: 'Infra' | 'Data' | 'Apps'
  level2: string
  level3: string
  confidence: number
  reasoning: string
  proposedTags: Record<string, string>
  existingTags: Record<string, string>
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  createdAt: string
  updatedAt: string
  appliedAt?: string
  errorMessage?: string
}

export interface DiscoveryResult {
  totalResources: number
  classifiedResources: number
  pendingApproval: number
  errors: string[]
}

export interface ApprovalRequest {
  resourceIds: string[]
  approved: boolean
  comment?: string
}

export interface TagApplicationResult {
  resourceId: string
  success: boolean
  error?: string
  tagsApplied: Record<string, string>
}

export interface DashboardStats {
  total?: number
  totalResources: number
  classified: number
  pending: number
  approved: number
  applied: number
  failed?: number
  byLevel1: Record<string, number>
  byLevel2: Record<string, number>
  recentActivity: Array<{
    timestamp: string
    action: string
    resourceCount: number
  }>
}
