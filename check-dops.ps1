  $proj   = "C:\test-app"
  $depDir = Join-Path $proj "deployment"
  $dep    = Join-Path $depDir "localhost.dep"

  $depXml = Get-Content $dep -Raw
  $ops = [regex]::Matches($depXml,'operationName="([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
  "Deployment 'localhost' includes: $($ops -join ', ')`n"

  foreach ($op in $ops) {
    $dop = Join-Path $depDir $op
    "==== $op ===="
    if (-not (Test-Path $dop)) { "   MISSING .dop FILE <<< PROBLEM`n"; continue }
    $x = Get-Content $dop -Raw
    foreach ($m in [regex]::Matches($x,'<(\w+)[^>]*?href="([^"]+)"')) {
      $tag = $m.Groups[1].Value
      $rel = ($m.Groups[2].Value -split '#')[0]
      if ([string]::IsNullOrEmpty($rel)) { "   $tag -> '' EMPTY PATH (=folder) <<< PROBLEM"; continue }
      $full = [System.IO.Path]::GetFullPath((Join-Path $depDir $rel))
      if     (Test-Path $full -PathType Leaf)      { "   $tag -> $rel  = OK file" }
      elseif (Test-Path $full -PathType Container) { "   $tag -> $rel  <<< FOLDER (PROBLEM)" }
      else                                          { "   $tag -> $rel  <<< MISSING (PROBLEM)" }
    }
    ""
  }
