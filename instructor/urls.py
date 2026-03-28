from django.urls import path
from . import views

app_name = 'instructor'

urlpatterns = [
    path('', views.instructor_dashboard, name='dashboard'),
    path('admin/', views.admin_panel, name='admin_panel'),
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/add/', views.add_session, name='add_session'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/confirm/', views.confirm_session, name='confirm_session'),
    path('sessions/<int:pk>/reject/', views.reject_session, name='reject_session'),
    path('sessions/bulk-confirm/', views.bulk_confirm, name='bulk_confirm'),
    path('instructor/<str:instructor_id>/', views.instructor_sessions, name='instructor_sessions'),
    path('ajax/search-student/', views.search_student, name='ajax_search_student'),
]