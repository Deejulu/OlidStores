from django.urls import path
from . import views

app_name = 'doc_converter'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_file, name='upload'),
    path('edit/<str:task_id>/', views.edit_docx, name='edit_docx'),
    path('save-edited/', views.save_edited_docx, name='save_edited_docx'),
    path('download/<str:task_id>/', views.download_file, name='download'),
]
