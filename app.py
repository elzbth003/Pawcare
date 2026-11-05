import os
from flask import Flask, jsonify, render_template, request
import database

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Ensure database tables are created at startup
with app.app_context():
    database.init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    try:
        stats = database.get_stats()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "total_appointments": stats["total"]
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route("/api/stats", methods=["GET"])
def api_stats():
    try:
        stats = database.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve statistics: {str(e)}"}), 500


@app.route("/api/appointments", methods=["GET"])
def list_appointments():
    try:
        search = request.args.get("q", "")
        status = request.args.get("status", "")
        appointments = database.get_appointments(search=search, status=status)
        return jsonify(appointments), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch appointments: {str(e)}"}), 500


@app.route("/api/appointments/<int:appointment_id>", methods=["GET"])
def get_appointment(appointment_id):
    try:
        appointment = database.get_appointment_by_id(appointment_id)
        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404
        return jsonify(appointment), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch appointment: {str(e)}"}), 500


@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON body provided"}), 400

        required_fields = [
            "pet_name", "pet_type", "owner_name",
            "owner_phone", "appointment_date", "appointment_time", "service"
        ]
        missing = [field for field in required_fields if not data.get(field) or not str(data.get(field)).strip()]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        allowed_statuses = ["Scheduled", "Completed", "Cancelled"]
        if "status" in data and data["status"] not in allowed_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"}), 400

        new_appointment = database.create_appointment(data)
        return jsonify(new_appointment), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create appointment: {str(e)}"}), 500


@app.route("/api/appointments/<int:appointment_id>", methods=["PUT"])
def update_appointment(appointment_id):
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON body provided"}), 400

        required_fields = [
            "pet_name", "pet_type", "owner_name",
            "owner_phone", "appointment_date", "appointment_time", "service"
        ]
        missing = [field for field in required_fields if not data.get(field) or not str(data.get(field)).strip()]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        allowed_statuses = ["Scheduled", "Completed", "Cancelled"]
        if "status" in data and data["status"] not in allowed_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"}), 400

        updated = database.update_appointment(appointment_id, data)
        if not updated:
            return jsonify({"error": "Appointment not found"}), 404

        return jsonify(updated), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update appointment: {str(e)}"}), 500


@app.route("/api/appointments/<int:appointment_id>/status", methods=["PATCH"])
def update_status(appointment_id):
    try:
        data = request.get_json(silent=True)
        if not data or "status" not in data:
            return jsonify({"error": "Request body must include 'status'"}), 400

        new_status = data["status"]
        allowed_statuses = ["Scheduled", "Completed", "Cancelled"]
        if new_status not in allowed_statuses:
            return jsonify({"error": f"Invalid status. Allowed values: {', '.join(allowed_statuses)}"}), 400

        updated = database.update_appointment_status(appointment_id, new_status)
        if not updated:
            return jsonify({"error": "Appointment not found"}), 404

        return jsonify(updated), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to update appointment status: {str(e)}"}), 500


@app.route("/api/appointments/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    try:
        deleted = database.delete_appointment(appointment_id)
        if not deleted:
            return jsonify({"error": "Appointment not found"}), 404
        return jsonify({"message": "Appointment deleted successfully", "id": appointment_id}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete appointment: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
