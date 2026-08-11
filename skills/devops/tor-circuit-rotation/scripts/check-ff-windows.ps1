# check-ff-windows.ps1 — Comprehensive Firefox orphan detection
# 
# Shows ALL firefox.exe processes, identifies which have live windows
# (non-empty MainWindowTitle) vs orphans (N/A or empty title).
# Counts are printed first for easy parsing; details follow.
#
# Usage:
#   powershell.exe -ExecutionPolicy Bypass -File check-ff-windows.ps1
#
# Output:
#   ORPHAN_COUNT=<N>  — firefox processes with empty/N/A MainWindowTitle
#   LIVE_COUNT=<N>    — firefox processes with a visible window
#   TOTAL=<N>         — total firefox.exe processes
#   (per-PID detail lines)
#
# Orphan PID listing (for selective kill):
#   ORPHAN_PID=<id>
# Live window listing (to avoid killing real browsers):
#   LIVE:PID=<id> TITLE=<title>

$procs = Get-Process firefox -ErrorAction SilentlyContinue
$orphanCount = 0
$liveCount = 0
$report = @()

foreach ($p in $procs) {
    $title = $p.MainWindowTitle
    if ($title -ne '' -and $title -ne 'N/A') {
        $truncated = if ($title.Length -gt 80) { $title.Substring(0, 80) + '...' } else { $title }
        $report += "LIVE:PID=$($p.Id) TITLE=$truncated"
        $liveCount++
    } else {
        $report += "ORPHAN:PID=$($p.Id)"
        $orphanCount++
    }
}

Write-Output "ORPHAN_COUNT=$orphanCount"
Write-Output "LIVE_COUNT=$liveCount"
Write-Output "TOTAL=$($procs.Count)"
if ($report.Count -gt 0) {
    Write-Output "---"
    $report | ForEach-Object { Write-Output $_ }
}
