param([Parameter(Mandatory=$true)][string]$InputDeck,
      [Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference='Stop'
$deckPath=(Resolve-Path -LiteralPath $InputDeck).Path
$pdfPath=[IO.Path]::GetFullPath($OutputPdf)
$powerPoint=New-Object -ComObject PowerPoint.Application
$hadOpenDecks=$powerPoint.Presentations.Count -gt 0
$deck=$null
try {
    $deck=$powerPoint.Presentations.Open($deckPath,-1,0,0)
    $deck.SaveAs($pdfPath,32)
    if(-not (Test-Path -LiteralPath $pdfPath)){throw 'PDF export absent'}
    Write-Output ('Exported '+$deck.Slides.Count+' slides to PDF')
} finally {
    if($null -ne $deck){$deck.Close()}
    if(-not $hadOpenDecks -and $powerPoint.Presentations.Count -eq 0){$powerPoint.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
}
