#define ProductVersion "0.1.0"
#define ProductGuid "{3699C4A8-8612-4F01-BB26-F014797A9CBE}"
#ifndef PayloadIncludes
  #error Build with packaging/build-installer.py to verify and enumerate the approved payload.
#endif

[Setup]
AppId={{3699C4A8-8612-4F01-BB26-F014797A9CBE}
AppName=HybridSign
AppVersion={#ProductVersion}
VersionInfoVersion=0.1.0.0
VersionInfoDescription=HybridSign Setup
AppPublisher=HybridSign thesis project
DefaultDirName={localappdata}\Programs\HybridSign
DefaultGroupName=HybridSign
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
AllowUNCPath=no
AllowNetworkDrive=no
AllowRootDirectory=no
SetupIconFile=..\logobig.ico
UninstallDisplayIcon={app}\HybridSign.exe
InfoBeforeFile=INSTALLER-INFO.txt
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=no
RestartApplications=no
SetupMutex=Local\HybridSign-3699C4A8-Setup
UninstallLogMode=append
OutputBaseFilename=HybridSign-Setup-Phase4C2B-win-x64

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; Flags: unchecked

[Files]
#include PayloadIncludes + "\files.iss"

[Icons]
Name: "{userprograms}\HybridSign\HybridSign"; Filename: "{app}\HybridSign.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\HybridSign"; Filename: "{app}\HybridSign.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#ProductGuid}_is1';
  WebViewKey = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  CloseMessage = 'HybridSign is open. Let any signing operation finish, then close HybridSign normally and try again.';
  ReparsePoint = $400;
  DirectoryAttribute = $10;
  InvalidAttributes = $FFFFFFFF;
  InvalidHandle = -1;

type
  // PROCESSENTRY32W as returned to the 32-bit Inno Setup engine.
  ProcessEntry = record
    Size, Usage, ProcessId, DefaultHeapId, ModuleId, Threads, ParentId: Cardinal;
    BasePriority: LongInt;
    Flags: Cardinal;
    ExeName: array[0..259] of Char;
  end;

var
  // Inno Setup 6.7.1 uses a 32-bit Setup engine in 64-bit install mode.
  LaunchGuard: LongInt;

function Attributes(Path: String): Cardinal;
  external 'GetFileAttributesW@kernel32.dll stdcall';
function DriveType(Path: String): Cardinal;
  external 'GetDriveTypeW@kernel32.dll stdcall';
function OpenLaunchGuard(Path: String; Access, Share: Cardinal; Security: LongInt;
  Creation, Flags: Cardinal; Template: LongInt): LongInt;
  external 'CreateFileW@kernel32.dll stdcall';
function CloseHandle(Handle: LongInt): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';
function ProcessSnapshot(Flags, ProcessId: Cardinal): LongInt;
  external 'CreateToolhelp32Snapshot@kernel32.dll stdcall';
function FirstProcess(Snapshot: LongInt; var Entry: ProcessEntry): Boolean;
  external 'Process32FirstW@kernel32.dll stdcall';
function NextProcess(Snapshot: LongInt; var Entry: ProcessEntry): Boolean;
  external 'Process32NextW@kernel32.dll stdcall';

function BlockLaunchDuringServicing: Boolean;
var
  ErrorCode: Integer;
begin
  // Existing mapped executable images cannot be opened for write access.
  // Share deletion so Uninstall can unlink its own executable while this
  // handle continues to deny execute/read opens until the operation finishes.
  LaunchGuard := OpenLaunchGuard(ExpandConstant('{app}\HybridSign.exe'),
    $40000000, 4, 0, 3, $00200080, 0);
  Result := LaunchGuard <> InvalidHandle;
  if not Result then begin
    ErrorCode := DLLGetLastError;
    Result := (ErrorCode = 2) or (ErrorCode = 3);
  end;
end;

procedure ReleaseLaunchGuard;
begin
  if (LaunchGuard <> 0) and (LaunchGuard <> InvalidHandle) then begin
    CloseHandle(LaunchGuard);
    LaunchGuard := 0;
  end;
end;

procedure DeinitializeSetup;
begin
  ReleaseLaunchGuard;
end;

procedure DeinitializeUninstall;
begin
  ReleaseLaunchGuard;
end;

function AppCanBeServiced: Boolean;
var
  Snapshot, I: LongInt;
  Entry: ProcessEntry;
  Name: String;
begin
  Result := False;
  Snapshot := ProcessSnapshot(2, 0);  // TH32CS_SNAPPROCESS
  if Snapshot = InvalidHandle then Exit;
  try
    Entry.Size := 556;
    if not FirstProcess(Snapshot, Entry) then Exit;
    repeat
      Name := '';
      for I := 0 to 259 do begin
        if Entry.ExeName[I] = #0 then Break;
        Name := Name + Entry.ExeName[I];
      end;
      if CompareText(Name, 'HybridSign.exe') = 0 then Exit;
    until not NextProcess(Snapshot, Entry);
    Result := DLLGetLastError = 18;  // ERROR_NO_MORE_FILES
  finally
    CloseHandle(Snapshot);
  end;
end;

function IsWebViewVersion(Version: String): Boolean;
var
  I, Groups, Digits: Integer;
begin
  Result := False;
  Groups := 0;
  Digits := 0;
  for I := 1 to Length(Version) do begin
    if (Version[I] >= '0') and (Version[I] <= '9') then
      Digits := Digits + 1
    else if (Version[I] = '.') and (Digits > 0) then begin
      Groups := Groups + 1;
      Digits := 0;
    end else
      Exit;
  end;
  if (Groups = 3) and (Digits > 0) then
    Result := StrToIntDef(Copy(Version, 1, Pos('.', Version) - 1), 0) >= 111;
end;

function InitializeSetup: Boolean;
var
  Release: Cardinal;
  Version: String;
begin
  Result := False;
  if not RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release)
    or (Release < 394802) then begin
    SuppressibleMsgBox('HybridSign needs Microsoft .NET Framework 4.6.2 or later.' + #13#10 +
      'Install a supported .NET Framework runtime from Microsoft, then run Setup again.' + #13#10 +
      'https://dotnet.microsoft.com/download/dotnet-framework', mbError, MB_OK, IDOK);
    Exit;
  end;
  if not ((RegQueryStringValue(HKLM32, 'SOFTWARE\' + WebViewKey, 'pv', Version) and IsWebViewVersion(Version)) or
          (RegQueryStringValue(HKCU, 'SOFTWARE\' + WebViewKey, 'pv', Version) and IsWebViewVersion(Version))) then begin
    SuppressibleMsgBox('HybridSign needs Microsoft Edge WebView2 Evergreen Runtime 111 or later.' + #13#10 +
      'Install the Evergreen Runtime from Microsoft, then run Setup again.' + #13#10 +
      'https://developer.microsoft.com/microsoft-edge/webview2/', mbError, MB_OK, IDOK);
    Exit;
  end;
  Result := True;
end;

function SafeDirectoryTree(Path: String): Boolean;
var
  Info: Cardinal;
  Parent: String;
  ErrorCode: Integer;
begin
  Result := False;
  repeat
    Info := Attributes(Path);
    if Info = InvalidAttributes then begin
      ErrorCode := DLLGetLastError;
      if (ErrorCode <> 2) and (ErrorCode <> 3) then Exit;
    end else if ((Info and ReparsePoint) <> 0) or ((Info and DirectoryAttribute) = 0) then
      Exit;
    Parent := ExtractFileDir(Path);
    if CompareText(Parent, Path) = 0 then Break;
    Path := Parent;
  until Path = '';
  Result := True;
end;

function UnoccupiedPath(Path: String): Boolean;
var
  FindRec: TFindRec;
  ErrorCode: Integer;
begin
  Result := False;
  if Attributes(Path) = InvalidAttributes then begin
    ErrorCode := DLLGetLastError;
    Result := (ErrorCode = 2) or (ErrorCode = 3);
    Exit;
  end;
  if not FindFirst(AddBackslash(Path) + '*', FindRec) then Exit;
  try
    repeat
      if (FindRec.Name <> '.') and (FindRec.Name <> '..') then Exit;
    until not FindNext(FindRec);
    Result := True;
  finally
    FindClose(FindRec);
  end;
end;

function MatchesOwnedFile(Root, RelativeName, Sha256: String): Boolean;
var
  Path: String;
  Info: Cardinal;
  ErrorCode: Integer;
begin
  Result := False;
  Path := AddBackslash(Root) + RelativeName;
  if not SafeDirectoryTree(ExtractFileDir(Path)) then Exit;
  Info := Attributes(Path);
  if Info = InvalidAttributes then begin
    ErrorCode := DLLGetLastError;
    Result := (ErrorCode = 2) or (ErrorCode = 3);
    Exit;
  end;
  if (Info and (ReparsePoint or DirectoryAttribute)) <> 0 then Exit;
  try
    Result := CompareText(GetSHA256OfFile(Path), Sha256) = 0;
  except
    Log('Could not read a managed payload file.');
  end;
end;

#include PayloadIncludes + "\ownership.iss"

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Target, Previous, Version: String;
begin
  Result := CloseMessage;
  if not AppCanBeServiced then Exit;
  Target := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  Result := 'Choose a dedicated folder on a fixed local drive. The folder path must not go through a link or junction.';
  if (DriveType(AddBackslash(ExtractFileDrive(Target))) <> 3) or not SafeDirectoryTree(Target) then Exit;
  if RegKeyExists(HKCU64, UninstallKey) then begin
    Result := 'A registered HybridSign installation already exists. Use its original location and release, or uninstall it first.';
    if not RegQueryStringValue(HKCU64, UninstallKey, 'Inno Setup: App Path', Previous) or
       not RegQueryStringValue(HKCU64, UninstallKey, 'DisplayVersion', Version) or
       (CompareText(Target, RemoveBackslashUnlessRoot(Previous)) <> 0) or (Version <> '{#ProductVersion}') then Exit;
    Result := 'Setup stopped because it could not verify the installed files. Keep your vaults and PDFs in a separate folder.';
    if not PayloadIsSafe(Target) then Exit;
  end else begin
    Result := 'Choose a new or empty folder. Setup leaves existing files untouched.';
    if not UnoccupiedPath(Target) then Exit;
    Result := 'A HybridSign shortcut already exists. Review or move the existing shortcut before installing.';
    if FileExists(ExpandConstant('{userprograms}\HybridSign\HybridSign.lnk')) or
       (WizardIsTaskSelected('desktopicon') and FileExists(ExpandConstant('{userdesktop}\HybridSign.lnk'))) then Exit;
  end;
  Result := '';
end;

procedure CurStepChanged(Step: TSetupStep);
var
  Message: String;
  NeedsRestart: Boolean;
begin
  if Step = ssInstall then begin
    NeedsRestart := False;
    Message := PrepareToInstall(NeedsRestart);
    if (Message = '') and not BlockLaunchDuringServicing then
      Message := CloseMessage;
    if Message <> '' then begin
      SuppressibleMsgBox(Message, mbError, MB_OK, IDOK);
      Abort;
    end;
  end;
end;

function CanUninstall: Boolean;
begin
  Result := False;
  if not AppCanBeServiced then begin
    SuppressibleMsgBox(CloseMessage, mbError, MB_OK, IDOK);
    Exit;
  end;
  if not PayloadIsSafe(ExpandConstant('{app}')) then begin
    SuppressibleMsgBox('Uninstall stopped because it could not verify the installed files. Your files were left in place.',
      mbError, MB_OK, IDOK);
    Exit;
  end;
  Result := True;
end;

function InitializeUninstall: Boolean;
begin
  Result := CanUninstall;
end;

procedure CurUninstallStepChanged(Step: TUninstallStep);
begin
  if Step = usUninstall then begin
    if not CanUninstall then Abort;
    if not BlockLaunchDuringServicing then begin
      SuppressibleMsgBox(CloseMessage, mbError, MB_OK, IDOK);
      Abort;
    end;
  end;
end;
