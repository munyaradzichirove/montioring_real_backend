
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

# logs = get_service_logs("accounts-daemon.service", lines=20)
# for line in logs:
#     print(line)




def run_systemctl(command: str, service_name: str):
    """Run a systemctl command safely and return status + output."""
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', command, service_name],
            capture_output=True,
            text=True,
            check=True
        )
        return {"success": True, "output": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        return {"success": False, "output": e.stderr.strip()}

def service_action():
    action="start"
    service_name="mariadb"
    if not service_name:
        return jsonify({"success": False, "error": "Service name is required"}), 400

    valid_actions = ['start', 'stop', 'restart', 'reload', 'enable', 'disable']
    if action not in valid_actions:
        return jsonify({"success": False, "error": f"Invalid action '{action}'"}), 400

    result = run_systemctl(action, service_name)
    return 

service_action()