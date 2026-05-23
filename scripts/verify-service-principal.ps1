# Verify Service Principal RBAC permissions
# Checks that all required roles are properly assigned

param(
    [Parameter(Mandatory=$true)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$false)]
    [string]$CosmosAccountName,
    
    [Parameter(Mandatory=$false)]
    [string]$FoundryHubName
)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Service Principal Permission Verification" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Service Principal Client ID: $ClientId`n" -ForegroundColor Cyan

# Get Service Principal details
Write-Host "Retrieving Service Principal details..." -ForegroundColor Cyan
$sp = az ad sp show --id $ClientId --output json 2>$null | ConvertFrom-Json

if ($null -eq $sp) {
    Write-Host "✗ Service Principal not found!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Service Principal found" -ForegroundColor Green
Write-Host "  Display Name: $($sp.displayName)"
Write-Host "  Object ID: $($sp.id)"
Write-Host "  App ID: $($sp.appId)`n"

# Check subscription-level roles
Write-Host "Checking subscription-level roles..." -ForegroundColor Cyan

$allRoles = az role assignment list --assignee $ClientId --output json | ConvertFrom-Json

if ($allRoles.Count -eq 0) {
    Write-Host "✗ No role assignments found!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found $($allRoles.Count) role assignment(s)`n" -ForegroundColor Green

# Group by subscription
$subscriptionRoles = $allRoles | Where-Object { $_.scope -like "/subscriptions/*" -and $_.scope -notlike "*/resourceGroups/*" }

if ($subscriptionRoles.Count -gt 0) {
    Write-Host "Subscription-level roles:" -ForegroundColor Yellow
    foreach ($role in $subscriptionRoles) {
        $subId = $role.scope -replace "/subscriptions/", ""
        Write-Host "  Subscription: $subId" -ForegroundColor White
        Write-Host "    Role: $($role.roleDefinitionName)" -ForegroundColor $(if ($role.roleDefinitionName -in @("Reader", "Tag Contributor")) { "Green" } else { "Yellow" })
    }
    Write-Host ""
} else {
    Write-Host "⚠ No subscription-level roles found`n" -ForegroundColor Yellow
}

# Check required roles
Write-Host "Verifying required permissions:" -ForegroundColor Cyan

$hasReader = $subscriptionRoles | Where-Object { $_.roleDefinitionName -eq "Reader" }
$hasTagContributor = $subscriptionRoles | Where-Object { $_.roleDefinitionName -eq "Tag Contributor" }

Write-Host "  Reader role: " -NoNewline
if ($hasReader) {
    Write-Host "✓ Assigned" -ForegroundColor Green
} else {
    Write-Host "✗ Missing" -ForegroundColor Red
}

Write-Host "  Tag Contributor role: " -NoNewline
if ($hasTagContributor) {
    Write-Host "✓ Assigned" -ForegroundColor Green
} else {
    Write-Host "✗ Missing" -ForegroundColor Red
}

# Check resource-specific roles
if ($ResourceGroup -and $CosmosAccountName) {
    Write-Host "`nChecking Cosmos DB permissions..." -ForegroundColor Cyan
    
    try {
        $cosmosRoles = az cosmosdb sql role assignment list `
          --account-name $CosmosAccountName `
          --resource-group $ResourceGroup `
          --output json | ConvertFrom-Json
        
        $spObjectId = $sp.id
        $hasCosmosAccess = $cosmosRoles | Where-Object { $_.principalId -eq $spObjectId }
        
        Write-Host "  Cosmos DB Data Contributor: " -NoNewline
        if ($hasCosmosAccess) {
            Write-Host "✓ Assigned" -ForegroundColor Green
        } else {
            Write-Host "✗ Missing" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ⚠ Could not verify Cosmos DB permissions" -ForegroundColor Yellow
    }
}

if ($ResourceGroup -and $FoundryHubName) {
    Write-Host "`nChecking Azure AI Foundry permissions..." -ForegroundColor Cyan
    
    try {
        $foundryScope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.MachineLearningServices/workspaces/$FoundryHubName"
        $foundryRoles = $allRoles | Where-Object { $_.scope -eq $foundryScope }
        
        $hasFoundryAccess = $foundryRoles | Where-Object { $_.roleDefinitionName -eq "Azure AI Developer" }
        
        Write-Host "  Azure AI Developer: " -NoNewline
        if ($hasFoundryAccess) {
            Write-Host "✓ Assigned" -ForegroundColor Green
        } else {
            Write-Host "✗ Missing" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ⚠ Could not verify Foundry permissions" -ForegroundColor Yellow
    }
}

# Display all role assignments
Write-Host "`nAll role assignments:" -ForegroundColor Cyan
Write-Host ""
az role assignment list --assignee $ClientId --output table

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Summary" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

$requiredPermissions = @(
    @{Name="Reader"; HasPermission=$hasReader}
    @{Name="Tag Contributor"; HasPermission=$hasTagContributor}
)

$missingPermissions = $requiredPermissions | Where-Object { -not $_.HasPermission }

if ($missingPermissions.Count -eq 0) {
    Write-Host "✅ All required subscription permissions are configured!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Missing permissions:" -ForegroundColor Yellow
    foreach ($perm in $missingPermissions) {
        Write-Host "  - $($perm.Name)" -ForegroundColor Red
    }
    Write-Host "`nRun setup-service-principal.ps1 to configure missing permissions." -ForegroundColor Yellow
}

Write-Host ""
