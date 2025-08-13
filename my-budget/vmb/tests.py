from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from logging import getLogger

from .models import Project, ExpenditureDocument, TimecardDocument

import os


logger = getLogger(__name__)


class Delete_Project(TestCase):

    def setUp(self):
        client = Client()
        with open("test_data/test.tsv", mode="rb") as fp:
            client.post(reverse("upload-expenditures"), {"document": fp})
        response = client.get(reverse("read-expenditures"))

    def test_read(self):
        """Check if a specific project can be deleted"""
        client = Client()
        response = client.get(reverse("project_delete", kwargs={"project_id": 12}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["location"], "/vmb/")

        projects = Project.objects.all()
        self.assertEqual(projects.count(), 0)

    def tearDown(self):
        cleaning_up(self)


class Upload_TSV(TestCase):

    def test_upload(self):
        """Check if the file from the media folder can be uploaded"""
        client = Client()
        with open("test_data/test.tsv", mode="rb") as fp:
            client.post(reverse("upload-expenditures"), {"document": fp})

        TARGET_FILE = os.path.join(settings.EXPENDITURE_ROOT, "test.tsv")
        self.assertTrue(os.path.isfile(TARGET_FILE))

        uploaded_document = ExpenditureDocument.objects.all().first()
        self.assertIsNotNone(uploaded_document)
        self.assertEqual(uploaded_document.filename(), "test.tsv")

    def tearDown(self):
        cleaning_up(self)


class Delete_TSV(TestCase):

    def setUp(self):
        setting_up_expenditures(self)

    def test_delete(self):
        """Check if the file from the upload folder can be deleted"""
        TARGET_FILE = os.path.join(settings.EXPENDITURE_ROOT, "test.tsv")

        self.assertTrue(os.path.isfile(TARGET_FILE))

        client = Client()
        client.get(reverse("delete-expenditure-documents"))

        self.assertFalse(os.path.isfile(TARGET_FILE))

        uploaded_documents = ExpenditureDocument.objects.all()

        self.assertEqual(uploaded_documents.count(), 0)

    def tearDown(self):
        cleaning_up(self)


class Import_TSV(TestCase):

    def setUp(self):
        setting_up_expenditures(self)

    def test_read(self):
        """Check if tsv files can be read"""
        client = Client()
        response = client.get(reverse("read-expenditures"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["location"], "/vmb/")

        project = Project.objects.filter(pk=12).first()
        self.assertIsNotNone(project)
        self.assertEqual(project.expenditureitem_set.count(), 256)

    def tearDown(self):
        cleaning_up(self)


class BurndownTestCase(TestCase):
    def setUp(self):
        Project.objects.create(
            oracle_id="178",
            name="BTest",
            start_date="2024-10-10",
            end_date="2025-10-10",
            sold_hours="750",
        )

    def test_burndown(self):
        """Check if the project runtime is calculated correctly"""
        btest = Project.objects.get(oracle_id="178")
        self.assertEqual(btest.name, "BTest")
        self.assertEqual(btest.runtime_in_month(), 12)


def setting_up_expenditures(self):
    client = Client()
    with open("test_data/test.tsv", mode="rb") as fp:
        client.post(reverse("upload-expenditures"), {"document": fp})


def setting_up_timecards(self):
    client = Client()
    with open("test_data/test.csv", mode="rb") as fp:
        client.post(reverse("upload-timecards"), {"document": fp})


def cleaning_up(self):
    """Clean up the upload folder"""
    try:
        filelist = [
            f for f in os.listdir(settings.EXPENDITURE_ROOT) if f.endswith(".tsv")
        ]
        for f in filelist:
            os.remove(os.path.join(settings.EXPENDITURE_ROOT, f))
    except Exception as e:
        logger.warn(f"Could not delete files in {settings.EXPENDITURE_ROOT}: {e}")

    try:
        filelist = [
            f for f in os.listdir(settings.TIMECARDS_ROOT) if f.endswith(".csv")
        ]
        for f in filelist:
            os.remove(os.path.join(settings.TIMECARDS_ROOT, f))
    except Exception as e:
        logger.warn(f"Could not delete files in {settings.TIMECARDS_ROOT}: {e}")
