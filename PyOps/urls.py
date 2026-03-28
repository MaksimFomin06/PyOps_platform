from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('internal_accounting/', lambda request: redirect('internal_accounting:adult:student_list')),
    path('internal_accounting/', include('internal_accounting.urls', namespace='internal_accounting')),
    path('instructor/', include('instructor.urls', namespace='instructor')),
]