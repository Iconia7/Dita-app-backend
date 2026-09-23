from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .admin import HackFestRegistrationResource
from .models import HackFestRegistration


class HackFestRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_team_registration_success(self):
        payload = {
            "event_slug": "hack-fest-26",
            "registration_type": "team",
            "team_name": "AgriGuardians",
            "full_name": "Cynthia Wanjiku",
            "email": "cynthia@example.com",
            "phone": "+254711223344",
            "institution": "Daystar University",
            "is_daystar": True,
            "student_id": "22-1044",
            "campus": "Athi River Campus",
            "track_preference": "Climate & Agri-Tech",
            "role_preference": "Developer",
            "members": [
                {
                    "full_name": "Brian Kiprop",
                    "email": "brian@example.com",
                    "phone": "+254722334455",
                    "institution": "Daystar University",
                    "student_id": "22-1088",
                    "role": "UI/UX Designer",
                },
                {
                    "full_name": "Amina Yusuf",
                    "email": "amina@example.com",
                    "phone": "+254733445566",
                    "institution": "Daystar University",
                    "student_id": "23-0112",
                    "role": "Domain Expert",
                },
            ],
        }
        response = self.client.post("/api/events/hack-fest-26/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status"], "confirmed")
        self.assertEqual(response.data["team_size"], 3)

        reg = HackFestRegistration.objects.get(email="cynthia@example.com")
        self.assertEqual(reg.team_name, "AgriGuardians")
        self.assertEqual(reg.team_size, 3)
        self.assertEqual(len(reg.roster_data), 2)

    def test_external_individual_builder_registration(self):
        payload = {
            "event_slug": "hack-fest-26",
            "registration_type": "individual",
            "full_name": "David Mwangi",
            "email": "david.external@strathmore.edu",
            "phone": "+254799887766",
            "institution": "Strathmore University",
            "is_daystar": False,
            "track_preference": "Digital Finance",
            "role_preference": "Developer",
        }
        response = self.client.post("/api/events/hack-fest-26/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "confirmed")

        reg = HackFestRegistration.objects.get(email="david.external@strathmore.edu")
        self.assertFalse(reg.is_daystar)
        self.assertEqual(reg.institution, "Strathmore University")
        self.assertEqual(reg.team_size, 1)

    def test_capacity_endpoint(self):
        response = self.client.get("/api/events/hack-fest-26/capacity/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cap"], 50)
        self.assertEqual(response.data["confirmed_count"], 0)
        self.assertEqual(response.data["remaining_slots"], 50)
        self.assertFalse(response.data["is_full"])

    def test_50_builder_cap_waitlist_logic(self):
        # Register 10 teams of 5 builders (50 builders total)
        for i in range(10):
            HackFestRegistration.objects.create(
                event_slug="hack-fest-26",
                registration_type="team",
                team_name=f"Team {i}",
                team_size=5,
                full_name=f"Lead {i}",
                email=f"lead{i}@daystar.ac.ke",
                phone="+254700000000",
                institution="Daystar University",
                status="confirmed",
            )

        # Verify capacity endpoint reports 0 remaining
        cap_resp = self.client.get("/api/events/hack-fest-26/capacity/")
        self.assertEqual(cap_resp.data["confirmed_count"], 50)
        self.assertEqual(cap_resp.data["remaining_slots"], 0)
        self.assertTrue(cap_resp.data["is_full"])

        # Next registration should automatically receive waitlist status
        next_payload = {
            "event_slug": "hack-fest-26",
            "registration_type": "individual",
            "full_name": "Late Registrant",
            "email": "late@example.com",
            "phone": "+254711000111",
            "institution": "Daystar University",
        }
        response = self.client.post("/api/events/hack-fest-26/register/", next_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "waitlist")
        self.assertIn("priority waitlist", response.data["message"])

    def test_admin_export_resource(self):
        reg = HackFestRegistration.objects.create(
            event_slug="hack-fest-26",
            registration_type="team",
            team_name="FinTech Pros",
            team_size=4,
            full_name="Catherine Lead",
            email="cate@example.com",
            phone="+254722112233",
            institution="Daystar University",
            is_daystar=True,
            status="confirmed",
        )
        resource = HackFestRegistrationResource()
        dataset = resource.export(HackFestRegistration.objects.filter(id=reg.id))
        self.assertIn("FinTech Pros", str(dataset.dict))
        self.assertIn("Catherine Lead", str(dataset.dict))

    def test_daystar_student_id_normalization(self):
        payload = {
            "event_slug": "hack-fest-26",
            "registration_type": "individual",
            "full_name": "William Kengere",
            "email": "williamkengere231670@daystar.ac.ke",
            "phone": "+254700112233",
            "institution": "Daystar University",
            "is_daystar": True,
            "student_id": "231670",
            "campus": "Athi River Campus",
            "track_preference": "AI in Everyday Life",
            "role_preference": "Developer",
        }
        response = self.client.post("/api/events/hack-fest-26/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reg = HackFestRegistration.objects.get(email="williamkengere231670@daystar.ac.ke")
        self.assertEqual(reg.student_id, "23-1670")
