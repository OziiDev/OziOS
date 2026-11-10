# First-logon setup for the OziOS Windows guest.
# Makes the guest reachable over RDP, lets single programs be opened as
# RemoteApp windows, and trims the parts of Windows nobody asked for.
$ErrorActionPreference = 'Continue'
Start-Transcript -Path 'C:\ozi-setup.log' -Force | Out-Null

function Set-Reg($Path, $Name, $Value, $Type = 'DWord') {
    if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
    Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Type -Force
}

# Remote Desktop, and RemoteApp for any program rather than an allow list.
Set-Reg 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server' 'fDenyTSConnections' 0
Set-Reg 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Terminal Server\TSAppAllowList' 'fDisabledAllowList' 1
Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'

# Files from the Linux side arrive as \\tsclient\home. Treat that as local
# intranet so programs start without a security prompt every time.
Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains\tsclient' 'file' 1

# Guest drivers and agent, if the virtio CD is attached.
foreach ($drive in 'D', 'E', 'F', 'G', 'H') {
    $tools = "${drive}:\virtio-win-guest-tools.exe"
    if (Test-Path $tools) {
        Start-Process $tools -ArgumentList '/install', '/passive', '/norestart' -Wait
        break
    }
}

# The guest is headless most of the time; it must not go to sleep on its own.
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /hibernate off

# Telemetry, ads and suggestions.
Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection' 'AllowTelemetry' 0
Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableWindowsConsumerFeatures' 1
Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search' 'AllowCortana' 0
Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo' 'DisabledByGroupPolicy' 1
Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager' 'SilentInstalledAppsEnabled' 0
Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager' 'SystemPaneSuggestionsEnabled' 0
Stop-Service DiagTrack -Force
Set-Service DiagTrack -StartupType Disabled

# Bundled apps. The Store, the app installer and the runtimes stay, so
# anything removed here can be put back.
$bloat = @(
    'Microsoft.3DBuilder', 'Microsoft.BingNews', 'Microsoft.BingWeather', 'Microsoft.GetHelp',
    'Microsoft.Getstarted', 'Microsoft.Microsoft3DViewer', 'Microsoft.MicrosoftOfficeHub',
    'Microsoft.MicrosoftSolitaireCollection', 'Microsoft.MixedReality.Portal', 'Microsoft.Office.OneNote',
    'Microsoft.People', 'Microsoft.SkypeApp', 'Microsoft.Wallet', 'Microsoft.WindowsFeedbackHub',
    'Microsoft.WindowsMaps', 'Microsoft.YourPhone', 'Microsoft.ZuneMusic', 'Microsoft.ZuneVideo',
    'Microsoft.549981C3F5F10', 'MicrosoftTeams', 'Clipchamp.Clipchamp', 'Microsoft.Todos',
    'Microsoft.PowerAutomateDesktop', 'MicrosoftCorporationII.QuickAssist'
)
foreach ($name in $bloat) {
    Get-AppxPackage -AllUsers -Name $name | Remove-AppxPackage -AllUsers
    Get-AppxProvisionedPackage -Online | Where-Object DisplayName -eq $name | Remove-AppxProvisionedPackage -Online | Out-Null
}

$onedrive = "$env:SystemRoot\SysWOW64\OneDriveSetup.exe"
if (-not (Test-Path $onedrive)) { $onedrive = "$env:SystemRoot\System32\OneDriveSetup.exe" }
if (Test-Path $onedrive) { Start-Process $onedrive -ArgumentList '/uninstall' -Wait }

Set-Content -Path 'C:\ozi-ready.txt' -Value (Get-Date -Format o)
Stop-Transcript | Out-Null
Restart-Computer -Force
