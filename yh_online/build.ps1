<#
.SYNOPSIS
  编译脚本
#>

# 配置
$AppName = "yh-online"
$Version = "202504060"
$OutputDir = "build"
$Platforms = @("windows", "linux", "darwin", "freebsd", "android")
$Architectures = @("386", "amd64", "arm64")
$WindowsExt = ".exe"

# 初始化
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Remove-Item -Path $OutputDir -Recurse -ErrorAction Ignore
New-Item -ItemType Directory -Path $OutputDir | Out-Null

# 静默编译函数
function Build-Platform {
    param ($OS, $ARCH)
    
    # 自动跳过不支持的组合
    if ($OS -eq "darwin" -and $ARCH -eq "386") { return }
    if ($ARCH -eq "arm" -and $OS -ne "android") { return }

    # 设置输出路径
    $Ext = if ($OS -eq "windows") { $WindowsExt } else { "" }
    $OutputFile = "${AppName}_${Version}_$(
        if ($OS -eq "darwin") { if ($ARCH -eq "arm64") { "macOS_M1" } else { "macOS_Intel" } }
        elseif ($OS -eq "android") { if ($ARCH -eq "arm") { "Android_armv7" } else { "Android_$ARCH" } }
        else { "${OS}_$ARCH" }
    )$Ext"
    
    # 执行编译
    $env:CGO_ENABLED = "0"
    $env:GOOS = $OS
    $env:GOARCH = if ($ARCH -eq "arm") { "arm" } else { $ARCH }
    if ($ARCH -eq "arm") { $env:GOARM = "7" }
    
    go build -o "$OutputDir\$OutputFile" main.go 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "编译失败: ${OS}/${ARCH}" }
}

# 执行编译
foreach ($os in $Platforms) {
    foreach ($arch in $Architectures) { Build-Platform $os $arch }
    if ($os -eq "android") { Build-Platform $os "arm" }  # 单独处理Android ARMv7
}

# 生成校验文件
Get-ChildItem -Path $OutputDir | ForEach-Object {
    "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash) *$($_.Name)" |
        Out-File "$OutputDir\checksums.sha256" -Append -Encoding UTF8
}