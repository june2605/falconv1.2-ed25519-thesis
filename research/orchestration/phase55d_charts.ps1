using namespace System.Drawing
using namespace System.Globalization
using namespace System.Windows.Forms.DataVisualization.Charting

param (
    [Parameter(Mandatory)] [string]$DataPath,
    [Parameter(Mandatory)] [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms.DataVisualization

$data = Get-Content -LiteralPath $DataPath -Encoding UTF8 -Raw | ConvertFrom-Json
$destination = (Resolve-Path -LiteralPath $OutputDirectory).Path
$environments = [ordered]@{ 'CI-WIN' = 'Windows'; 'CI-LINUX' = 'Ubuntu'; 'CI-MAC' = 'macOS Intel' }
$workloads = [ordered]@{ 'demo' = '742 byte'; '1-MiB' = '1 MiB'; '10-MiB' = '10 MiB' }
$methods = @('Ed25519', 'Falcon-512', 'Hybrid')
$colors = @([Color]::FromArgb(34, 81, 143), [Color]::FromArgb(158, 82, 16), [Color]::FromArgb(12, 111, 94))
$markers = @('Circle', 'Square', 'Diamond')

function Add-Heading($Chart, [string]$Text, $Position, [int]$Size, [FontStyle]$Style) {
    $title = [Title]::new($Text)
    $title.Font = [Font]::new('Segoe UI', $Size, $Style)
    $title.ForeColor = [Color]::FromArgb(29, 37, 47)
    $title.Position = $Position
    [void]$Chart.Titles.Add($title)
}

function New-Canvas([string]$Heading, [string]$Description) {
    $chart = [Chart]::new()
    $chart.Width = 1920
    $chart.Height = 920
    $chart.BackColor = [Color]::White
    $chart.AntiAliasing = 'All'
    $chart.TextAntiAliasingQuality = 'High'
    Add-Heading $chart $Heading ([ElementPosition]::new(3, 3, 94, 9)) 27 Bold
    Add-Heading $chart $Description ([ElementPosition]::new(3, 12, 94, 7)) 17 Regular
    $legend = [Legend]::new('Chú giải')
    $legend.Font = [Font]::new('Segoe UI', 18)
    $legend.Position = [ElementPosition]::new(5, 85, 90, 10)
    $legend.Alignment = 'Center'
    $legend.LegendStyle = 'Row'
    $chart.Legends.Add($legend)
    return $chart
}

function New-Plot($Chart, [string]$Name, $Position, $Inner, [string[]]$Labels) {
    $area = $Chart.ChartAreas.Add($Name)
    $area.Position = $Position
    $area.InnerPlotPosition = $Inner
    $area.AxisX.Minimum = 0.5
    $area.AxisX.Maximum = $Labels.Length + 0.5
    $area.AxisX.Interval = 1
    $area.AxisX.MajorGrid.Enabled = $false
    $area.AxisX.MajorTickMark.Enabled = $false
    $area.AxisX.IsLabelAutoFit = $false
    $area.AxisX.LabelStyle.Font = [Font]::new('Segoe UI', 17)
    for ($i = 0; $i -lt $Labels.Length; $i++) {
        [void]$area.AxisX.CustomLabels.Add($i + 0.5, $i + 1.5, $Labels[$i], 0, 'None')
    }
    $area.AxisY.IsLabelAutoFit = $false
    $area.AxisY.LabelStyle.Font = [Font]::new('Segoe UI', 17)
    $area.AxisY.LabelStyle.Format = '0.###'
    $area.AxisY.MajorGrid.LineColor = [Color]::FromArgb(220, 225, 231)
    return $area
}

function Set-AxisScale($Axis, [double]$Lower, [double]$Upper) {
    $min = [Math]::Min($Lower, 0)
    $span = ($Upper - $min) * 1.12
    if ($span -le 0) { throw 'Invalid plot range.' }
    $target = $span / 5
    $magnitude = [Math]::Pow(10, [Math]::Floor([Math]::Log10($target)))
    $steps = @(1, 2, 2.5, 5, 10)
    $step = ($steps | Where-Object { $_ * $magnitude -ge $target } | Select-Object -First 1) * $magnitude
    $Axis.Minimum = [Math]::Floor($min / $step) * $step
    $Axis.Maximum = [Math]::Ceiling(($min + $span) / $step) * $step
    $Axis.Interval = $step
}

function Add-Intervals($Chart, $Area, $Rows, [string]$Category, [string[]]$Labels, [string[]]$LegendText) {
    $plotNumber = 0
    $offset = if ($Labels.Count -eq 2) { @(-0.17, 0.17) } else { @(-0.24, 0, 0.24) }
    foreach ($label in $Labels) {
        $id = "$($Area.Name)-$plotNumber"
        $range = $Chart.Series.Add("IQR-$id")
        $range.ChartArea = $Area.Name
        $range.ChartType = 'ErrorBar'
        $range.YValuesPerPoint = 3
        $range.Color = $colors[$plotNumber]
        $range.BorderWidth = 4
        $range['PointWidth'] = '0.32'
        $range.IsVisibleInLegend = $false
        $range['ErrorBarStyle'] = 'Both'
        $range['ErrorBarCenterMarkerStyle'] = 'None'
        $points = $Chart.Series.Add("Median-$id")
        $points.ChartArea = $Area.Name
        $points.ChartType = 'Point'
        $points.Color = $colors[$plotNumber]
        $points.MarkerStyle = $markers[$plotNumber]
        $points.MarkerSize = 17
        $points.LegendText = $LegendText[$plotNumber]
        $points.IsVisibleInLegend = $Area.Name -eq 'PDF-1'
        $index = 0
        foreach ($environment in $environments.Keys) {
            $index++
            $row = @($Rows | Where-Object { $_.environment -eq $environment -and $_.$Category -eq $label })
            if ($row.Count -ne 1 -or $row[0].n -ne 90) { throw "Incomplete group: $id / $environment" }
            $x = [double]($index + $offset[$plotNumber])
            $median = [double]$row[0].median
            $q1 = [double]$row[0].q1
            $q3 = [double]$row[0].q3
            if ($median -lt $q1 -or $median -gt $q3) { throw "Invalid quartiles: $id / $environment" }
            [void]$range.Points.Add([DataPoint]::new($x, [double[]]@($median, $q1, $q3)))
            [void]$points.Points.AddXY($x, $median)
        }
        $plotNumber++
    }
}

function Save-Figure($Chart, [string]$Name) {
    $path = Join-Path $destination $Name
    $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $Chart.SaveImage($stream, 'Png') } finally { $stream.Dispose() }
    Write-Output $path
}

function Write-Latency($Rows, [string]$Category, [string[]]$Labels, [string[]]$LegendText,
                      [string]$Title, [string]$Name) {
    $chart = New-Canvas $Title 'Trung vị và Q1-Q3 (ms), n = 90. Mỗi cỡ PDF dùng một thang tuyến tính.'
    try {
        $index = 0
        foreach ($workload in $workloads.Keys) {
            $left = 1 + $index * 33
            $index++
            $rowsForSize = @($Rows | Where-Object workload -eq $workload)
            if ($rowsForSize.Count -ne $Labels.Count * $environments.Count) {
                throw "Unexpected number of observations for $workload."
            }
            Add-Heading $chart $workloads[$workload] ([ElementPosition]::new($left, 20, 32, 6)) 19 Bold
            $area = New-Plot $chart "PDF-$index" ([ElementPosition]::new($left, 27, 32, 53)) `
                ([ElementPosition]::new(18, 3, 79, 84)) @($environments.Values)
            $low = ($rowsForSize | Measure-Object q1 -Minimum).Minimum
            $high = ($rowsForSize | Measure-Object q3 -Maximum).Maximum
            Set-AxisScale $area.AxisY $low $high
            Add-Intervals $chart $area $rowsForSize $Category $Labels $LegendText
        }
        Save-Figure $chart $Name
    } finally { $chart.Dispose() }
}

function Write-Storage {
    $chart = New-Canvas 'Mức tăng kích thước của PDF sau ký' 'Số byte ghi thêm theo cấu hình mặc định'
    try {
        $area = New-Plot $chart 'Storage' ([ElementPosition]::new(6, 22, 88, 58)) `
            ([ElementPosition]::new(10, 3, 87, 85)) $methods
        $area.AxisY.LabelStyle.Format = 'N0'
        Set-AxisScale $area.AxisY 0 (($data.storage | Measure-Object growth -Maximum).Maximum)
        $hex = $chart.Series.Add('Ô Contents (hex và đệm)')
        $frame = $chart.Series.Add('Dấu, siêu dữ liệu và cú pháp')
        foreach ($series in @($hex, $frame)) {
            $series.ChartArea = $area.Name
            $series.ChartType = 'StackedColumn'
            $series['PointWidth'] = '0.46'
        }
        $hex.Color = [Color]::FromArgb(34, 81, 143)
        $frame.Color = [Color]::FromArgb(231, 173, 84)
        $totals = $chart.Series.Add('Tổng')
        $totals.ChartArea = $area.Name
        $totals.ChartType = 'Point'
        $totals.Color = [Color]::Transparent
        $totals.MarkerStyle = 'None'
        $totals.IsVisibleInLegend = $false
        $totals.Font = [Font]::new('Segoe UI', 20, [FontStyle]::Bold)
        $totals.LabelForeColor = [Color]::FromArgb(29, 37, 47)
        $totals['LabelStyle'] = 'Top'
        $index = 0
        foreach ($method in $methods) {
            $index++
            $row = @($data.storage | Where-Object method -eq $method)
            if ($row.Count -ne 1 -or $row[0].growth -ne $row[0].contents + $row[0].metadata) {
                throw "Invalid storage data: $method"
            }
            [void]$hex.Points.AddXY($index, [double]$row[0].contents)
            [void]$frame.Points.AddXY($index, [double]$row[0].metadata)
            $point = $totals.Points.AddXY($index, [double]($row[0].growth + $area.AxisY.Interval * 0.13))
            $totals.Points[$point].Label = ([double]$row[0].growth).ToString('N0')
        }
        Save-Figure $chart 'tang-truong-pdf.png'
    } finally { $chart.Dispose() }
}

$thread = [System.Threading.Thread]::CurrentThread
$originalCulture = $thread.CurrentCulture
$culture = [CultureInfo]::new('vi-VN')
$culture.NumberFormat.NumberGroupSeparator = ' '
$thread.CurrentCulture = $culture
try {
    $sign = 'sign_and_publish'
    $verify = 'verify_published_file'
    Write-Latency @($data.pdf | Where-Object operation -eq $sign) method $methods $methods `
        'Thời gian ký và xuất PDF' 'pdf-ky-va-xuat.png'
    Write-Latency @($data.pdf | Where-Object operation -eq $verify) method $methods $methods `
        'Thời gian xác minh PDF đã xuất' 'pdf-xac-minh.png'
    $baselines = $methods[0..1]
    $differences = @('Hybrid - Ed25519', 'Hybrid - Falcon-512')
    Write-Latency @($data.paired | Where-Object operation -eq $sign) baseline $baselines $differences `
        'Chênh lệch ghép cặp khi ký và xuất PDF' 'chenh-lech-ky-va-xuat.png'
    Write-Latency @($data.paired | Where-Object operation -eq $verify) baseline $baselines $differences `
        'Chênh lệch ghép cặp khi xác minh PDF' 'chenh-lech-xac-minh.png'
    Write-Storage
} finally { $thread.CurrentCulture = $originalCulture }
