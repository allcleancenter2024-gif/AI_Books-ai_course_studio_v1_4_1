param([string]$Time = '16:00')
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$runner = Join-Path $root 'scripts\run_weekly_research.py'
if (!(Test-Path $python)) { throw 'Project virtual environment is required.' }
$action = New-ScheduledTaskAction -Execute $python -Argument ('"{0}"' -f $runner) -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'AI-Course-Studio-Weekly-Official-Research' -Action $action -Trigger $trigger -Settings $settings -Description 'Studio-owned official release note research; Saturday 16:00; catch-up when available.' -Force
