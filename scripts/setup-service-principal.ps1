# Setup Service Principal for Azure Resource Tagger
# This script creates a service principal and assigns all necessary RBAC roles

param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$CosmosAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$FoundryHubName,
    
    [Parameter(Mandatory=$false)]
    [string]$ServicePrincipalName = "sp-resource-tagger"
)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Azure Resource Tagger - Service Principal Setup" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Set the subscription context
Write-Host "Setting subscription context: $SubscriptionId" -ForegroundColor Cyan
az account set --subscription $SubscriptionId

# 1. Create Service Principal
Write-Host "`n[1/5] Creating Service Principal: $ServicePrincipalName" -ForegroundColor Cyan
$sp = az ad sp create-for-rbac --name $ServicePrincipalName --output json | ConvertFrom-Json

if ($null -eq $sp) {
    Write-Host "Failed to create Service Principal!" -ForegroundColor Red
    exit 1
}

$clientId = $sp.appId
$clientSecret = $sp.password
$tenantId = $sp.tenant

Write-Host "✓ Service Principal Created" -ForegroundColor Green
Write-Host "  Client ID: $clientId" -ForegroundColor White
Write-Host "  Tenant ID: $tenantId" -ForegroundColor White
Write-Host "  Client Secret: $clientSecret" -ForegroundColor Yellow

# Wait for service principal to propagate
Write-Host "`nWaiting for Service Principal to propagate (15 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# Get Service Principal Object ID for Cosmos DB RBAC
$spObjectId = az ad sp show --id $clientId --query id -o tsv

# 2. Assign Reader role on subscription
Write-Host "`n[2/5] Assigning Reader role on subscription..." -ForegroundColor Cyan
try {
    az role assignment create `
      --role "Reader" `
      --assignee $clientId `
      --scope "/subscriptions/$SubscriptionId" `
      --output none
    Write-Host "✓ Reader role assigned" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Reader role assignment may have failed (may already exist)" -ForegroundColor Yellow
}

# 3. Assign Tag Contributor role on subscription
Write-Host "`n[3/5] Assigning Tag Contributor role on subscription..." -ForegroundColor Cyan
try {
    az role assignment create `
      --role "Tag Contributor" `
      --assignee $clientId `
      --scope "/subscriptions/$SubscriptionId" `
      --output none
    Write-Host "✓ Tag Contributor role assigned" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Tag Contributor role assignment may have failed (may already exist)" -ForegroundColor Yellow
}

# 4. Assign Cosmos DB Data Contributor role
Write-Host "`n[4/5] Assigning Cosmos DB Data Contributor role..." -ForegroundColor Cyan
try {
    az cosmosdb sql role assignment create `
      --account-name $CosmosAccountName `
      --resource-group $ResourceGroup `
      --role-definition-name "Cosmos DB Built-in Data Contributor" `
      --principal-id $spObjectId `
      --scope "/" `
      --output none
    Write-Host "✓ Cosmos DB Data Contributor role assigned" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Cosmos DB role assignment may have failed (may already exist)" -ForegroundColor Yellow
}

# 5. Assign Azure AI Developer role on Foundry Hub
Write-Host "`n[5/5] Assigning Azure AI Developer role on Foundry Hub..." -ForegroundColor Cyan
$foundryScope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.MachineLearningServices/workspaces/$FoundryHubName"
try {
    az role assignment create `
      --role "Azure AI Developer" `
      --assignee $clientId `
      --scope $foundryScope `
      --output none
    Write-Host "✓ Azure AI Developer role assigned" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Azure AI Developer role assignment may have failed (may already exist)" -ForegroundColor Yellow
}

# Display summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Service Principal Configuration:" -ForegroundColor Cyan
Write-Host "  Name: $ServicePrincipalName"
Write-Host "  Client ID: $clientId"
Write-Host "  Tenant ID: $tenantId"
Write-Host "  Object ID: $spObjectId"
Write-Host ""

Write-Host "Assigned Roles:" -ForegroundColor Cyan
Write-Host "  ✓ Reader (Subscription: $SubscriptionId)"
Write-Host "  ✓ Tag Contributor (Subscription: $SubscriptionId)"
Write-Host "  ✓ Cosmos DB Data Contributor (Account: $CosmosAccountName)"
Write-Host "  ✓ Azure AI Developer (Foundry Hub: $FoundryHubName)"
Write-Host ""

Write-Host "Add these values to your .env file:" -ForegroundColor Yellow
Write-Host ""
Write-Host "AZURE_CLIENT_ID=$clientId" -ForegroundColor White
Write-Host "AZURE_CLIENT_SECRET=$clientSecret" -ForegroundColor Red
Write-Host "AZURE_TENANT_ID=$tenantId" -ForegroundColor White
Write-Host "AZURE_SUBSCRIPTION_ID=$SubscriptionId" -ForegroundColor White
Write-Host "AUTH_MODE=service_principal" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANT: Save the Client Secret securely!" -ForegroundColor Red
Write-Host "   It will not be shown again." -ForegroundColor Red
Write-Host ""

# Verify role assignments
Write-Host "Verifying role assignments..." -ForegroundColor Cyan
Write-Host ""
az role assignment list --assignee $clientId --output table

Write-Host "`n✅ Service Principal is ready to use!" -ForegroundColor Green
Write-Host ""
