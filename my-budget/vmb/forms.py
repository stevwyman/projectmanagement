from django import forms
from django.forms import ModelForm

from .models import ExpenditureDocument, Project, Project_Group, Milestone, TimecardDocument


class ExpenditureDocumentForm(forms.ModelForm):
    class Meta:
        model = ExpenditureDocument
        fields = ("document",)


class TimecardDocumentForm(forms.ModelForm):
    class Meta:
        model = TimecardDocument
        fields = ("document",)


class DateInput(forms.DateInput):
    input_type = "date"


class ProjectForm(ModelForm):

    class Meta:
        model = Project
        fields = ["oracle_id", "name", "sold_hours", "start_date", "end_date", "type"]
        widgets = {
            "start_date": DateInput(),
            "end_date": DateInput(),
        }

class MilestoneForm(ModelForm):

    class Meta:
        model = Milestone
        fields = ["task", "name", "cost_per_hour", "sold_hours"]
