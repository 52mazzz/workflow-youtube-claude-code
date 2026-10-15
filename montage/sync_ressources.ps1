# sync_ressources.ps1 - copie entre deux PC les medias qui ne passent pas par git : Whisper surtout
# (musiques et sfx sont maintenant dans git ; ce script sait encore les copier par cle USB si besoin). Ne supprime jamais rien, n'ecrase pas un fichier plus recent.
#
#   .\montage\sync_ressources.ps1 export E:\        sur le PC source : vers une cle USB, un dossier Drive ou un partage reseau
#   .\montage\sync_ressources.ps1 import E:\        sur le PC cible  : depuis cette cle / ce dossier
#   .\montage\sync_ressources.ps1 whisper           sur le PC cible  : telecharge Whisper depuis les sources officielles
#                                                   (whisper.cpp v1.9.2 sur GitHub + modele sur Hugging Face, ~555 Mo)
#
# Option : -Quoi musiques,sfx   (par defaut : musiques,sfx,whisper ; pour export/import seulement)
# Les musiques perso ne sont pas dans la copie publique (voir 04_RESSOURCES/LICENCES.md).
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateSet('export', 'import', 'whisper')][string]$Action,
    [Parameter(Position = 1)][string]$Chemin,
    [string[]]$Quoi = @('musiques', 'sfx', 'whisper')
)

$ErrorActionPreference = 'Stop'
$M = $PSScriptRoot   # le dossier montage/ du depot
$dossiers = @{
    musiques = '04_RESSOURCES\musiques'
    sfx      = '04_RESSOURCES\sfx'
    whisper  = '08_HYPERFRAMES\.whisper'
}
$MODELE = 'ggml-large-v3-turbo-q5_0.bin'
$URL_MODELE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODELE"
$URL_BIN = 'https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.2/whisper-bin-x64.zip'

function Copier($de, $vers, $nom) {
    if (-not (Test-Path $de)) { Write-Output ("{0,-9} absent chez la source : {1}" -f $nom, $de); return }
    New-Item -ItemType Directory -Force $vers | Out-Null
    # /E sous-dossiers, /XO ne remplace pas un fichier plus recent, jamais de /MIR ni /PURGE (rien n'est supprime)
    robocopy $de $vers /E /XO /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy a echoue pour $nom (code $LASTEXITCODE)" }
    $n = (Get-ChildItem $vers -Recurse -File -Force | Measure-Object).Count
    Write-Output ("{0,-9} ok : {1} fichiers dans {2}" -f $nom, $n, $vers)
}

if ($Action -eq 'whisper') {
    $ProgressPreference = 'SilentlyContinue'
    $w = Join-Path $M $dossiers.whisper
    New-Item -ItemType Directory -Force $w | Out-Null
    $modele = Join-Path $w $MODELE
    if (Test-Path $modele) { Write-Output "modele deja present : $modele" }
    else {
        Write-Output "telechargement du modele (547 Mo) depuis Hugging Face..."
        Invoke-WebRequest -Uri $URL_MODELE -OutFile "$modele.part" -UseBasicParsing
        Move-Item "$modele.part" $modele
    }
    $exe = Join-Path $w 'v1.9.2\Release\whisper-cli.exe'
    if (Test-Path $exe) { Write-Output "whisper-cli deja present : $exe" }
    else {
        Write-Output "telechargement de whisper.cpp v1.9.2 (8 Mo) depuis GitHub..."
        $zip = Join-Path $env:TEMP 'whisper-bin-x64.zip'
        Invoke-WebRequest -Uri $URL_BIN -OutFile $zip -UseBasicParsing
        Expand-Archive -Path $zip -DestinationPath (Join-Path $w 'v1.9.2') -Force
        Remove-Item $zip
        if (-not (Test-Path $exe)) { throw "whisper-cli.exe introuvable apres extraction : $exe" }
    }
    Write-Output "Whisper pret."
    return
}

if (-not $Chemin) { throw "Indique le dossier de transfert, ex. : .\montage\sync_ressources.ps1 $Action E:\" }
$transfert = Join-Path $Chemin 'TSAR_ressources'
foreach ($k in $Quoi) {
    if (-not $dossiers.ContainsKey($k)) { throw "inconnu : $k (choix : musiques, sfx, whisper)" }
    $local = Join-Path $M $dossiers[$k]
    $ext = Join-Path $transfert $k
    if ($Action -eq 'export') { Copier $local $ext $k } else { Copier $ext $local $k }
}
