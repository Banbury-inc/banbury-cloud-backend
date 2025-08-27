from django.urls import path
from . import views

urlpatterns = [
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('create-subscription-intent/', views.create_subscription_intent, name='create_subscription_intent'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('check-payment-status/', views.check_payment_status, name='check_payment_status'),
    path('verify-payment-intent/', views.verify_payment_intent, name='verify_payment_intent'),
    path('cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),
]
