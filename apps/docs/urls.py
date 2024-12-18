from django.urls import path
from . import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Schema generation endpoint
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI with custom styling
    path('api/docs/', SpectacularSwaggerView.as_view(
        url_name='schema',
        template_name='swagger-ui.html',  # Custom template
    ), name='swagger-ui'),
    
    # Redoc UI with custom styling
    path('api/redoc/', SpectacularRedocView.as_view(
        url_name='schema',
        template_name='redoc.html',  # Custom template
    ), name='redoc'),
]
