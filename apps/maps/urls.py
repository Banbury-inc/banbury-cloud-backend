from django.urls import path
from . import views

urlpatterns = [
    path('places/', views.places_list, name='maps-places'),
    path('places/<str:place_id>/', views.place_detail, name='maps-place-detail'),
]
