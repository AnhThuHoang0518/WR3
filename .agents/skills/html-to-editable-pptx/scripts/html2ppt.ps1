param(
  [Parameter(Position=0, Mandatory=$true)][string]$InputHtml,
  [Parameter(ValueFromRemainingArguments=$true)][string[]]$ConverterArguments
)

$ErrorActionPreference = 'Stop'
$skillRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$inputPath = (Resolve-Path -LiteralPath $InputHtml).Path
$cli = Join-Path $skillRoot 'bin\html2ppt.js'
if (-not (Test-Path -LiteralPath (Join-Path $skillRoot 'node_modules'))) {
  throw "Dependencies are missing. Run npm install in $skillRoot before conversion."
}

function Get-OptionValue {
  param([string[]]$Arguments, [string]$Name)
  for ($index = 0; $index -lt $Arguments.Count - 1; $index++) {
    if ($Arguments[$index] -eq $Name) { return $Arguments[$index + 1] }
  }
  return $null
}

function Update-ConversionReport {
  param([string]$ReportPath, [hashtable]$FontAutomation, [switch]$FailGate)
  if (-not (Test-Path -LiteralPath $ReportPath)) { return }
  $report = Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json
  $report | Add-Member -NotePropertyName fontAutomation -NotePropertyValue ([pscustomobject]$FontAutomation) -Force
  if ($report.nativeObjects) {
    $report.nativeObjects | Add-Member -NotePropertyName fontEmbedding -NotePropertyValue $FontAutomation.status -Force
  }
  if ($FailGate) {
    $report.output = $null
    if (-not $report.qualityGate) {
      $report | Add-Member -NotePropertyName qualityGate -NotePropertyValue ([pscustomobject]@{ status = 'FAIL'; reasons = @(); deliveryPolicy = 'Do not deliver.' }) -Force
    }
    $report.qualityGate.status = 'FAIL'
    $report.qualityGate.reasons = @($report.qualityGate.reasons) + 'FONT_EMBEDDING_FAILED'
  }
  $reportText = $report | ConvertTo-Json -Depth 100
  [System.IO.File]::WriteAllText($ReportPath, $reportText, (New-Object System.Text.UTF8Encoding($false)))
}

function Get-EmbeddedFontCount {
  param([string]$PptxPath)
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive = [System.IO.Compression.ZipFile]::OpenRead($PptxPath)
  try {
    return @($archive.Entries | Where-Object { $_.FullName -like 'ppt/fonts/*.fntdata' }).Count
  } finally {
    $archive.Dispose()
  }
}

function Save-WithEmbeddedFonts {
  param([string]$PptxPath)
  $parent = Split-Path -Parent $PptxPath
  $stem = [System.IO.Path]::GetFileNameWithoutExtension($PptxPath)
  $temporary = Join-Path $parent ($stem + '.font-embed-' + [guid]::NewGuid().ToString('N') + '.pptx')
  $powerPoint = $null
  $presentation = $null
  try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Open($PptxPath, $true, $false, $false)
    $presentation.SaveAs($temporary, 24, $true)
    $presentation.Close()
    $presentation = $null
    $powerPoint.Quit()
    $powerPoint = $null
    if (-not (Test-Path -LiteralPath $temporary)) { throw 'PowerPoint did not create the font-embedded file.' }
    [System.IO.File]::Copy($temporary, $PptxPath, $true)
  } finally {
    if ($presentation) { try { $presentation.Close() } catch {} }
    if ($powerPoint) { try { $powerPoint.Quit() } catch {} }
    if ($presentation) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($presentation) }
    if ($powerPoint) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($powerPoint) }
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
  }
}

if (-not ([System.Management.Automation.PSTypeName]'HtmlToPptFontResource').Type) {
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HtmlToPptFontResource {
  [DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
  public static extern int AddFontResourceEx(string fileName, uint flags, IntPtr reserved);
  [DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
  public static extern bool RemoveFontResourceEx(string fileName, uint flags, IntPtr reserved);
  [DllImport("user32.dll", CharSet = CharSet.Auto)]
  public static extern IntPtr SendMessageTimeout(IntPtr window, uint message, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
}
'@
}

$outputOption = Get-OptionValue -Arguments $ConverterArguments -Name '--output'
$outputPath = if ($outputOption) { [System.IO.Path]::GetFullPath($outputOption) } else { [System.IO.Path]::ChangeExtension($inputPath, '.pptx') }
$artifactOption = Get-OptionValue -Arguments $ConverterArguments -Name '--artifacts'
$artifactRoot = if ($artifactOption) { [System.IO.Path]::GetFullPath($artifactOption) } else { $outputPath + '.validation' }
$reportPath = Join-Path $artifactRoot 'conversion-report.json'
$fontRuntime = Join-Path $artifactRoot 'font-runtime'
New-Item -ItemType Directory -Force -Path $fontRuntime | Out-Null

$registeredFonts = New-Object System.Collections.Generic.List[string]
$fontSources = New-Object System.Collections.Generic.List[object]
$html = Get-Content -LiteralPath $inputPath -Raw
$fontBlocks = [regex]::Matches($html, '@font-face\s*\{(?<body>.*?)\}', [Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [Text.RegularExpressions.RegexOptions]::Singleline)
$fontIndex = 0
foreach ($fontBlock in $fontBlocks) {
  $body = $fontBlock.Groups['body'].Value
  $familyMatch = [regex]::Match($body, 'font-family\s*:\s*["'']?(?<family>[^;"'']+)', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
  $urlMatch = [regex]::Match($body, 'url\(\s*["'']?(?<url>[^)"'']+)', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if (-not $urlMatch.Success) { continue }
  $family = if ($familyMatch.Success) { $familyMatch.Groups['family'].Value.Trim() } else { 'embedded-font' }
  $url = $urlMatch.Groups['url'].Value.Trim()
  $fontPath = $null
  $format = $null
  if ($url -match '^data:font/(?<format>[^;]+);base64,(?<data>.+)$') {
    $format = $Matches['format'].ToLowerInvariant()
    if ($format -notin @('ttf', 'truetype', 'otf', 'opentype')) {
      $fontSources.Add([pscustomobject]@{ family = $family; source = 'embedded-data'; format = $format; status = 'UNSUPPORTED_FOR_POWERPOINT' })
      continue
    }
    $extension = if ($format -in @('otf', 'opentype')) { '.otf' } else { '.ttf' }
    $safeFamily = ($family -replace '[^A-Za-z0-9._-]', '-')
    $fontPath = Join-Path $fontRuntime ('{0:D2}-{1}{2}' -f (++$fontIndex), $safeFamily, $extension)
    [System.IO.File]::WriteAllBytes($fontPath, [Convert]::FromBase64String($Matches['data']))
  } elseif ($url -notmatch '^https?:') {
    try {
      $fontPath = if ($url -match '^file:') { ([uri]$url).LocalPath } else { [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $inputPath) ([uri]::UnescapeDataString($url)))) }
      $format = [System.IO.Path]::GetExtension($fontPath).TrimStart('.').ToLowerInvariant()
    } catch {
      $fontPath = $null
    }
  }
  if ($fontPath -and (Test-Path -LiteralPath $fontPath) -and ([System.IO.Path]::GetExtension($fontPath) -match '^\.(ttf|otf)$')) {
    $added = [HtmlToPptFontResource]::AddFontResourceEx($fontPath, 0, [IntPtr]::Zero)
    if ($added -gt 0) { $registeredFonts.Add($fontPath) }
    $fontSources.Add([pscustomobject]@{ family = $family; source = $fontPath; format = $format; status = if ($added -gt 0) { 'REGISTERED_FOR_SESSION' } else { 'REGISTRATION_FAILED' } })
  }
}

if ($registeredFonts.Count -gt 0) {
  $broadcastResult = [IntPtr]::Zero
  [void][HtmlToPptFontResource]::SendMessageTimeout([IntPtr]0xffff, 0x001D, [IntPtr]::Zero, [IntPtr]::Zero, 2, 3000, [ref]$broadcastResult)
}

$arguments = @($cli, $inputPath) + $ConverterArguments
$exitCode = 1
$fontStatus = [ordered]@{
  status = if ($fontSources.Count) { 'REGISTERED_PENDING_EMBED' } else { 'NOT_APPLICABLE' }
  discovered = $fontSources.Count
  registered = $registeredFonts.Count
  sources = @($fontSources | ForEach-Object { $_ })
  embeddedFontEntries = 0
}

try {
  $node = Get-Command node -ErrorAction SilentlyContinue
  if ($node) {
    & $node.Source @arguments
    $exitCode = $LASTEXITCODE
  } else {
    $codeNode = 'C:\Users\thuha13\AppData\Local\Programs\Microsoft VS Code\Code.exe'
    if (-not (Test-Path -LiteralPath $codeNode)) {
      throw 'Node.js is not available. Install Node.js 20+ or provide a Node-compatible runtime.'
    }
    $previousElectronRunAsNode = $env:ELECTRON_RUN_AS_NODE
    $env:ELECTRON_RUN_AS_NODE = '1'
    try {
      # Code.exe can detach its Node-compatible child before PowerShell's call
      # operator returns. Start-Process -Wait keeps font registration active and
      # prevents the wrapper from attempting font embedding before conversion ends.
      $quotedArguments = @($arguments | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' })
      $nodeProcess = Start-Process -FilePath $codeNode -ArgumentList $quotedArguments -Wait -PassThru -WindowStyle Hidden
      $exitCode = $nodeProcess.ExitCode
    } finally {
      $env:ELECTRON_RUN_AS_NODE = $previousElectronRunAsNode
    }
  }

  if ($exitCode -eq 0 -and $fontSources.Count -gt 0) {
    try {
      Save-WithEmbeddedFonts -PptxPath $outputPath
      $embeddedFontCount = Get-EmbeddedFontCount -PptxPath $outputPath
      $fontStatus.embeddedFontEntries = $embeddedFontCount
      if ($embeddedFontCount -lt 1) { throw 'PowerPoint saved the deck without any embedded font entries.' }
      $fontStatus.status = 'EMBEDDED'
      Update-ConversionReport -ReportPath $reportPath -FontAutomation $fontStatus
    } catch {
      $fontStatus.status = 'FAIL'
      $fontStatus.error = $_.Exception.Message
      Update-ConversionReport -ReportPath $reportPath -FontAutomation $fontStatus -FailGate
      Write-Error "Font embedding failed; the PPTX must not be delivered. $($_.Exception.Message)"
      $exitCode = 3
    }
  } else {
    Update-ConversionReport -ReportPath $reportPath -FontAutomation $fontStatus
  }
} finally {
  foreach ($fontPath in $registeredFonts) {
    [void][HtmlToPptFontResource]::RemoveFontResourceEx($fontPath, 0, [IntPtr]::Zero)
  }
  if ($registeredFonts.Count -gt 0) {
    $broadcastResult = [IntPtr]::Zero
    [void][HtmlToPptFontResource]::SendMessageTimeout([IntPtr]0xffff, 0x001D, [IntPtr]::Zero, [IntPtr]::Zero, 2, 3000, [ref]$broadcastResult)
  }
}

exit $exitCode
