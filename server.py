from flask import Flask, jsonify
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)  # allow all origins

def get_systemd_services():
    # List all services
    all_services = subprocess.run(
        ['systemctl', 'list-units', '--type=service', '--all', '--no-legend'],
        capture_output=True,
        text=True
    ).stdout.strip().splitlines()

    service_names = [line.split()[0] for line in all_services]
    services = []
    for svc in service_names:
        # Get systemctl info
        result = subprocess.run(
            ['systemctl', 'show', svc, '--no-page'],
            capture_output=True,
            text=True
        )
        info = {}
        for line in result.stdout.splitlines():
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            info[k] = v

        # CPU, memory, threads via ps (ignore errors)
        cpu = mem = threads = 0
        try:
            proc_name = svc.replace('.service', '')
            ps_result = subprocess.run(
                ['ps', '-C', proc_name, '-o', 'pcpu,pmem,nlwp', '--no-headers'],
                capture_output=True,
                text=True
            ).stdout.strip()
            if ps_result:
                for line in ps_result.splitlines():
                    parts = line.split()
                    if len(parts) == 3:
                        cpu += float(parts[0])
                        mem += float(parts[1])
                        threads += int(parts[2])
        except:
            pass

        # Restart count: fallback to 0 if not available
        restart_count = 0
        try:
            restart_count = int(info.get("NRestarts", 0))
        except ValueError:
            pass
        # Optional: you can compute "real" restart count using journalctl, but this is heavier
        services.append({
            "name": svc,
            "status": info.get("ActiveState", "unknown"),
            "sub": info.get("SubState", ""),
            "cpu": round(cpu, 2),
            "memory": round(mem, 2),
            "threads": threads,
            "uptime": info.get("ActiveEnterTimestamp", ""),
            "restart_count": restart_count,
        })

    return services

@app.route("/api/services")
def services_endpoint():
    return jsonify(get_systemd_services())
def get_service_info(service_name: str):
    try:
        # 1️⃣ Get systemctl info
        result = subprocess.check_output(
            ["systemctl", "show", service_name, "--no-page"],
            text=True
        )

        data = {}
        for line in result.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k] = v

        # 2️⃣ Memory in MB safely
        memory_str = data.get("MemoryCurrent", "0")
        try:
            memory_bytes = int(memory_str)
        except ValueError:
            memory_bytes = 0
        memory_mb = round(memory_bytes / (1024 * 1024), 2)

        # 3️⃣ CPU usage safely
        cpu_str = data.get("CPUUsageNSec", "0")
        try:
            cpu_nsec = int(cpu_str)
        except ValueError:
            cpu_nsec = 0
        cpu_sec = round(cpu_nsec / 1_000_000_000, 2)

        # 4️⃣ Threads from `ps`
        threads = 0
        proc_name = service_name.replace(".service", "")
        try:
            ps_result = subprocess.run(
                ["ps", "-C", proc_name, "-o", "nlwp", "--no-headers"],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            if ps_result:
                for line in ps_result.splitlines():
                    try:
                        threads += int(line.strip())
                    except ValueError:
                        continue
        except subprocess.CalledProcessError:
            threads = 0

        return {
            "name": service_name,
            "status": data.get("ActiveState", "UNKNOWN").upper(),
            "sub": data.get("SubState", "UNKNOWN").upper(),
            "uptime": data.get("ActiveEnterTimestamp", "N/A"),
            "restart_count": int(data.get("NRestarts", 0)),
            "cpu": f"{cpu_sec} %",
            "memory": f"{memory_mb} MB",
            "threads": threads,
        }

    except subprocess.CalledProcessError:
        return {
            "name": service_name,
            "status": "FAILED",
            "sub": "FAILED",
            "uptime": "N/A",
            "restart_count": 0,
            "cpu": "0 %",
            "memory": "0 MB",
            "threads": 0,
        }

@app.route("/api/service/<service_name>", methods=["GET"])
def service_detail(service_name):
    print(f"Service found: {service_name}")
    service = get_service_info(service_name)

    if not service:
        return jsonify({"error": "Service not foundw"}), 404

    return jsonify(service)


@app.route("/api/service/<service_name>/logs")
def service_logs(service_name):
    try:
        # Grab the last 100 lines of the journal for this service
        result = subprocess.run(
            ["journalctl", "-u", service_name, "-n", "100", "--no-pager", "--output=short-iso"],
            capture_output=True,
            text=True,
            check=True
        )

        # split lines into a list
        logs = result.stdout.strip().splitlines()

        return jsonify({
            "service": service_name,
            "logs": logs
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            "service": service_name,
            "logs": [],
            "error": str(e)
        }), 500

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


@app.route("/api/service/<service_name>/<action>", methods=['POST'])
def service_action(service_name,action):
    print("Service action called")
    if not service_name:
        print("no service")
        return jsonify({"success": False, "error": "Service name is required"}), 400

    valid_actions = ['start', 'stop', 'restart', 'reload', 'enable', 'disable']
    if action not in valid_actions:
        print(f"success")
        return jsonify({"success": False, "error": f"Invalid action '{action}'"}), 400

    result = run_systemctl(action, service_name)
    return jsonify(result)

# ----------------------------
# Get current monitor settings
# ----------------------------
@app.route("/api/monitor-settings", methods=["GET"])
def fetch_monitor_settings():
    settings = get_monitor_settings()
    if settings:
        return jsonify({"success": True, "data": settings})
    return jsonify({"success": False, "message": "No settings found"}), 404

# ----------------------------
# Update monitor settings
# ----------------------------
@app.route("/api/monitor-settings", methods=["POST"])
def save_monitor_settings():
    data = request.json or {}
    
    upsert_monitor_settings(
        auto_restart=data.get("auto_restart"),
        alerts_enabled=data.get("alerts_enabled"),
        whatsapp_enabled=data.get("whatsapp_enabled"),
        whatsapp_number=data.get("whatsapp_number"),
        email_enabled=data.get("email_enabled"),
        primary_email=data.get("primary_email"),
        secondary_email=data.get("secondary_email")
    )
    
    return jsonify({"success": True, "message": "Settings saved"})

# ----------------------------
# List all monitored services
# ----------------------------
@app.route("/api/monitored-services", methods=["GET"])
def list_services():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_services ORDER BY service_name")
    rows = cursor.fetchall()
    keys = [desc[0] for desc in cursor.description]
    services = [dict(zip(keys, row)) for row in rows]
    conn.close()
    return jsonify({"success": True, "data": services})


# ----------------------------
# Add a new service
# ----------------------------
@app.route("/api/monitored-services", methods=["POST"])
def add_service():
    data = request.json or {}
    name = data.get("service_name")
    notify = data.get("notify_on_fail", 1)

    if not name:
        return jsonify({"success": False, "message": "service_name is required"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO monitored_services (service_name, notify_on_fail)
            VALUES (?, ?)
        """, (name, 1 if notify else 0))
        conn.commit()
        service_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": str(e)}), 400

    conn.close()
    return jsonify({"success": True, "id": service_id})


# ----------------------------
# Delete a service
# ----------------------------
@app.route("/api/monitored-services/<int:service_id>", methods=["DELETE"])
def delete_service(service_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM monitored_services WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Service {service_id} deleted"})


if __name__ == "__main__":
    app.run(debug=True)
