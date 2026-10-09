$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Security
    $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $bytes = [Convert]::FromBase64String($request.data)
    $scope = [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    $entropy = [System.Text.Encoding]::UTF8.GetBytes('chrysalis-provider-credentials-v1')
    if ($request.operation -eq 'protect') {
        $result = [System.Security.Cryptography.ProtectedData]::Protect($bytes, $entropy, $scope)
    } elseif ($request.operation -eq 'unprotect') {
        $result = [System.Security.Cryptography.ProtectedData]::Unprotect($bytes, $entropy, $scope)
    } else { throw 'unsupported' }
    [Console]::Out.Write([Convert]::ToBase64String($result))
} catch {
    [Console]::Error.Write('protected_store_unavailable')
    exit 1
}
