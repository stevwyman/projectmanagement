import base64
import matplotlib

matplotlib.use("SVG")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from django.db.models import Sum
from django.db.models.manager import BaseManager
from django.db.models.functions import TruncMonth, TruncWeek
from io import BytesIO
from .models import Project, Project_Group, TimecardItems, Milestone


def burndown(project: Project, timeframe: str) -> dict:

    data = project.expenditureitem_set.filter(uom="Hours")

    if timeframe == "month":
        hours = (
            data.annotate(month=TruncMonth("item_date"))
            .values("month")
            .annotate(sum=Sum("quantity"))
        )
        time = hours.values_list("month", flat="True")
    else:
        hours = (
            data.annotate(week=TruncWeek("item_date"))
            .values("week")
            .annotate(sum=Sum("quantity"))
        )
        time = hours.values_list("week", flat="True")

    sums = hours.values_list("sum", flat="True")

    burned = []
    cumulated = project.sold_hours
    for i in sums:
        cumulated -= i
        burned.append(cumulated)

    plt.clf()
    fig, ax1 = plt.subplots(figsize=(7, 4))
    fig.tight_layout()

    #ibd_timeframe, ibd_hours_left = project.ideal_burndown_by_month()
    ibd_timeframe, ibd_hours_left = project.ideal_burndown_by_weeks()

    ax1.plot(ibd_timeframe, ibd_hours_left, linestyle="dashed", color="green", label="Ideal")
    ax1.step(time, burned, where="post", label="Actual")
    ax1.set_title(f"Burn down chart for {project.oracle_id} ")
    ax1.set_ylabel("Remaining hours")
    ax1.legend(loc="upper right")

    #plt.bar(months, sums, width=9)
    plt.xticks(rotation=20)

    ax2 = ax1.twinx()
    ax2.bar(time, sums, width=6, color="orange", label="Hours", alpha=0.25)
    ax2.set_ylabel("Burned hours by week")

    # Set the locator
    locator = mdates.MonthLocator()  # every month
    # Specify the format - %b gives us Jan, Feb...
    fmt = mdates.DateFormatter('%b %Y')
    X = plt.gca().xaxis
    X.set_major_locator(locator)
    # Specify formatter
    X.set_major_formatter(fmt)

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=96, bbox_inches="tight")
    buffer.seek(0)
    image_png = buffer.getvalue()
    
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode("utf-8")

    #memory management
    buffer.close()
    plt.close()

    return {"image": graphic}

def burndown_by_timecards(project: Project, timeframe: str) -> dict:

    data = project.timecarditems_set.all()

    if timeframe == "month":
        hours = (
            data.annotate(month=TruncMonth("start_date"))
            .values("month")
            .annotate(sum=Sum("total_hours"))
        )
        time = hours.values_list("month", flat="True")
    else:
        hours = (
            data.annotate(week=TruncWeek("start_date"))
            .values("week")
            .annotate(sum=Sum("total_hours"))
        )
        time = hours.values_list("week", flat="True")

    sums = hours.values_list("sum", flat="True")

    burned = []
    cumulated = project.sold_hours
    for i in sums:
        cumulated -= i
        burned.append(cumulated)

    plt.clf()
    fig, ax1 = plt.subplots(figsize=(7, 4))
    fig.tight_layout()

    #ibd_timeframe, ibd_hours_left = project.ideal_burndown_by_month()
    ibd_timeframe, ibd_hours_left = project.ideal_burndown_by_weeks()

    ax1.plot(ibd_timeframe, ibd_hours_left, linestyle="dashed", color="green", label="Ideal")
    ax1.step(time, burned, where="post", label="Actual")
    ax1.set_title(f"Burn down chart for {project.oracle_id} ")
    ax1.set_ylabel("Remaining hours")
    ax1.legend(loc="upper right")

    #plt.bar(months, sums, width=9)
    plt.xticks(rotation=20)

    ax2 = ax1.twinx()
    ax2.bar(time, sums, width=6, color="orange", label="Hours", alpha=0.25)
    ax2.set_ylabel("Burned hours by week")

    # Set the locator
    locator = mdates.MonthLocator()  # every month
    # Specify the format - %b gives us Jan, Feb...
    fmt = mdates.DateFormatter('%b %Y')
    X = plt.gca().xaxis
    X.set_major_locator(locator)
    # Specify formatter
    X.set_major_formatter(fmt)

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=96, bbox_inches="tight")
    buffer.seek(0)
    image_png = buffer.getvalue()
    
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode("utf-8")

    #memory management
    buffer.close()
    plt.close()

    return {"image": graphic}

def hours_by_month_by_project_group(project_group: Project_Group) -> dict:
    """
    Creates a bar-chart with sum hours by month for a Project Group
    """
    project_list = project_group.get_projects()

    data = TimecardItems.objects.filter(project__in=project_list)

    hours = (
            data.annotate(month=TruncMonth("start_date"))
            .values("month")
            .annotate(sum=Sum("total_hours"))
        )
    time = hours.values_list("month", flat="True")

    sums = hours.values_list("sum", flat="True")

    plt.clf()

    fig, ax1 = plt.subplots(figsize=(7, 4))
    fig.tight_layout()

    plt.bar(time, sums, width=9)
    plt.xticks(rotation=20)

    ax1.bar(time, sums, width=9, color="red", label="Hours")
    ax1.set_ylabel("Burned hours by month")

    # Set the locator
    locator = mdates.MonthLocator()  # every month
    # Specify the format - %b gives us Jan, Feb...
    fmt = mdates.DateFormatter('%b %Y')
    X = plt.gca().xaxis
    X.set_major_locator(locator)
    # Specify formatter
    X.set_major_formatter(fmt)

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=96, bbox_inches="tight")
    buffer.seek(0)
    image_png = buffer.getvalue()
    
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode("utf-8")

    #memory management
    buffer.close()
    plt.close()

    return {"image": graphic}

#
# helper methods for getting data from the db
#

def calculate_hours_by_month(reported_timecards: BaseManager[TimecardItems]):
    hours_by_month = (
        reported_timecards.annotate(month=TruncMonth("start_date"))
        .values("month")
        .annotate(sum=Sum("total_hours"))
    )
    return hours_by_month

def calculate_hours_sum(reported_timecards: BaseManager[TimecardItems]):
    return reported_timecards.aggregate(sum=Sum("total_hours"))

def calculate_hours_by_team_and_milestone(reported_timecards: BaseManager[TimecardItems]):
    milestones_with_hours = reported_timecards.values("milestone").distinct()
    teams_with_hours = reported_timecards.values('team').distinct()
    teams_lines = []

    for team_with_hours in teams_with_hours:
        team_name = team_with_hours['team']
        sums_by_team_and_milestone = []
        for milestone_with_hours in milestones_with_hours:
            milestone_id = milestone_with_hours['milestone']
            milestone = Milestone.objects.get(id=milestone_id)
            hours_by_milestone_and_team = TimecardItems.objects.filter(
                team=team_name, milestone=milestone_id)
            sum = hours_by_milestone_and_team.aggregate(sum=Sum("total_hours"))

            sums_by_team_and_milestone.append(
                {"milestone":milestone, "hours":sum}
            )
        teams_lines.append(
            {"team": team_with_hours, "sums":sums_by_team_and_milestone}
        )
    
    teams_lines = sorted(teams_lines, key=lambda item: item['team']['team'] )
    return teams_lines

def calculate_hours_by_milestone(reported_timecards: BaseManager[TimecardItems]):
    milestones_with_hours = reported_timecards.values("milestone").distinct()
    
    sums_by_milestone = []
    for milestone_with_hours in milestones_with_hours:
        milestone_id = milestone_with_hours['milestone']
        milestone = Milestone.objects.get(id=milestone_id)
        hours_by_milestone = TimecardItems.objects.filter(milestone=milestone_id)
        sum = hours_by_milestone.aggregate(sum=Sum("total_hours"))

        delta = float("NaN")
        if milestone != None:
            task = milestone.get_name_display()
            delta = milestone.sold_hours - sum["sum"]
        sums_by_milestone.append(
            {"task": task, "sum": sum, "milestone": milestone, "delta": delta}
        )
    return sums_by_milestone
