#define MyAppName "Student Support System"
#define MyAppVersion "1.2.0"
#define MyAppExeName "StudentSupportSystem.exe"
#define MyAppSourceDir "..\dist\StudentSupportSystem"

[Setup]
AppId={{E941EF1D-4D33-43BD-9A40-107F9886B1E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={localappdata}\Programs\StudentSupportSystem
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=StudentSupportSystem-1.2.0-Setup
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=PREREQUISITES_V1.2.txt
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình Desktop"; GroupDescription: "Tùy chọn bổ sung:"; Flags: unchecked

[Icons]
Name: "{group}\Student Support System"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Gỡ cài đặt Student Support System"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Student Support System"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Khởi chạy Student Support System"; Flags: nowait postinstall skipifsilent

[Code]
function IsOdbcDriver18Installed: Boolean;
var
  DriverState: String;
begin
  Result :=
    (RegQueryStringValue(HKLM64,
      'SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers',
      'ODBC Driver 18 for SQL Server', DriverState) and
      (CompareText(DriverState, 'Installed') = 0)) or
    (RegQueryStringValue(HKLM32,
      'SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers',
      'ODBC Driver 18 for SQL Server', DriverState) and
      (CompareText(DriverState, 'Installed') = 0));
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  if not IsOdbcDriver18Installed then
    MsgBox(
      'Không phát hiện Microsoft ODBC Driver 18 for SQL Server. ' +
      'Bạn vẫn có thể tiếp tục cài đặt, nhưng phải cài driver trước khi chạy ứng dụng.',
      mbInformation, MB_OK);
end;
