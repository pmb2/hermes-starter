import subprocess
from datetime import datetime, timedelta
from pathlib import Path

log = Path(r"${USER_HOME}\AppData\Local\hermes\logs\schedule-bounce.log")
script = r"${USER_HOME}\AppData\Local\hermes\scripts\manual_gw_bounce.cmd"
task = "HermesManualGatewayRestart"

log.write_text(f"{datetime.now().isoformat()} scheduling {task}\n", encoding="utf-8")

# Delete prior task if any
subprocess.run(
    ["schtasks", "/Delete", "/TN", task, "/F"],
    capture_output=True,
    text=True,
)

# Schedule 1 minute from now (local time)
run_at = datetime.now() + timedelta(minutes=1)
# schtasks wants HH:MM
when = run_at.strftime("%H:%M")
date = run_at.strftime("%m/%d/%Y")

create = subprocess.run(
    [
        "schtasks",
        "/Create",
        "/TN",
        task,
        "/TR",
        script,
        "/SC",
        "ONCE",
        "/ST",
        when,
        "/SD",
        date,
        "/RL",
        "HIGHEST",
        "/F",
    ],
    capture_output=True,
    text=True,
)
log.write_text(
    log.read_text(encoding="utf-8")
    + f"create rc={create.returncode}\n{create.stdout}\n{create.stderr}\n"
    + f"scheduled for {date} {when}\n",
    encoding="utf-8",
)

# Also try immediate run (independent of one-shot clock)
run = subprocess.run(["schtasks", "/Run", "/TN", task], capture_output=True, text=True)
log.write_text(
    log.read_text(encoding="utf-8") + f"run rc={run.returncode}\n{run.stdout}\n{run.stderr}\n",
    encoding="utf-8",
)
print("create", create.returncode, create.stdout.strip() or create.stderr.strip())
print("run", run.returncode, run.stdout.strip() or run.stderr.strip())
print("when", date, when)
