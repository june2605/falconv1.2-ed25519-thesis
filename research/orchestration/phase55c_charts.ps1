using namespace System.Drawing
using namespace System.Windows.Forms.DataVisualization.Charting

param (
    [Parameter(Mandatory)] [string]$SummaryPath,
    [Parameter(Mandatory)] [string[]]$RunDirectories,
    [Parameter(Mandatory)] [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms.DataVisualization

function Read-Json([string]$Path) {
    Get-Content -Encoding UTF8 -LiteralPath $Path -Raw | ConvertFrom-Json
}

$summary = Read-Json $SummaryPath
$destination = (Resolve-Path -LiteralPath $OutputDirectory).Path
$environments = @('CI-WIN', 'CI-LINUX', 'CI-MAC')
$methods = @('Ed25519', 'Falcon-512', 'Hybrid')
$bySlot = @{}
$directories = @($RunDirectories | ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory })
foreach ($artifact in $directories) {
    $flow = Join-Path $artifact.FullName 'workflow.json'
    $session = Join-Path $artifact.FullName 'session/session.json'
    if (!(Test-Path -LiteralPath $flow) -or !(Test-Path -LiteralPath $session)) { continue }
    $identity = Read-Json $flow
    $measure = Read-Json $session
    $key = "$($identity.environment)-s$($identity.slot)"
    $record = @($summary.sessions | Where-Object { $_.provenance.session -eq $measure.session })
    if ($record.Count -ne 1 -or $bySlot.ContainsKey($key)) { throw "Unexpected summary identity $key" }
    $bySlot[$key] = $record[0]
}
if ($bySlot.Count -ne 9) { throw 'The figures require nine verified main sessions.' }

function Find-Statistic($Rows, [string]$Method, [string]$Operation, [int]$ExpectedN) {
    $record = @($Rows | Where-Object {
        $_.layer -eq 'pdf' -and $_.workload -eq '10-MiB' -and $_.method -eq $Method -and $_.operation -eq $Operation
    })
    if ($record.Count -ne 1 -or $record[0].n -ne $ExpectedN -or $record[0].unit -ne 'ms') {
        throw "Unexpected 10 MiB statistic: $Method $Operation"
    }
    return $record[0]
}

function New-Series($Chart, [string]$Name, [string]$Marker, [Color]$Color, [int]$Size) {
    $s = $Chart.Series.Add($Name)
    $s.ChartType = 'Point'
    $s.Color = $Color
    $s.MarkerStyle = $Marker
    $s.MarkerSize = $Size
    return $s
}

function Write-Medians([string]$Operation, [string]$Title, [string]$FileName) {
    $chart = [Chart]::new()
    try {
        $chart.Width = 1800
        $chart.Height = 1020
        $chart.AntiAliasing = 'All'
        $chart.BackColor = [Color]::White
        $chart.Titles.Add($Title).Font = [Font]::new('Segoe UI', 24, [FontStyle]::Bold)
        $chart.Titles.Add('Mỗi slot n = 30 · Mỗi nhóm theo môi trường n = 90').Font = [Font]::new('Segoe UI', 15)
        $legend = [Legend]::new('Median')
        $legend.Docking = 'Bottom'
        $legend.Font = [Font]::new('Segoe UI', 16)
        $chart.Legends.Add($legend)
        $area = $chart.ChartAreas.Add('Latency')
        $area.AxisY.Title = 'Trung vị thời gian (ms)'
        $area.AxisY.TitleFont = [Font]::new('Segoe UI', 19)
        $area.AxisY.LabelStyle.Font = [Font]::new('Segoe UI', 16)
        $area.AxisY.Minimum = 0
        $area.AxisY.MajorGrid.LineColor = [Color]::Gainsboro
        $area.AxisX.Minimum = 0.5
        $area.AxisX.Maximum = 9.5
        $area.AxisX.Interval = 1
        $area.AxisX.IsLabelAutoFit = $false
        $area.AxisX.MajorGrid.Enabled = $false
        $area.AxisX.MajorTickMark.Enabled = $false
        $area.AxisX.LabelStyle.Font = [Font]::new('Segoe UI', 15)
        $pooled = New-Series $chart 'Trung vị gộp' 'Diamond' ([Color]::FromArgb(48, 54, 63)) 17
        $s1 = New-Series $chart 'Slot 1' 'Circle' ([Color]::FromArgb(35, 81, 156)) 13
        $s2 = New-Series $chart 'Slot 2' 'Square' ([Color]::FromArgb(0, 112, 92)) 13
        $s3 = New-Series $chart 'Slot 3' 'Triangle' ([Color]::FromArgb(161, 82, 26)) 14
        $series = @($s1, $s2, $s3)
        $offsets = @(-0.25, -0.13, 0.20)
        $at = 0
        foreach ($environment in $environments) {
            $aggregate = @($summary.aggregates | Where-Object {
                $_.environment -eq $environment -and $_.mode -eq 'main'
            })
            if ($aggregate.Count -ne 1 -or $aggregate[0].sessions.Count -ne 3) { throw "Unexpected pool $environment" }
            foreach ($method in $methods) {
                $at++
                $label = $method + [Environment]::NewLine + $environment
                [void]$area.AxisX.CustomLabels.Add($at - 0.5, $at + 0.5, $label, 0, 'None')
                $center = Find-Statistic $aggregate[0].statistics $method $Operation 90
                [void]$pooled.Points.AddXY([double]$at, [double]$center.median)
                for ($i = 0; $i -lt 3; $i++) {
                    $slot = $i + 1
                    $row = Find-Statistic $bySlot["$environment-s$slot"].statistics $method $Operation 30
                    [void]$series[$i].Points.AddXY([double]($at + $offsets[$i]), [double]$row.median)
                }
            }
        }
        $path = Join-Path $destination $FileName
        $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
        try { $chart.SaveImage($stream, 'Png') }
        finally { $stream.Dispose() }
        Write-Output $path
    }
    finally { $chart.Dispose() }
}

Write-Medians 'sign_and_publish' 'Ký và xuất PDF 10 MiB theo môi trường và slot' 'phase5-5c-10mib-sign.png'
Write-Medians 'verify_published_file' 'Xác minh PDF 10 MiB đã xuất theo môi trường và slot' 'phase5-5c-10mib-verify.png'
