
import subprocess

from typing import List

def get_service_logs(service_name: str, lines: int = 5) -> List[str]:
    try:
        result = subprocess.run(
            ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager", "--output=short"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        return [f"Failed to fetch logs for {service_name}"]

logs = get_service_logs("accounts-daemon.service", lines=20)
for line in logs:
    print(line)