from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('browse/', views.browse_listings, name='browse_listings'),
    path('listing/<int:listing_id>/', views.listing_detail, name='listing_detail'),
    path('listing/<int:listing_id>/purchase/', views.purchase_listing, name='purchase_listing'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('sell/', views.sell_item, name='sell_item'),
    path('my-listings/', views.my_listings, name='my_listings'),
    path('listing/<int:listing_id>/cancel/', views.cancel_listing, name='cancel_listing'),
    path('deposit/', views.deposit_funds, name='deposit_funds'),
    path('orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('logout/', views.logout_view, name='logout'),
]
