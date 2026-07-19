from django.urls import path
from . import views


app_name = 'chat'

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('private/<int:user_id>/', views.start_private_conversation, name='start_private_conversation'),
    path('group/create/', views.create_group, name='create_group'),
    path('<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('<int:conversation_id>/messages/older/', views.load_older_messages, name='load_older_messages'),
    path('<int:conversation_id>/member/add/', views.add_group_member, name='add_group_member'),
    path('<int:conversation_id>/member/<int:user_id>/remove/', views.remove_group_member, name='remove_group_member'),
    path('<int:conversation_id>/leave/', views.leave_group, name='leave_group'),
]