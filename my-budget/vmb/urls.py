from django.urls import path

from . import views

urlpatterns = [
    # straight to overview
    path("", views.timecard_overview, name="overview"),
    path("expenditure_documents", views.expenditure_documents, name="expenditure-documents"),
    path("upload_expenditures", views.upload_expenditures, name="upload-expenditures"),
    path("delete_expenditure_documents", views.delete_expenditure_documents, name="delete-expenditure-documents"),
    path("read_expenditures", views.read_expenditures, name="read-expenditures"),

    path("timecard_documents", views.timecard_documents, name="timecard-documents"),
    path("upload_timecards", views.upload_timecard, name="upload-timecards"),
    path("delete_timecard_documents", views.delete_timecard_documents, name="delete-timecard-documents"),
    path("read_timecards", views.read_timecards, name="read-timecards"),
    path("timecard_report/<int:project_id>", views.report_timecards, name="report-timecards"),
    path("timecard_report/<int:project_id>/<int:month>", views.report_timecards_customer, name="report-timecards-month"),
    path("timecard_overview", views.timecard_overview, name="timecard-overview"),
    path("timecard_detail_by_project/<int:project_id>/", views.timecard_detail_by_project, name="timecard-detail-by-project"),
    path("timecard_detail_by_project_month/<int:project_id>/<str:month>/", views.timecard_detail_by_project_month, name="timecard-detail-by-project-month"),
    path("timecarditem_update/<pk>", views.TimecardItemUpdateView.as_view(), name="timecarditem-update"),

    path("expenditure_overview", views.expenditure_overview, name="expenditure-overview"),
    path("detail_by_project/<int:project_id>/", views.expenditure_detail_by_project, name="detail_by_project"),
    path("detail_by_project_month/<int:project_id>/<str:month>/", views.expenditure_detail_by_project_month, name="detail_by_project_month"),
    path("project_update/<pk>", views.ProjectUpdateView.as_view(), name="project_update"),
    path("project_create", views.ProjectCreateView.as_view(), name="project_create"),
    path("project_delete/<int:project_id>", views.delete_project, name="project_delete"),
    path("milestone_create/<pk>", views.MilestoneCreateView.as_view(), name="milestone_create"),
    path("milestone_update/<pk>", views.MilestoneUpdateView.as_view(), name="milestone_update"),

    path("project_group_create", views.Project_GroupCreateView.as_view(), name="project_group_create"),
    path("project_group_detail/<int:project_group_id>", views.project_group_detail, name="project_group_detail"),
    path("report_timecards_by_group/<int:project_group_id>", views.report_timecards_by_group, name="report_timecards_by_group"),
    path("report_timecards_by_group_by_month/<int:project_group_id>/<str:month>/", views.report_timecards_by_group_by_month, name="report_timecards_by_group_by_month"),
]