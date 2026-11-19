using namespace System.Drawing
using namespace System.Globalization
using namespace System.Windows.Forms.DataVisualization.Charting

param (
    [Parameter(Mandatory = $true)]
    [string]$AnalysisDirectory
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing

$directory = (Resolve-Path -LiteralPath $AnalysisDirectory).Path
$data = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $directory 'plot-data.json') | ConvertFrom-Json
$labels = $data.labels
[System.Threading.Thread]::CurrentThread.CurrentCulture = [CultureInfo]::GetCultureInfo('vi-VN')
$colors = @([Color]::FromArgb(34, 78, 150), [Color]::FromArgb(0, 111, 96),
            [Color]::FromArgb(145, 76, 17), [Color]::FromArgb(157, 49, 80))
$markers = @('Circle', 'Square', 'Triangle', 'Cross')

function New-Chart([string]$Title, [string]$Subtitle) {
    $chart = [Chart]::new()
    $chart.Width = 1800
    $chart.Height = 1050
    $chart.AntiAliasing = 'All'
    $chart.BackColor = [Color]::White
    $chart.Titles.Add($Title).Font = [Font]::new('Segoe UI', 25, [FontStyle]::Bold)
    $chart.Titles.Add($Subtitle).Font = [Font]::new('Segoe UI', 15)
    $legend = [Legend]::new('Methods')
    $legend.Docking = 'Bottom'
    $legend.Font = [Font]::new('Segoe UI', 15)
    $chart.Legends.Add($legend)
    return $chart
}

function New-PlotArea([string]$Name, [string]$AxisTitle) {
    $area = [ChartArea]::new($Name)
    $area.AxisX.MajorGrid.Enabled = $false
    $area.AxisX.LabelStyle.Font = [Font]::new('Segoe UI', 17)
    $area.AxisX.TitleFont = [Font]::new('Segoe UI', 17)
    $area.AxisY.LabelStyle.Font = [Font]::new('Segoe UI', 15)
    $area.AxisY.TitleFont = [Font]::new('Segoe UI', 17)
    $area.AxisY.Title = $AxisTitle
    $area.AxisY.LabelStyle.Format = '0.###'
    $area.AxisY.MajorGrid.LineColor = [Color]::Gainsboro
    return $area
}

function Add-Series($Chart, [string]$Name, [string]$Area, [string]$Type, [Color]$Color) {
    $series = $Chart.Series.Add($Name)
    $series.ChartArea = $Area
    $series.ChartType = $Type
    $series.Color = $Color
    return $series
}

function Save-Chart($Chart, [string]$Name) {
    $destination = Join-Path $directory ($Name + '.png')
    $stream = [System.IO.File]::Open($destination, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
    try { $Chart.SaveImage($stream, 'Png') }
    finally { $stream.Dispose() }
    Write-Output $destination
}

function Write-ComparisonChart($Plot) {
    $chart = New-Chart $Plot.title $Plot.subtitle
    try {
        $yTitle = if ($Plot.logarithmic) { $labels.log_ms } else { $labels.ms }
        $area = New-PlotArea 'Comparison' $yTitle
        $area.AxisX.Minimum = 0.5
        $area.AxisX.Maximum = $Plot.groups.Count + 0.5
        $area.AxisX.MajorTickMark.Enabled = $false
        $area.AxisX.IsLabelAutoFit = $false
        if ($Plot.logarithmic) {
            $area.AxisY.IsLogarithmic = $true
            $area.AxisY.LogarithmBase = 10
            $area.AxisY.Minimum = 0.01
            $area.AxisY.Maximum = 10
            $area.AxisY.Interval = 1
        }
        else { $area.AxisY.Minimum = 0 }
        $chart.ChartAreas.Add($area)

        $gray = [Color]::FromArgb(70, 76, 85)
        $median = Add-Series $chart $labels.median $area.Name 'Point' $gray
        $median.MarkerStyle = 'Diamond'
        $median.MarkerSize = 19
        for ($at = 0; $at -lt $Plot.groups.Count; $at++) {
            $group = $Plot.groups[$at]
            $x = $at + 1
            [void]$area.AxisX.CustomLabels.Add($x - 0.5, $x + 0.5, $group.label, 0, 'None')
            [void]$median.Points.AddXY([double]$x, [double]$group.median_ms)
            $quartiles = Add-Series $chart "iqr-$at" $area.Name 'Line' $gray
            $quartiles.LegendText = 'Q1-Q3'
            $quartiles.IsVisibleInLegend = ($at -eq 0)
            $quartiles.BorderWidth = 4
            $quartiles.MarkerStyle = 'Square'
            $quartiles.MarkerSize = 7
            foreach ($quartile in $group.iqr_ms) {
                [void]$quartiles.Points.AddXY([double]($x + 0.06), [double]$quartile)
            }
        }
        $sessions = @($data.sessions) + @($data.supplement)
        for ($i = 0; $i -lt $sessions.Count; $i++) {
            $session = $sessions[$i]
            $selected = @($Plot.groups | Where-Object { $null -ne $_.session_medians_ms.PSObject.Properties[$session] })
            if ($selected.Count -eq 0) { continue }
            $series = Add-Series $chart $session $area.Name 'Point' $colors[$i]
            $series.MarkerStyle = $markers[$i]
            $series.MarkerSize = 15
            if ($session -eq $data.supplement) { $series.LegendText = $labels.supplement }
            for ($at = 0; $at -lt $Plot.groups.Count; $at++) {
                $point = $Plot.groups[$at].session_medians_ms.PSObject.Properties[$session]
                if ($null -ne $point) {
                    $offset = @(-0.24, -0.12, 0.18, 0.19)[$i]
                    [void]$series.Points.AddXY([double]($at + 1 + $offset), [double]$point.Value)
                }
            }
        }
        Save-Chart $chart $Plot.name
    }
    finally { $chart.Dispose() }
}

foreach ($plot in $data.plots) { Write-ComparisonChart $plot }

$tail = New-Chart $labels.tail_title $labels.tail_caption
try {
    for ($at = 0; $at -lt $data.tails.Count; $at++) {
        $group = $data.tails[$at]
        $area = New-PlotArea "Tail-$at" $labels.ms
        $area.Position = [ElementPosition]::new([float](2 + 33 * $at), 15, 31, 72)
        $area.AxisX.Title = $group.label
        $area.AxisX.Minimum = 0
        $area.AxisX.Maximum = 32
        $area.AxisX.Interval = 10
        $area.AxisY.Minimum = 0
        $tail.ChartAreas.Add($area)
        for ($i = 0; $i -lt $data.sessions.Count; $i++) {
            $session = $data.sessions[$i]
            $series = Add-Series $tail "$at-$session" $area.Name 'Point' $colors[$i]
            $series.LegendText = $session
            $series.IsVisibleInLegend = ($at -eq 0)
            $series.MarkerStyle = $markers[$i]
            $series.MarkerSize = 9
            $values = $group.series.PSObject.Properties[$session].Value
            for ($rank = 0; $rank -lt $values.Count; $rank++) {
                [void]$series.Points.AddXY([double]($rank + 1), [double]$values[$rank])
            }
        }
    }
    Save-Chart $tail 'hybrid-sign-session-variability'
}
finally { $tail.Dispose() }
