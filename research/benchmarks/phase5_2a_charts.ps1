param (
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing

$run = (Resolve-Path -LiteralPath $RunDirectory).Path
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $run 'experiment.json') | ConvertFrom-Json
if ($manifest.status -ne 'complete') { throw 'Charts require a completed pilot.' }
$summary = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $run 'summary.json') | ConvertFrom-Json

function Write-ComparisonChart {
    param (
        [string]$FileName,
        [string]$Title,
        [string]$VerticalLabel,
        [string[]]$Labels,
        [System.Collections.IDictionary]$Columns
    )

    $chart = [System.Windows.Forms.DataVisualization.Charting.Chart]::new()
    try {
        $chart.Width = 900
        $chart.Height = 500
        $chart.AntiAliasing = 'All'
        $chart.BackColor = [System.Drawing.Color]::White
        $area = [System.Windows.Forms.DataVisualization.Charting.ChartArea]::new('Pilot')
        $area.AxisY.Minimum = 0
        $area.AxisY.Title = $VerticalLabel
        $area.AxisY.MajorGrid.LineColor = [System.Drawing.Color]::Gainsboro
        $area.AxisX.Interval = 1
        $area.AxisX.MajorGrid.Enabled = $false
        $area.AxisX.LabelStyle.IsEndLabelVisible = $true
        $chart.ChartAreas.Add($area)
        $titleObject = $chart.Titles.Add($Title)
        $titleObject.Font = [System.Drawing.Font]::new('Segoe UI', 15, [System.Drawing.FontStyle]::Bold)
        $legend = [System.Windows.Forms.DataVisualization.Charting.Legend]::new('Operations')
        $legend.Docking = 'Bottom'
        $chart.Legends.Add($legend)
        $colors = @([System.Drawing.Color]::FromArgb(45, 72, 170), [System.Drawing.Color]::FromArgb(0, 124, 115))
        $index = 0
        foreach ($label in $Columns.Keys) {
            $series = $chart.Series.Add($label)
            $series.ChartType = 'Column'
            $series.IsXValueIndexed = $true
            $series.Color = $colors[$index]
            for ($at = 0; $at -lt $Labels.Count; $at++) {
                [void]$series.Points.AddXY([object]$Labels[$at], [object[]]@([double]$Columns[$label][$at]))
            }
            $index++
        }
        $target = Join-Path $run $FileName
        $stream = [System.IO.File]::Open($target, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
        try { $chart.SaveImage($stream, 'Png') }
        finally { $stream.Dispose() }
        Write-Output $target
    }
    finally { $chart.Dispose() }
}

function Get-Median {
    param (
        [string]$Mode,
        [string]$Workload,
        [string]$Algorithm,
        [string]$Operation
    )

    $rows = @($summary | Where-Object {
        $_.unit -eq 'ns' -and $_.mode -eq $Mode -and $_.workload -eq $Workload -and
        $_.algorithm -eq $Algorithm -and $_.operation -eq $Operation
    })
    if ($rows.Count -ne 1) { throw "Expected a unique median for $Mode, $Workload, $Algorithm, $Operation" }
    return [double]$rows[0].median
}

$primitive = [ordered]@{}
foreach ($algorithm in @('Ed25519', 'Falcon-512')) {
    $primitive[$algorithm] = @(
        (Get-Median 'primitive' '64-B' $algorithm 'sign') / 1000
        (Get-Median 'primitive' '64-B' $algorithm 'verify') / 1000
    )
}
Write-ComparisonChart 'primitive-64b-median.png' 'Phase 5.2A pilot | 64-byte primitive calls' 'Median elapsed time (microseconds)' @('Sign', 'Verify') $primitive

$workloads = @($manifest.pdf_inputs | ForEach-Object { $_.workload })
$labels = @($workloads | ForEach-Object { if ($_ -eq 'demo') { 'Public sample' } else { $_ -replace '-', ' ' } })
$pdf = [ordered]@{
    'Sign and publish' = @($workloads | ForEach-Object { (Get-Median 'unprofiled' $_ 'Hybrid' 'sign_and_publish') / 1000000 })
    'Verify published file' = @($workloads | ForEach-Object { (Get-Median 'unprofiled' $_ 'Hybrid' 'verify_published_file') / 1000000 })
}
Write-ComparisonChart 'hybrid-pdf-median.png' 'Phase 5.2A pilot | Real hybrid PDF pipeline' 'Median elapsed time (milliseconds)' $labels $pdf
