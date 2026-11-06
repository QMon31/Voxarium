"""Avvio di un programma che deve restare acceso dopo la chiusura di chi lo avvia (usato da build_deploy.py per il
backend di Voxarium). Solo per gli strumenti di sviluppo: non fa parte del pacchetto del programma.

Su Windows un processo avviato da un altro resta nel suo "job": se il job chiude i processi alla sua fine (come fa
l'app Claude quando si chiude o si aggiorna), si chiude anche il backend. Il 05/11/2026 Voxarium, riavviato da
build_deploy.py lanciato da Claude, si è chiuso così alle 19:39 e la pausa della Modalità Eco ha smesso di funzionare.
"""
import os
import subprocess
from typing import List, Optional

DETACHED = 0x00000008
NEW_GROUP = 0x00000200
NO_WINDOW = 0x08000000
BREAKAWAY = 0x01000000   # CREATE_BREAKAWAY_FROM_JOB


def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def start_detached(args: List[str], cwd: str, log_path: str) -> str:
    """Avvia args in cwd con l'output aggiunto in fondo a log_path. Restituisce il modo usato:
    "breakaway" (fuori dal job), "wmi" (avviato da Windows, fuori dal job) o "popen" (come prima, resta nel job)."""
    if os.name != "nt":
        with open(log_path, "a", encoding="utf-8") as log:
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True, close_fds=True, creationflags=0)   # 0: fuori da Windows
        return "popen"

    # Prima WMI: CREATE_BREAKAWAY_FROM_JOB esce solo dal job più interno e il processo resta in quelli esterni
    # (provato il 06/11/2026: "breakaway" accettato ma processo ancora in un job), oppure è rifiutato (Accesso negato)
    pid = _start_with_wmi(args, cwd, log_path)
    if pid:
        return "wmi"

    with open(log_path, "a", encoding="utf-8") as log:
        try:
            subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=DETACHED | NEW_GROUP | NO_WINDOW | BREAKAWAY, close_fds=True)
            return "breakaway"
        except OSError:
            pass

    with open(log_path, "a", encoding="utf-8") as log:
        subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                         creationflags=DETACHED | NEW_GROUP | NO_WINDOW, close_fds=True)
    return "popen"


def _start_with_wmi(args: List[str], cwd: str, log_path: str) -> Optional[int]:
    """Win32_Process.Create: il processo lo crea il servizio WMI, con lo stesso utente e nella stessa sessione, ma
    fuori dal job di chi lo chiede. cmd /c serve solo a scrivere l'output nel registro; la finestra resta nascosta."""
    inner = subprocess.list2cmdline(args) + f' >> "{log_path}" 2>&1'
    command_line = f'cmd.exe /d /c "{inner}"'
    script = (
        "$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}; "
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{"
        f"CommandLine={_ps_quote(command_line)}; CurrentDirectory={_ps_quote(cwd)}; ProcessStartupInformation=$si}}; "
        "if ($r.ReturnValue -eq 0) { $r.ProcessId } else { 'ERR' + $r.ReturnValue }"
    )
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW)
        out = (res.stdout or "").strip().splitlines()
        return int(out[-1]) if out and out[-1].isdigit() else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
