#define MyAppName "Home Unit Calculator"
#define MyAppExeName "HomeUnitCalculator.exe"
#define MyAppPublisher "Home Unit Calculator"
#define MyAppId "{{F3D62E60-7E4D-4B6F-8D54-33A17DCB9BA2}}"

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "0.0.0.0"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=HomeUnitCalculator-Setup-{#MyAppVersion}
OutputDir=dist\installer
SetupIconFile=icons\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoTextVersion={#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\HomeUnitCalculator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function GetUninstallStringRoot(const RootKey: Integer): string;
var
  S: string;
begin
  S := '';
  if RegQueryStringValue(RootKey, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}_is1', 'UninstallString', S) then
    Result := S
  else
    Result := '';
end;

function GetUninstallString(): string;
begin
  Result := GetUninstallStringRoot(HKLM);
  if Result = '' then
    Result := GetUninstallStringRoot(HKCU);
end;

function ExtractUninstallExe(const UninstallString: string): string;
var
  S: string;
  P: Integer;
begin
  S := UninstallString;
  if (Length(S) >= 1) and (S[1] = '"') then begin
    Delete(S, 1, 1);
    P := Pos('"', S);
    if P > 0 then
      Result := Copy(S, 1, P - 1)
    else
      Result := S;
  end else begin
    P := Pos(' ', S);
    if P > 0 then
      Result := Copy(S, 1, P - 1)
    else
      Result := S;
  end;
end;

function InitializeSetup(): Boolean;
var
  UninstallString: string;
  UninstallExe: string;
  ResultCode: Integer;
begin
  Result := True;
  UninstallString := GetUninstallString();
  if UninstallString <> '' then begin
    UninstallExe := ExtractUninstallExe(UninstallString);
    if FileExists(UninstallExe) then
      Exec(UninstallExe, '/VERYSILENT /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

