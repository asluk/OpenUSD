$ErrorActionPreference='Stop'
$taskOutput='C:\Users\aluk\Documents\Codex\2026-09-21\have\outputs\geospatial-fresh-build-20261014'
$taskPowerPoint=$null
$taskPresentation=$null
try {
 $taskPowerPoint=New-Object -ComObject PowerPoint.Application
 $taskPresentation=$taskPowerPoint.Presentations.Open((Join-Path $taskOutput 'Geospatial-proposal-quality-2026-10-14-v3.pptx'),-1,0,0)
 $taskPresentation.SaveAs((Join-Path $taskOutput 'Geospatial-proposal-quality-2026-10-14.pdf'),32)
 $taskPresentation.Export((Join-Path $taskOutput 'powerpoint-slides'),'PNG',1920,1080)
 Write-Output ('Exported final PPTX: '+$taskPresentation.Slides.Count+' slides to PDF and PNG.')
} finally {
 if ($taskPresentation) { $taskPresentation.Close(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskPresentation) }
 if ($taskPowerPoint) { $taskPowerPoint.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskPowerPoint) }
}
