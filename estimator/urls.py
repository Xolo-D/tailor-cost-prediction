from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),

    # Core estimator
    path('estimator/',    views.estimator_view, name='estimator'),
    path('api/predict/',  views.predict_ajax,   name='predict_ajax'),
    path('api/chat/',     views.chat_predict,   name='chat_predict'),

    # History
    path('history/',                  views.history_view,    name='history'),
    path('history/delete/<int:pk>/',  views.delete_estimate, name='delete_estimate'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
]
