param(
  [Parameter(Mandatory=$true)][string]$InputPptx,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [string]$InspectionJson,
  [int]$Width = 1920,
  [int]$Height = 1080
)

$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $InputPptx).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$outputPath = (Resolve-Path -LiteralPath $OutputDirectory).Path

$powerPoint = New-Object -ComObject PowerPoint.Application
$powerPoint.Visible = -1
$presentation = $null
$inspectionSlides = New-Object System.Collections.Generic.List[object]
$inspectionIssues = New-Object System.Collections.Generic.List[object]
try {
  $presentation = $powerPoint.Presentations.Open($inputPath, $true, $true, $false)
  for ($index = 1; $index -le $presentation.Slides.Count; $index++) {
    $file = Join-Path $outputPath ('slide-{0:D3}.png' -f $index)
    $presentation.Slides.Item($index).Export($file, 'PNG', $Width, $Height)
    $textShapes = New-Object System.Collections.Generic.List[object]
    foreach ($shape in $presentation.Slides.Item($index).Shapes) {
      try {
        if ($shape.HasTextFrame -ne -1 -or $shape.TextFrame2.HasText -ne -1) { continue }
        $text = [string]$shape.TextFrame2.TextRange.Text
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        $record = [pscustomobject]@{
          name = [string]$shape.Name
          text = $text.Trim()
          left = [double]$shape.Left
          top = [double]$shape.Top
          width = [double]$shape.Width
          height = [double]$shape.Height
          boundLeft = [double]$shape.TextFrame2.TextRange.BoundLeft
          boundTop = [double]$shape.TextFrame2.TextRange.BoundTop
          boundWidth = [double]$shape.TextFrame2.TextRange.BoundWidth
          boundHeight = [double]$shape.TextFrame2.TextRange.BoundHeight
        }
        $textShapes.Add($record)
        $rightOverflow = ($record.boundLeft + $record.boundWidth) - ($record.left + $record.width)
        $bottomOverflow = ($record.boundTop + $record.boundHeight) - ($record.top + $record.height)
        if ($rightOverflow -gt 8 -or $bottomOverflow -gt [Math]::Max(8, $record.height * 0.8)) {
          $inspectionIssues.Add([pscustomobject]@{ code = 'POWERPOINT_TEXT_OVERFLOW'; slide = $index; shape = $record.name; text = $record.text.Substring(0, [Math]::Min(120, $record.text.Length)); bounds = @($record.width, $record.height); rendered = @($record.boundWidth, $record.boundHeight) })
        }
      } catch {}
    }
    for ($leftIndex = 0; $leftIndex -lt $textShapes.Count; $leftIndex++) {
      for ($rightIndex = $leftIndex + 1; $rightIndex -lt $textShapes.Count; $rightIndex++) {
        $a = $textShapes[$leftIndex]
        $b = $textShapes[$rightIndex]
        $intersectionWidth = [Math]::Max(0, [Math]::Min($a.boundLeft + $a.boundWidth, $b.boundLeft + $b.boundWidth) - [Math]::Max($a.boundLeft, $b.boundLeft))
        $intersectionHeight = [Math]::Max(0, [Math]::Min($a.boundTop + $a.boundHeight, $b.boundTop + $b.boundHeight) - [Math]::Max($a.boundTop, $b.boundTop))
        $intersection = $intersectionWidth * $intersectionHeight
        $smallerArea = [Math]::Min($a.boundWidth * $a.boundHeight, $b.boundWidth * $b.boundHeight)
        if ($intersection -gt 120 -and $smallerArea -gt 0 -and ($intersection / $smallerArea) -gt 0.65) {
          $inspectionIssues.Add([pscustomobject]@{ code = 'OVERLAPPING_TEXT_BOXES'; slide = $index; shapes = @($a.name, $b.name); overlapRatio = [Math]::Round($intersection / $smallerArea, 4); text = @($a.text.Substring(0, [Math]::Min(80, $a.text.Length)), $b.text.Substring(0, [Math]::Min(80, $b.text.Length))) })
        }
      }
    }
    $inspectionSlides.Add([pscustomobject]@{ index = $index; textShapeCount = $textShapes.Count })
  }
  if ($InspectionJson) {
    $inspection = [pscustomobject]@{ status = if ($inspectionIssues.Count) { 'FAIL' } else { 'PASS' }; issueCount = $inspectionIssues.Count; issues = @($inspectionIssues | ForEach-Object { $_ }); slides = @($inspectionSlides | ForEach-Object { $_ }) }
    $inspectionText = $inspection | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($InspectionJson, $inspectionText, (New-Object System.Text.UTF8Encoding($false)))
  }
}
finally {
  if ($null -ne $presentation) { $presentation.Close() }
  $powerPoint.Quit()
  if ($null -ne $presentation) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
