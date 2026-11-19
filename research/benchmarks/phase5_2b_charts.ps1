param (
    [Parameter(Mandatory = $true)]
    [string]$AnalysisDirectory
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing

$analysis = (Resolve-Path -LiteralPath $AnalysisDirectory).Path
$summary = @(Import-Csv -LiteralPath (Join-Path $analysis 'per-session.csv') |
    Where-Object { $_.kind -eq 'matched' -and $_.unit -eq 'ns' })
$sessions = @($summary.session | Sort-Object -Unique)
if ($sessions.Count -ne 3) { throw 'These charts require all three matched sessions.' }

$primitive = @(
    @{ mode = 'primitive'; workload = '64-B'; algorithm = 'Ed25519'; label = 'Ed25519 (64 B)' },
    @{ mode = 'primitive'; workload = '64-B'; algorithm = 'Falcon-512'; label = 'Falcon-512 (64 B)' },
    @{ mode = 'primitive'; workload = '1024-B'; algorithm = 'Ed25519'; label = 'Ed25519 (1,024 B)' },
    @{ mode = 'primitive'; workload = '1024-B'; algorithm = 'Falcon-512'; label = 'Falcon-512 (1,024 B)' }
)
$pdf = @(
    @{ mode = 'unprofiled'; workload = 'demo'; algorithm = 'Hybrid'; label = 'Public sample (742 B)' },
    @{ mode = 'unprofiled'; workload = '1-MiB'; algorithm = 'Hybrid'; label = '1 MiB' },
    @{ mode = 'unprofiled'; workload = '10-MiB'; algorithm = 'Hybrid'; label = '10 MiB' }
)

function Write-SessionChart {
    param (
        [string]$FileName, [string]$Title, [string]$Unit,
        [object[]]$Conditions, [string]$Operation, [double]$Scale, [switch]$Logarithmic
    )

    $chart = [System.Windows.Forms.DataVisualization.Charting.Chart]::new()
    try {
        $chart.Width = 1400
        $chart.Height = 820
        $chart.AntiAliasing = 'All'
        $chart.BackColor = [System.Drawing.Color]::White
        $area = [System.Windows.Forms.DataVisualization.Charting.ChartArea]::new('Matched')
        $area.AxisY.Title = "Session median elapsed time ($Unit)"
        $area.AxisY.TitleFont = [System.Drawing.Font]::new('Segoe UI', 14)
        $area.AxisY.LabelStyle.Font = [System.Drawing.Font]::new('Segoe UI', 13)
        $area.AxisY.MajorGrid.LineColor = [System.Drawing.Color]::Gainsboro
        if ($Logarithmic) {
            $area.AxisY.IsLogarithmic = $true
            $area.AxisY.LogarithmBase = 10
            $area.AxisY.Minimum = 10
            $area.AxisY.Maximum = 10000
            $area.AxisY.Interval = 1
        }
        else { $area.AxisY.Minimum = 0 }
        $area.AxisX.Minimum = 0.5
        $area.AxisX.Maximum = $Conditions.Count + 0.5
        $area.AxisX.MajorGrid.Enabled = $false
        $area.AxisX.MajorTickMark.Enabled = $false
        $area.AxisX.LabelStyle.Font = [System.Drawing.Font]::new('Segoe UI', 13)
        for ($i = 0; $i -lt $Conditions.Count; $i++) {
            [void]$area.AxisX.CustomLabels.Add($i + 0.5, $i + 1.5, $Conditions[$i].label, 0, 'None')
        }
        $chart.ChartAreas.Add($area)
        $heading = $chart.Titles.Add($Title)
        $heading.Font = [System.Drawing.Font]::new('Segoe UI', 20, [System.Drawing.FontStyle]::Bold)
        $caption = $chart.Titles.Add('Phase 5.2B | 3 fresh processes on one host | 30 measured trials per session and condition')
        $caption.Font = [System.Drawing.Font]::new('Segoe UI', 12)
        $legend = [System.Windows.Forms.DataVisualization.Charting.Legend]::new('Sessions')
        $legend.Docking = 'Bottom'
        $legend.Font = [System.Drawing.Font]::new('Segoe UI', 12)
        $chart.Legends.Add($legend)

        $colors = @([System.Drawing.Color]::FromArgb(32, 80, 166),
                    [System.Drawing.Color]::FromArgb(13, 128, 112),
                    [System.Drawing.Color]::FromArgb(155, 65, 10))
        $shapes = @('Circle', 'Square', 'Triangle')
        for ($index = 0; $index -lt $sessions.Count; $index++) {
            $session = $sessions[$index]
            $series = $chart.Series.Add($session)
            $series.ChartType = 'Point'
            $series.Color = $colors[$index]
            $series.MarkerStyle = $shapes[$index]
            $series.MarkerSize = 15
            for ($at = 0; $at -lt $Conditions.Count; $at++) {
                $condition = $Conditions[$at]
                $row = @($summary | Where-Object {
                    $_.session -eq $session -and $_.mode -eq $condition.mode -and
                    $_.workload -eq $condition.workload -and $_.algorithm -eq $condition.algorithm -and
                    $_.operation -eq $Operation
                })
                if ($row.Count -ne 1 -or [int]$row[0].n -ne 30) { throw 'Incomplete or repeated matched chart series.' }
                $value = [double]::Parse($row[0].median, [System.Globalization.CultureInfo]::InvariantCulture) / $Scale
                [void]$series.Points.AddXY([double]($at + 1 + ($index - 1) * 0.12), $value)
            }
        }

        $destination = Join-Path $analysis $FileName
        $stream = [System.IO.File]::Open($destination, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
        try { $chart.SaveImage($stream, 'Png') }
        finally { $stream.Dispose() }
        Write-Output $destination
    }
    finally { $chart.Dispose() }
}

Write-SessionChart 'primitive-sign.png' 'Matched primitive signing | logarithmic time axis' 'microseconds, log scale' $primitive 'sign' 1000 -Logarithmic
Write-SessionChart 'primitive-verify.png' 'Matched primitive verification' 'microseconds' $primitive 'verify' 1000
Write-SessionChart 'hybrid-sign.png' 'Hybrid PDF signing and atomic publication' 'milliseconds' $pdf 'sign_and_publish' 1000000
Write-SessionChart 'hybrid-verify.png' 'Hybrid verification of the published PDF' 'milliseconds' $pdf 'verify_published_file' 1000000
