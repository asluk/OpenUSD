[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Python,
    [string]$ProposalRepo,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [string]$AecoZip,
    [string]$DatasetRoot,
    [switch]$Deliver,
    [string]$CheckpointId
)
$ErrorActionPreference = 'Stop'
$runDirectory = Join-Path $OutputRoot (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$arguments = @('-X', 'utf8', (Join-Path $PSScriptRoot 'run.py'), '--output', $runDirectory)
if ($ProposalRepo) { $arguments += @('--proposal-repo', $ProposalRepo) }
if ($AecoZip) { $arguments += @('--aeco-zip', $AecoZip) }
if ($DatasetRoot) { $arguments += @('--dataset-root', $DatasetRoot) }
if ($Deliver) { $arguments += '--deliver' }
if ($CheckpointId) { $arguments += @('--checkpoint-id', $CheckpointId) }
& $Python @arguments
$runExitCode = $LASTEXITCODE
Write-Host "Report: $(Join-Path $runDirectory 'REPORT.md')"
Write-Host 'Exit 0 means every conditional workflow completed. Design approval and survey accuracy remain separate.'
exit $runExitCode
