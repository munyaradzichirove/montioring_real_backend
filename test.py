
import subprocess
def service_exists(service_name: str):
    try:
        subprocess.check_output(
            ["systemctl", "status", service_name],
            stderr=subprocess.STDOUT,
            text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
print(service_exists("alsa-restore"))