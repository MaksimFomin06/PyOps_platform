from django.urls import path, include

app_name = 'internal_accounting'

urlpatterns = [
    # Взрослые студенты
    path('adult/', include('internal_accounting.urls.adult_urls', namespace='adult')),
    
    # Детские студенты
    path('child/', include('internal_accounting.urls.child_urls', namespace='child')),
]