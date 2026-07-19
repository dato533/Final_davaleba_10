from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from .models import CustomUser, FriendRequest, Friendship, Notification
from .forms import (
                    CustomPasswordChangeForm,
                    CustomUserRegisterForm,
                    DeleteAccountForm,
                    EditProfileForm,
                    EditUserForm,
                    EmailAuthenticationForm,
                    )


def register_user(request):
    if request.user.is_authenticated:
        return redirect('posts:feed')

    if request.method == 'POST':
        form = CustomUserRegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Your account was created successfully.')
            return redirect('posts:feed')
    else:
        form = CustomUserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


def login_user(request):
    if request.user.is_authenticated:
        return redirect('posts:feed')

    if request.method == 'POST':
        form = EmailAuthenticationForm(request=request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'You have logged in successfully.')

            next_url = request.GET.get('next')

            if next_url:
                return redirect(next_url)

            return redirect('posts:feed')
    else:
        form = EmailAuthenticationForm(request=request)

    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_user(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have logged out successfully.')
        return redirect('users:login')

    return redirect('posts:feed')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was changed successfully.')
            return redirect('posts:feed')
    else:
        form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'users/change_password.html', {'form': form})


@login_required
def profile_detail(request, user_id):
    profile_user = get_object_or_404(CustomUser, id=user_id)
    is_friend = request.user.is_friend_with(profile_user)

    sent_request = FriendRequest.objects.filter(
        sender=request.user,
        receiver=profile_user,
        status='pending'
    ).exists()

    received_request = FriendRequest.objects.filter(
        sender=profile_user,
        receiver=request.user,
        status='pending'
    ).first()

    friends_count = profile_user.get_friends().count()
    user_posts = profile_user.posts.prefetch_related('media', 'likes', 'comments').all()

    return render(request, 'users/profile_detail.html', {
        'profile_user': profile_user,
        'is_friend': is_friend,
        'sent_request': sent_request,
        'received_request': received_request,
        'friends_count': friends_count,
        'user_posts': user_posts
    })


@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = EditUserForm(request.POST, instance=request.user)
        profile_form = EditProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile was updated successfully.')
            return redirect('users:profile_detail', user_id=request.user.id)
    else:
        user_form = EditUserForm(instance=request.user)
        profile_form = EditProfileForm(instance=request.user.profile)

    return render(request, 'users/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def delete_account(request):
    if request.method == 'POST':
        form = DeleteAccountForm(request.user, request.POST)

        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, 'Your account was deleted successfully.')
            return redirect('users:login')
    else:
        form = DeleteAccountForm(request.user)

    return render(request, 'users/delete_account.html', {'form': form})


@login_required
def user_search(request):
    query = request.GET.get('q', '').strip()
    users = CustomUser.objects.none()

    if query:
        users = CustomUser.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(id=request.user.id)

    return render(request, 'users/user_search.html', {'users': users, 'query': query})


@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(CustomUser, id=user_id)

    if request.method != 'POST':
        return redirect('users:profile_detail', user_id=receiver.id)

    if receiver == request.user:
        messages.error(request, 'You cannot send a friend request to yourself.')
        return redirect('users:profile_detail', user_id=receiver.id)

    if request.user.is_friend_with(receiver):
        messages.info(request, 'You are already friends.')
        return redirect('users:profile_detail', user_id=receiver.id)

    reverse_request = FriendRequest.objects.filter(
        sender=receiver,
        receiver=request.user,
        status='pending'
    ).first()

    if reverse_request:
        messages.info(request, 'This user has already sent you a friend request.')
        return redirect('users:friend_requests')

    friend_request, created = FriendRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver,
        defaults={'status': 'pending'}
    )

    if not created and friend_request.status == 'declined':
        friend_request.status = 'pending'
        friend_request.save()

    if created or friend_request.status == 'pending':
        Notification.objects.get_or_create(
            recipient=receiver,
            sender=request.user,
            notification_type='friend_request',
            url='/users/friend-requests/',
            defaults={
                'text': (
                    f'{request.user.first_name} '
                    f'{request.user.last_name} sent you a friend request.'
                )
            }
        )

    messages.success(request, 'Friend request sent successfully.')
    return redirect('users:profile_detail', user_id=receiver.id)


@login_required
def friend_requests(request):
    requests = FriendRequest.objects.filter(
        receiver=request.user,
        status='pending'
    ).select_related('sender', 'sender__profile')

    return render(request, 'users/friend_requests.html', {'requests': requests})


@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        receiver=request.user,
        status='pending'
    )

    if request.method == 'POST':
        user1, user2 = sorted([friend_request.sender, friend_request.receiver], key=lambda user: user.id)

        Notification.objects.create(
            recipient=friend_request.sender,
            sender=request.user,
            notification_type='friend_accepted',
            text=f'{request.user.first_name} {request.user.last_name} accepted your friend request.',
            url=f'/users/profile/{request.user.id}/'
        )
        
        Friendship.objects.get_or_create(user1=user1, user2=user2)

        friend_request.status = 'accepted'
        friend_request.save()

        FriendRequest.objects.filter(
            sender=friend_request.receiver,
            receiver=friend_request.sender
        ).delete()

        messages.success(request, 'Friend request accepted.')

    return redirect('users:friend_requests')


@login_required
def decline_friend_request(request, request_id):
    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        receiver=request.user,
        status='pending'
    )

    if request.method == 'POST':
        friend_request.status = 'declined'
        friend_request.save()
        messages.success(request, 'Friend request declined.')

    return redirect('users:friend_requests')


@login_required
def friends_list(request, user_id=None):
    profile_user = request.user

    if user_id:
        profile_user = get_object_or_404(CustomUser, id=user_id)

    friends = profile_user.get_friends().select_related('profile')

    return render(request, 'users/friends_list.html', {
        'profile_user': profile_user,
        'friends': friends
    })


@login_required
def remove_friend(request, user_id):
    friend = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        friendship = Friendship.objects.filter(
            Q(user1=request.user, user2=friend) |
            Q(user1=friend, user2=request.user)
        ).first()

        if friendship:
            friendship.delete()

        FriendRequest.objects.filter(
            Q(sender=request.user, receiver=friend) |
            Q(sender=friend, receiver=request.user)
        ).delete()

        messages.success(request, 'Friend removed successfully.')

    return redirect('users:profile_detail', user_id=friend.id)


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related(
        'sender',
        'sender__profile'
    ).all()

    return render(request, 'users/notification_list.html', {
        'notifications': notifications
    })


@login_required
def open_notification(request, notification_id):
    notification = request.user.notifications.filter(
        id=notification_id
    ).first()

    if not notification:
        return redirect('users:notification_list')

    notification_url = notification.url
    notification.delete()

    if notification_url:
        return redirect(notification_url)

    return redirect('users:notification_list')


@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(
            is_read=False
        ).update(
            is_read=True
        )

        messages.success(
            request,
            'All notifications were marked as read.'
        )

    return redirect('users:notification_list')


@login_required
def delete_notification(request, notification_id):
    if request.method == 'POST':
        notification = request.user.notifications.filter(
            id=notification_id
        ).first()

        if notification:
            notification.delete()

    return redirect('users:notification_list')


@login_required
def delete_all_notifications(request):
    if request.method == 'POST':
        deleted_count, deleted_objects = request.user.notifications.all().delete()

        if deleted_count > 0:
            messages.success(
                request,
                'All notifications were deleted successfully.'
            )
        else:
            messages.info(
                request,
                'There are no notifications to delete.'
            )

    return redirect('users:notification_list')