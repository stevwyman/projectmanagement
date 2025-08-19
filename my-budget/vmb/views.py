from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView

from logging import getLogger

import math
import os
import pandas as pd
import statistics

from .helper import burndown, burndown_by_timecards, hours_by_month_by_project_group, calculate_hours_by_month, calculate_hours_sum, calculate_hours_by_team_and_milestone, calculate_hours_by_milestone
from .models import ExpenditureItem, Project, Project_Group, ExpenditureDocument, Milestone, TimecardItems, TimecardDocument, TASK_TYPES
from .forms import ExpenditureDocumentForm, ProjectForm, MilestoneForm, TimecardDocumentForm


logger = getLogger(__name__)


def expenditure_documents(request):
    documents = ExpenditureDocument.objects.all()
    return render(request, "vmb/expenditure_documents.html", {"documents": documents})


def upload_expenditures(request):
    if request.method == "POST":
        form = ExpenditureDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.info(request, "uploaded file")
            return redirect("expenditure-documents")
    else:
        form = ExpenditureDocumentForm()
    return render(request, "vmb/expenditure_upload.html", {"form": form})


def read_expenditures(request):

    filenames = next(os.walk(settings.EXPENDITURE_ROOT), (None, None, []))[2]  # [] if no file

    date_format = "%d-%b-%Y"

    saved_entries = 0

    logger.debug("found %i files for import", len(filenames))

    for filename in filenames:
        abs_file_path = os.path.join(settings.EXPENDITURE_ROOT, filename)

        data = pd.read_csv(abs_file_path, sep="\t", encoding="UTF-16")

        for index, row in data.iterrows():
            trans_id = row.get("Trans Id")
            items = ExpenditureItem.objects.filter(trans_id=trans_id)
            if items.exists():
                logger.debug("Trans Id %i already existing, skipping", trans_id)
                continue

            project_id = row.get("Project")

            try:
                project = Project.objects.get(oracle_id=project_id)
            except ObjectDoesNotExist:
                project = Project.objects.create(
                    oracle_id=project_id,
                    name=project_id,
                    sold_hours=1,
                    start_date="1976-01-01",
                    end_date=datetime.now(),
                )
                logger.info("Created Project for Oracle ID %s", project_id)

            item = ExpenditureItem()

            item.trans_id = trans_id
            item.project = project

            item.task = row.get("Task")
            item.expnd_type = row.get("Project")

            date_obj = datetime.strptime(row.get("Item Date"), date_format)

            item.item_date = date_obj
            item.employee_supplier = row.get("Employee/Supplier")
            item.quantity = row.get("Quantity")
            item.uom = row.get("UOM")

            pfbc = row.get("Proj Func Burdened Cost")
            if math.isnan(pfbc):
                pfbc = 0.0
            item.proj_func_burdened_cost = pfbc

            pbc = row.get("Project Burdened Cost")
            if math.isnan(pbc):
                pbc = 0.0
            item.project_burdened_cost = pbc

            ar = row.get("Accrued Revenue")
            if math.isnan(ar):
                ar = 0.0
            item.accrued_revenue = ar

            ba = row.get("Bill Amount")
            if math.isnan(ba):
                ba = 0.0
            item.bill_amount = ba

            item.comment = row.get("Comment")

            item.save()
            saved_entries += 1

    messages.info(
        request,
        "Found "
        + str(len(filenames))
        + " file(s) for import and imported "
        + str(saved_entries)
        + " entries.",
    )

    return redirect("overview")


def delete_expenditure_documents(request):

    files = ExpenditureDocument.objects.all()
    for file in files:
        logger.info(f"Working on {file.document}")
        filename = os.path.join(settings.EXPENDITURE_ROOT, file.filename())

        if os.path.exists(filename):
            os.remove(filename)

            document = ExpenditureDocument.objects.get(document=file.document)
            document.delete()
            logger.info(f"The file {filename} has been deleted.")
        else:
            document = ExpenditureDocument.objects.get(document=file.document)
            document.delete()
            logger.warning(f"Could not locate {filename}")

    return redirect("expenditure-documents")


def timecard_documents(request):
    documents = TimecardDocument.objects.all()
    return render(request, "vmb/timecard_documents.html", {"documents": documents})


def upload_timecard(request):
    if request.method == "POST":
        form = TimecardDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.info(request, "uploaded file")
            return redirect("timecard-documents")
    else:
        form = TimecardDocumentForm()
    return render(request, "vmb/timecard_upload.html", {"form": form})


def report_timecards(request, project_id):

    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)
        
    content_disposition = "attachment; filename=summary_report_" + str(project_id) + ".csv"

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": content_disposition}
    )

    csv_data = [
        ("Oracle ID", "Date", "Month", "Week", "Name", "Milestone", "Total Hours", "Team", "Note")
    ]

    reported_timecards = project.timecarditems_set.all()
    for timecard_entry in reported_timecards:

        oracle_id = timecard_entry.project.oracle_id
        date = timecard_entry.start_date
        month = date.strftime("%m") + "(" + date.strftime("%B") + ")"
        week = date.strftime("%V")
        name = timecard_entry.name
        milestone = timecard_entry.milestone.get_name_display
        total_hours = timecard_entry.total_hours
        team = timecard_entry.team
        note = timecard_entry.notes

        csv_data.append((oracle_id, date, month, week, name, milestone, total_hours, team, note))


    t = loader.get_template("vmb/timecard_report.txt")
    c = {"data": csv_data}
    response.write(t.render(c))

    return response


def report_timecards_by_group(request, project_group_id):

    if request.method == "GET":
        project_group = get_object_or_404(Project_Group, pk=project_group_id)
        
    content_disposition = "attachment; filename=summary_report_" + str(project_group.name) + ".csv"

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": content_disposition}
    )

    csv_data = [
        ("Oracle ID", "Date", "Month", "Week", "Name", "Milestone", "Total Hours", "Team", "Note")
    ]

    project_list = project_group.get_projects()
 
    reported_timecards = TimecardItems.objects.filter(project__in=project_list)
    for timecard_entry in reported_timecards:

        oracle_id = timecard_entry.project.oracle_id
        date = timecard_entry.start_date
        month = date.strftime("%m") + "(" + date.strftime("%B") + ")"
        week = date.strftime("%V")
        name = timecard_entry.name
        milestone = timecard_entry.milestone.get_name_display
        total_hours = timecard_entry.total_hours
        team = timecard_entry.team
        note = timecard_entry.notes

        csv_data.append((oracle_id, date, month, week, name, milestone, total_hours, team, note))


    t = loader.get_template("vmb/timecard_report.txt")
    c = {"data": csv_data}
    response.write(t.render(c))

    return response


def report_timecards_by_group_by_month(request, project_group_id, month):

    if request.method == "GET":
        project_group = get_object_or_404(Project_Group, pk=project_group_id)

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="report.csv"'},
    )

    csv_data = [
        ("Start Date", "OPA Project Number", "Total Hours", "Milestone", "Resource", "Timecard Notes")
    ]

    project_list = project_group.get_projects()

    target_month = datetime.strptime(month, "%d%b%Y")

    filter_month = target_month.month
    filter_year = target_month.year
 
    reported_timecards = TimecardItems.objects.filter(
        project__in=project_list,
        start_date__year__gte=filter_year,
        start_date__month__gte=filter_month,
        start_date__year__lte=filter_year,
        start_date__month__lte=filter_month,
    )

    for timecard_entry in reported_timecards:

        start_date = timecard_entry.start_date.strftime("%-m/%-d/%Y")
        opa_project_number = timecard_entry.project.oracle_id
        total_hours = timecard_entry.total_hours
        milestone = timecard_entry.milestone.get_name_display
        resource = timecard_entry.name
        timecard_notes = timecard_entry.notes

        csv_data.append((start_date, opa_project_number, total_hours, milestone, resource, timecard_notes))


    t = loader.get_template("vmb/timecard_report_customer.txt")
    c = {"data": csv_data}
    response.write(t.render(c))

    return response


def report_timecards_customer(request, project_id, month):

    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="report.csv"'},
    )

    csv_data = [
        ("Start Date", "OPA Project Number", "Total Hours", "Milestone", "Resource", "Timecard Notes")
    ]

    reported_timecards = project.timecarditems_set.filter(
        start_date__month__lte=month,
        start_date__month__gte=month)
    
    for timecard_entry in reported_timecards:

        start_date = timecard_entry.start_date.strftime("%-m/%-d/%Y")
        opa_project_number = project.oracle_id
        total_hours = timecard_entry.total_hours
        milestone = timecard_entry.milestone.get_name_display
        resource = timecard_entry.name
        timecard_notes = timecard_entry.notes

        csv_data.append((start_date, opa_project_number, total_hours, milestone, resource, timecard_notes))


    t = loader.get_template("vmb/timecard_report_customer.txt")
    c = {"data": csv_data}
    response.write(t.render(c))

    return response


def read_timecards(request):

    filenames = next(os.walk(settings.TIMECARDS_ROOT), (None, None, []))[2]  # [] if no file

    date_format = "%m/%d/%Y"

    saved_entries = 0

    logger.debug("found %i files for import", len(filenames))

    TASK_TYPE_CHOICES = dict([i[::-1] for i in TASK_TYPES])

    for filename in filenames:
        abs_file_path = os.path.join(settings.TIMECARDS_ROOT, filename)

        data = pd.read_csv(abs_file_path, sep=",", encoding="UTF-8")

        for index, row in data.iterrows():
            timecard_id = row.get("Timecard Split ID")
            items = TimecardItems.objects.filter(timecard_id=timecard_id)
            if items.exists():
                logger.info("timecard_id %s already existing, skipping", timecard_id)
                continue

            project_id = row.get("Project: OPA Project Number")

            try:
                project = Project.objects.get(oracle_id=project_id)
            except ObjectDoesNotExist:
                project = Project.objects.create(
                    oracle_id=project_id,
                    name=project_id,
                    sold_hours=1,
                    start_date="1976-01-01",
                    end_date=datetime.now(),
                )
                logger.info("Created Project for Oracle ID %s", project_id)

            timecard_item = TimecardItems()

            timecard_item.timecard_id = timecard_id
            timecard_item.project = project

            milestone_task = row.get("Milestone: OPA Task Number")
            milestone_name = row.get("Milestone: Milestone Name")

            milestone_name_short = TASK_TYPE_CHOICES[milestone_name]

            milestone = Milestone.objects.filter(project=project, task=milestone_task).first()
            if milestone is None:
                logger.debug(f"no milestone {milestone_task} for project {project}")
                milestone = Milestone.objects.create(
                    project=project,
                    task=milestone_task,
                    name=milestone_name_short,
                    cost_per_hour=0,
                    sold_hours=0
                )
                logger.info(f"Created {milestone}")

            timecard_item.milestone=milestone

            date_obj = datetime.strptime(row.get("Start Date"), date_format)

            timecard_item.start_date = date_obj
            timecard_item.name = row.get("Resource: Full Name")
            timecard_item.total_hours = row.get("Total Hours")
            timecard_item.deliver_location = row.get("Delivery Location")

            timecard_notes_week = row.get("Timecard Notes week")
            timecard_notes_friday = row.get("Friday Notes")

            try:
                math.isnan(timecard_notes_week)
                timecard_item.notes = timecard_notes_friday
            except TypeError:
                timecard_item.notes = timecard_notes_week

            try:
                team = timecard_item.notes[:3]
            except TypeError:
                team = "T00"

            if team.startswith("T"):
                timecard_item.team = team
            else:
                timecard_item.team = "T00"
                #item.team = "N/A"
                
            timecard_item.save()
            saved_entries += 1

        logger.info(f"saved {saved_entries} entries")

    messages.info(
        request,
        "Found "
        + str(len(filenames))
        + " file(s) for import and imported "
        + str(saved_entries)
        + " entries.",
    )

    return redirect("timecard-overview")


def delete_timecard_documents(request):

    files = TimecardDocument.objects.all()
    for file in files:
        logger.info(f"Working on {file.document}")
        filename = os.path.join(settings.TIMECARDS_ROOT, file.filename())

        if os.path.exists(filename):
            os.remove(filename)

            document = TimecardDocument.objects.get(document=file.document)
            document.delete()
            logger.info(f"The file {filename} has been deleted.")
        else:
            document = TimecardDocument.objects.get(document=file.document)
            document.delete()
            logger.warning(f"Could not locate {filename}")

    return redirect("timecard-documents")

#
# Expenditure based reporting
#


def expenditure_detail_by_project(request, project_id):
    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)

    data = project.expenditureitem_set.filter(uom="Hours")

    hours_by_month = (
        data.annotate(month=TruncMonth("item_date"))
        .values("month")
        .annotate(sum=Sum("quantity"))
    )
    hours_sum = data.aggregate(sum=Sum("quantity"))
    sums = hours_by_month.values_list("sum", flat="True")

    tasks_with_hours = data.values("task").distinct()
    sums_by_task = []
    for i in tasks_with_hours:
        task = i["task"]
        hours_by_task = project.expenditureitem_set.filter(uom="Hours", task=task)
        sum = hours_by_task.aggregate(sum=Sum("quantity"))
        milestone = project.milestone_set.filter(task=task).first()
        delta = float("NaN")
        if milestone != None:
            task = milestone.get_name_display()
            delta = milestone.sold_hours - sum["sum"]
        sums_by_task.append(
            {"task": task, "sum": sum, "milestone": milestone, "delta": delta}
        )

    milestones = project.milestone_set.filter()
    logger.info(milestones)

    template = loader.get_template("vmb/expenditure_detail_by_project.html")
    context = {
        "hours_by_month": hours_by_month,
        "hours_sum": hours_sum,
        "project": project,
        "avg_burned": statistics.fmean(sums),
        "graphic": burndown(project=project, timeframe="week")["image"],
        "sums_by_task": sums_by_task,
        "milestones": milestones,
    }
    return HttpResponse(template.render(context, request))


def expenditure_detail_by_project_month(request, project_id, month):
    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)

    target_month = datetime.strptime(month, "%d%b%Y")

    filter_month = target_month.month
    filter_year = target_month.year

    data = project.expenditureitem_set.filter(
        uom="Hours",
        item_date__year__gte=filter_year,
        item_date__month__gte=filter_month,
        item_date__year__lte=filter_year,
        item_date__month__lte=filter_month,
    )

    hours_by_employee = (
        data.values("task", "employee_supplier")
        .order_by("task")
        .annotate(sum=Sum("quantity"))
    )
    sum_by_month = data.aggregate(hours_sum=Sum("quantity"))

    template = loader.get_template("vmb/expenditure_detail_by_project_month.html")
    context = {
        "hours_by_employee": hours_by_employee,
        "sum_by_month": sum_by_month,
        "project": project,
        "month": filter_month,
        "year": filter_year,
        "target_month": target_month,
    }
    return HttpResponse(template.render(context, request))


def expenditure_overview(request):
    data = ExpenditureItem.objects.filter(uom="Hours")

    hours_by_project = (
        data.values("project_id")
        .order_by("project")
        .annotate(hours_sum=Sum("quantity"))
    )

    today = datetime.now().date()
    for line in hours_by_project:
        project = Project.objects.get(oracle_id=line["project_id"])
        line["project"] = project
        line["ratio"] = 100 * line["hours_sum"] / project.sold_hours
        line["hours_left"] = project.sold_hours - line["hours_sum"]
        days_left = project.end_date - today
        if days_left.days < 0:
            line["days_left"] = "-"
        else:
            line["days_left"] = days_left.days

    template = loader.get_template("vmb/expenditure_overview.html")
    context = {
        "hours_by_project": hours_by_project,
    }
    return HttpResponse(template.render(context, request))

#
# Timecard based reporting
#

def timecard_detail_by_project(request, project_id):
    """list the summary of hours by month, also provides 
    an overview of hours by milestone and team"""

    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)

    timecards = project.timecarditems_set.all()

    hours_by_month = calculate_hours_by_month(timecards)
    hours_sum = calculate_hours_sum(timecards)

    sums = hours_by_month.values_list("sum", flat="True")

    teams_lines = calculate_hours_by_team_and_milestone(timecards)

    sums_by_milestone = calculate_hours_by_milestone(timecards)

    milestones = project.milestone_set.filter()
    
    template = loader.get_template("vmb/timecard_detail_by_project.html")
    context = {
        "hours_by_month": hours_by_month,
        "hours_sum": hours_sum,
        "project": project,
        "avg_burned": statistics.fmean(sums),
        "graphic": burndown_by_timecards(project=project, timeframe="week")["image"],
        "sums_by_task": sums_by_milestone,
        "milestones": milestones,
        "hours_by_and_milestone": teams_lines
    }
    return HttpResponse(template.render(context, request))


def timecard_detail_by_project_month(request, project_id, month):
    """
    simple view to show the timecards for a specific month with 
    date, name, milestone and comment
    """
    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)

    target_month = datetime.strptime(month, "%d%b%Y")

    filter_month = target_month.month
    filter_year = target_month.year

    timecards = project.timecarditems_set.filter(
        
        start_date__year__gte=filter_year,
        start_date__month__gte=filter_month,
        start_date__year__lte=filter_year,
        start_date__month__lte=filter_month,
    )

    milestones_with_hours = timecards.values("milestone").distinct()
    teams_with_hours = timecards.values('team').distinct()
    teams_lines = []

    for team_with_hours in teams_with_hours:
        team_name = team_with_hours['team']
        sums_by_team_and_milestone = []
        for milestone_with_hours in milestones_with_hours:
            milestone_id = milestone_with_hours['milestone']
            milestone = Milestone.objects.get(id=milestone_id)
            hours_by_milestone_and_team = timecards.filter(
                team=team_name, milestone=milestone_id)
            sum = hours_by_milestone_and_team.aggregate(sum=Sum("total_hours"))

            sums_by_team_and_milestone.append(
                {"milestone":milestone, "hours":sum}
            )
        teams_lines.append(
            {"team": team_with_hours, "sums":sums_by_team_and_milestone}
        )
    
    teams_lines = sorted(teams_lines, key=lambda item: item['team']['team'] )

    hours_by_employee = (
        timecards.values("milestone__task", "name")
        .order_by("milestone__task")
        .annotate(sum=Sum("total_hours"))
    )
    sum_by_month = timecards.aggregate(hours_sum=Sum("total_hours"))

    template = loader.get_template("vmb/timecard_detail_by_project_month.html")
    context = {
        "hours_by_employee": hours_by_employee,
        "sum_by_month": sum_by_month,
        "project": project,
        "month": filter_month,
        "year": filter_year,
        "target_month": target_month,
        "timecards": timecards,
        "hours_by_and_milestone": teams_lines
    }
    return HttpResponse(template.render(context, request))


def timecard_overview(request):
    data = TimecardItems.objects.all()

    hours_by_project = (
        data.values("project_id")
        .order_by("project")
        .annotate(hours_sum=Sum("total_hours"))
    )

    today = datetime.now().date()
    for line in hours_by_project:
        project = Project.objects.get(oracle_id=line["project_id"])
        line["project"] = project
        line["ratio"] = 100 * line["hours_sum"] / project.sold_hours
        line["hours_left"] = project.sold_hours - line["hours_sum"]
        days_left = project.end_date - today
        if days_left.days < 0:
            line["days_left"] = "-"
        else:
            line["days_left"] = days_left.days

    project_groups_list = Project_Group.objects.all()

    template = loader.get_template("vmb/timecard_overview.html")
    context = {
        "hours_by_project": hours_by_project, "project_groups_list" : project_groups_list
    }
    return HttpResponse(template.render(context, request))


def project_group_detail(request, project_group_id):
    if request.method == "GET":
        project_group = get_object_or_404(Project_Group, pk=project_group_id)

    project_list = project_group.get_projects()

    reported_timecards = TimecardItems.objects.filter(project__in=project_list)
    hours_by_month = calculate_hours_by_month(reported_timecards)
    hours_sum = calculate_hours_sum(reported_timecards)

    team_lines = calculate_hours_by_team_and_milestone(reported_timecards)

    graphic = hours_by_month_by_project_group(project_group)["image"]

    template = loader.get_template("vmb/project_group_detail.html")
    context = {
        "project_group": project_group,
        "project_list": project_list,
        "graphic": graphic,
        "hours_by_month": hours_by_month,
        "hours_sum": hours_sum,
        "hours_by_team_and_milestone": team_lines
    }
    return HttpResponse(template.render(context, request))


class ProjectCreateView(CreateView):
    model = Project
    template_name = "vmb/project_create.html"
    form_class = ProjectForm
    success_url = reverse_lazy("overview")


class ProjectUpdateView(UpdateView):
    model = Project
    fields = ["name", "sold_hours", "start_date", "end_date", "type", "project_group"]
    template_name = "vmb/project_update.html"
    success_url = reverse_lazy("overview")


def delete_project(request, project_id):
    if request.method == "GET":
        project = get_object_or_404(Project, pk=project_id)
        project.delete()

    return redirect("overview")


class MilestoneCreateView(CreateView):
    model = Milestone
    template_name = "vmb/milestone_create.html"
    form_class = MilestoneForm

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["pk"])
        return super(MilestoneCreateView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        oracle_id = self.object.project_id
        return reverse_lazy("detail_by_project", kwargs={"project_id": oracle_id})

    def form_valid(self, form):
        form.instance.project = self.project
        messages.success(self.request, "Milestone has been added")
        return super(MilestoneCreateView, self).form_valid(form)
    

class Project_GroupCreateView(CreateView):
    model = Project_Group
    template_name = "vmb/project_group_create.html"
    fields = ["name"]
    success_url = reverse_lazy("overview")


class MilestoneUpdateView(UpdateView):
    model = Milestone
    fields = ["task", "name", "sold_hours"]
    template_name = "vmb/milestone_update.html"
    success_url = reverse_lazy("overview")


class TimecardItemUpdateView(UpdateView):
    model = TimecardItems
    fields = ["name", "total_hours", "deliver_location", "team", "notes"]
    template_name = "vmb/timecarditem_update.html"
    success_url = reverse_lazy("overview")