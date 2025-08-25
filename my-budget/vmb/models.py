from django.db import models
from django.conf import settings
import pandas as pd
import decimal
import os

from .tools import diff_month, diff_weeks

PROJECT_TYPES = (
    ("tandm", "T&M"),
    ("cu", "CU"),
    ("pp", "Pre Paied"),
)

TASK_TYPES = (
    ("na", "Not assigned"),
    ("pc", "Project Coordinator"),
    ("pm", "Project Manager"),
    ("spm", "Senior Project Manager"),
    ("arc", "Architect"),
    ("sarc", "Senior Architect"),
    ("con", "Consultant"),
    ("scon", "Senior Consultant"),
    ("prarc", "Principal Architect"),
    ("el", "Engagement Lead"),
    ("fpe", "Fixed Price Engagement")
)

class Project_Group(models.Model):
    id = models.BigAutoField("ID", unique=True, null=False, primary_key=True)
    name = models.CharField("Name", max_length=200)

    def get_projects(self):
        return self.project_set.all()
    
    def __str__(self):
        return (f"{self.name}")


class Project(models.Model):
    oracle_id = models.BigIntegerField("Oracle ID", primary_key=True)
    name = models.CharField("Name", max_length=200)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    last_imported = models.DateTimeField(null=True)
    sold_hours = models.DecimalField("Sold Hours", decimal_places=2, max_digits=12)
    start_date = models.DateField()
    end_date = models.DateField()
    type = models.CharField(max_length=6, choices=PROJECT_TYPES, default="tandm")

    project_group = models.ForeignKey(Project_Group, blank=True, null=True, on_delete=models.SET_NULL)

    def runtime_in_month(self):
        return diff_month(self.end_date, self.start_date)

    def runtime_in_weeks(self):
        return diff_weeks(self.start_date, self.end_date)

    def ideal_burn_by_month(self):
        return self.sold_hours / self.runtime_in_month()

    def ideal_burndown_by_month(self):
        sold_hours = self.sold_hours
        runtime = self.runtime_in_month()
        burn_by_month = sold_hours / runtime
        remaining_hours = sold_hours
        start_date = self.start_date
        months = []
        hours_left = []
        for i in range(runtime):
            months.append(pd.to_datetime(start_date) + pd.DateOffset(months=i))
            remaining_hours = remaining_hours - burn_by_month
            hours_left.append(remaining_hours)

        return months, hours_left

    def ideal_burndown_by_weeks(self):
        sold_hours = self.sold_hours
        runtime = self.runtime_in_weeks()
        burn_by_week = sold_hours / decimal.Decimal(runtime)
        remaining_hours = sold_hours
        start_date = self.start_date
        weeks = []
        hours_left = []
        runtime_as_int = int(runtime)
        for i in range(runtime_as_int):
            weeks.append(pd.to_datetime(start_date) + pd.DateOffset(weeks=i))
            remaining_hours = remaining_hours - burn_by_week
            hours_left.append(remaining_hours)

        return weeks, hours_left

    class Meta:
        ordering = ["name"]


class Milestone(models.Model):
    id = models.BigAutoField("ID", unique=True, null=False, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    task = models.CharField("Task", max_length=5)
    name = models.CharField(max_length=6, choices=TASK_TYPES, default="--")
    cost_per_hour = models.DecimalField(
        "Cost per Hour", decimal_places=2, max_digits=12
    )
    sold_hours = models.DecimalField("Sold Hours", decimal_places=2, max_digits=12)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # combination of project and task must be unique
    def __str__(self):
        return (f"{self.id}, {self.task}, {self.get_name_display()}")


class TimecardItems(models.Model):
    timecard_id = models.CharField(max_length=28, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE)
    start_date = models.DateField(null=False)
    name = models.CharField("Full Name", max_length=255, null=False)
    total_hours = models.DecimalField(
        "Total Hours", decimal_places=2, max_digits=12, null=False
    )
    deliver_location = models.CharField("Delivery Location", max_length=25)
    team = models.CharField("Team", max_length=5)
    notes = models.CharField("Notes", max_length=512)


class ExpenditureItem(models.Model):
    trans_id = models.IntegerField(
        "Trans Id", unique=True, null=False, primary_key=True
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    task = models.CharField("Task", max_length=5)
    expnd_type = models.CharField("Expnd Type", max_length=55)
    item_date = models.DateField("Item Date")
    employee_supplier = models.CharField("Employee/Supplier", max_length=255)
    quantity = models.DecimalField("Quantity", decimal_places=2, max_digits=12)
    uom = models.CharField("UOM", max_length=55)
    proj_func_burdened_cost = models.DecimalField(
        "Proj Func Burdened Cost", decimal_places=2, max_digits=12
    )
    project_burdened_cost = models.DecimalField(
        "Project Burdened Cost", decimal_places=2, max_digits=12
    )
    accrued_revenue = models.DecimalField(
        "Accrued Revenue", decimal_places=2, max_digits=12
    )
    bill_amount = models.DecimalField("Bill Amount", decimal_places=2, max_digits=12)
    comment = models.CharField("Comment", max_length=255, null=True)


class ExpenditureDocument(models.Model):
    document = models.FileField(upload_to="expenditures")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def filename(self):
        return os.path.basename(self.document.name)


class TimecardDocument(models.Model):
    document = models.FileField(upload_to="timecards")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def filename(self):
        return os.path.basename(self.document.name)
