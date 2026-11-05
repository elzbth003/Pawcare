import os
import tempfile
import unittest
import database
from app import app


class PawCareTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for test isolation
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        
        os.environ["DATABASE_PATH"] = self.db_path
        database.init_db(self.db_path)

        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(self.db_path + ext):
                os.remove(self.db_path + ext)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")

    def test_index_dashboard(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"PawCare", res.data)
        self.assertIn(b"Appointments Directory", res.data)

    def test_stats_initial(self):
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total", data)
        self.assertIn("scheduled", data)
        self.assertIn("completed", data)
        self.assertIn("cancelled", data)
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["total"], data["scheduled"] + data["completed"] + data["cancelled"])

    def test_list_appointments(self):
        res = self.client.get("/api/appointments")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_create_appointment_success(self):
        new_apt = {
            "pet_name": "Barnaby",
            "pet_type": "Dog (Poodle)",
            "owner_name": "Claire Vance",
            "owner_phone": "555-9001",
            "owner_email": "claire@example.com",
            "appointment_date": "2026-11-10",
            "appointment_time": "11:00",
            "service": "Dental Cleaning",
            "status": "Scheduled",
            "notes": "Mild tartar build-up."
        }
        res = self.client.post("/api/appointments", json=new_apt)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIsNotNone(data.get("id"))
        self.assertEqual(data["pet_name"], "Barnaby")
        self.assertEqual(data["status"], "Scheduled")

        # Verify in list
        res_list = self.client.get("/api/appointments?q=Barnaby")
        list_data = res_list.get_json()
        self.assertTrue(any(a["pet_name"] == "Barnaby" for a in list_data))

    def test_create_appointment_missing_field(self):
        invalid_apt = {
            "pet_name": "Barnaby",
            # missing pet_type, owner_name, etc.
        }
        res = self.client.post("/api/appointments", json=invalid_apt)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Missing required fields", data["error"])

    def test_update_appointment_status(self):
        # Create appointment
        new_apt = {
            "pet_name": "Simba",
            "pet_type": "Cat",
            "owner_name": "Tom King",
            "owner_phone": "555-8833",
            "appointment_date": "2026-11-11",
            "appointment_time": "14:30",
            "service": "Vaccination",
            "status": "Scheduled"
        }
        create_res = self.client.post("/api/appointments", json=new_apt)
        apt_id = create_res.get_json()["id"]

        # Patch status to Completed
        patch_res = self.client.patch(f"/api/appointments/{apt_id}/status", json={"status": "Completed"})
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.get_json()["status"], "Completed")

        # Verify retrieval
        get_res = self.client.get(f"/api/appointments/{apt_id}")
        self.assertEqual(get_res.get_json()["status"], "Completed")

        # Try invalid status
        invalid_patch = self.client.patch(f"/api/appointments/{apt_id}/status", json={"status": "Pending"})
        self.assertEqual(invalid_patch.status_code, 400)

    def test_update_full_appointment(self):
        # Create appointment
        new_apt = {
            "pet_name": "Daisy",
            "pet_type": "Dog",
            "owner_name": "Alice Green",
            "owner_phone": "555-4422",
            "appointment_date": "2026-11-12",
            "appointment_time": "09:00",
            "service": "General Checkup",
            "status": "Scheduled"
        }
        create_res = self.client.post("/api/appointments", json=new_apt)
        apt_id = create_res.get_json()["id"]

        # Update appointment details
        updated_data = {
            "pet_name": "Daisy Mae",
            "pet_type": "Dog (Labrador)",
            "owner_name": "Alice Green",
            "owner_phone": "555-4422",
            "owner_email": "alice.g@example.com",
            "appointment_date": "2026-11-12",
            "appointment_time": "10:30",
            "service": "General Checkup & Nails",
            "status": "Scheduled",
            "notes": "Updated appointment time at owner request"
        }
        update_res = self.client.put(f"/api/appointments/{apt_id}", json=updated_data)
        self.assertEqual(update_res.status_code, 200)
        data = update_res.get_json()
        self.assertEqual(data["pet_name"], "Daisy Mae")
        self.assertEqual(data["appointment_time"], "10:30")

    def test_delete_appointment(self):
        new_apt = {
            "pet_name": "Temporary Pet",
            "pet_type": "Hamster",
            "owner_name": "Sam Solo",
            "owner_phone": "555-0000",
            "appointment_date": "2026-11-15",
            "appointment_time": "12:00",
            "service": "Nail Trimming",
            "status": "Scheduled"
        }
        create_res = self.client.post("/api/appointments", json=new_apt)
        apt_id = create_res.get_json()["id"]

        # Delete
        del_res = self.client.delete(f"/api/appointments/{apt_id}")
        self.assertEqual(del_res.status_code, 200)

        # Ensure 404 on get
        get_res = self.client.get(f"/api/appointments/{apt_id}")
        self.assertEqual(get_res.status_code, 404)

        # Delete non-existent
        del_res2 = self.client.delete(f"/api/appointments/{apt_id}")
        self.assertEqual(del_res2.status_code, 404)

    def test_search_and_filter(self):
        # Search for known initial seed data "Luna"
        res_search = self.client.get("/api/appointments?q=Luna")
        self.assertEqual(res_search.status_code, 200)
        search_data = res_search.get_json()
        self.assertTrue(any("Luna" in a["pet_name"] for a in search_data))

        # Filter by status Completed
        res_filter = self.client.get("/api/appointments?status=Completed")
        self.assertEqual(res_filter.status_code, 200)
        filter_data = res_filter.get_json()
        self.assertGreater(len(filter_data), 0)
        self.assertTrue(all(a["status"] == "Completed" for a in filter_data))


if __name__ == "__main__":
    unittest.main()
