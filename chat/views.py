from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from users.models import CustomUser, Notification
from .consumers import ACTIVE_CHAT_USERS
from .forms import GroupConversationForm, MessageForm
from .models import Conversation, Message


MESSAGE_PAGE_SIZE = 50


def notify_conversation_inboxes(conversation, action='updated'):
    channel_layer = get_channel_layer()

    for participant_id in conversation.participants.values_list('id', flat=True):
        async_to_sync(channel_layer.group_send)(
            f'chat_inbox_{participant_id}',
            {
                'type': 'conversation_updated',
                'conversation_id': conversation.id,
                'action': action,
            }
        )


def get_sender_name(user):
    sender_name = f'{user.first_name} {user.last_name}'.strip()
    return sender_name or user.email


def serialize_message_for_socket(message, user):
    sender_avatar = ''

    if hasattr(user, 'profile') and user.profile.avatar:
        sender_avatar = user.profile.avatar.url

    return {
        'type': 'chat_message',
        'message_id': message.id,
        'message': message.text,
        'sender_id': user.id,
        'sender_name': get_sender_name(user),
        'sender_avatar': sender_avatar,
        'created_at': message.created_at.strftime('%H:%M'),
        'is_read': message.is_read,
        'is_edited': bool(message.edited_at),
        'image_url': message.image.url if message.image else '',
        'video_url': message.video.url if message.video else '',
        'file_url': message.file.url if message.file else '',
        'file_name': message.file.name.split('/')[-1] if message.file else '',
    }


@login_required
def conversation_list(request):
    conversations = request.user.conversations.prefetch_related(
        'participants',
        'participants__profile',
        'messages',
        'messages__sender'
    ).annotate(
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    )

    for conversation in conversations:
        if conversation.conversation_type == 'private':
            conversation.other_user = conversation.participants.exclude(
                id=request.user.id
            ).first()
        else:
            conversation.other_user = None

    return render(request, 'chat/conversation_list.html', {
        'conversations': conversations
    })


@login_required
def start_private_conversation(request, user_id):
    other_user = get_object_or_404(CustomUser, id=user_id)

    if other_user == request.user:
        messages.error(request, 'You cannot start a conversation with yourself.')
        return redirect('chat:conversation_list')

    if not request.user.is_friend_with(other_user):
        messages.error(request, 'You can start a conversation only with your friends.')
        return redirect('users:profile_detail', user_id=other_user.id)

    conversation = Conversation.objects.filter(
        conversation_type='private',
        participants=request.user
    ).filter(participants=other_user).distinct().first()

    if not conversation:
        conversation = Conversation.objects.create(
            conversation_type='private',
            created_by=request.user
        )
        conversation.participants.add(request.user, other_user)
        notify_conversation_inboxes(conversation, 'created')

    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related(
            'participants',
            'participants__profile'
        ),
        id=conversation_id,
        participants=request.user
    )

    room_group_name = f'chat_{conversation.id}'
    channel_layer = get_channel_layer()

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)

        if form.is_valid():
            active_users = ACTIVE_CHAT_USERS.get(str(conversation.id), {})
            active_user_ids = list(active_users.keys())

            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.is_read = False
            message.save()

            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])

            recipients = conversation.participants.exclude(
                id=request.user.id
            ).exclude(id__in=active_user_ids)

            notifications = [
                Notification(
                    recipient=participant,
                    sender=request.user,
                    notification_type='message',
                    text=f'{get_sender_name(request.user)} sent you a message.',
                    url=f'/chat/{conversation.id}/'
                )
                for participant in recipients
            ]

            if notifications:
                Notification.objects.bulk_create(notifications)

            async_to_sync(channel_layer.group_send)(
                room_group_name,
                serialize_message_for_socket(message, request.user)
            )

            notify_conversation_inboxes(conversation, 'created')

            return redirect('chat:conversation_detail', conversation_id=conversation.id)
    else:
        form = MessageForm()

    unread_messages = conversation.messages.filter(
        is_read=False
    ).exclude(sender=request.user)

    read_message_ids = list(unread_messages.values_list('id', flat=True))

    if read_message_ids:
        unread_messages.update(is_read=True)

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'messages_read',
                'message_ids': read_message_ids,
                'reader_id': request.user.id,
            }
        )
        notify_conversation_inboxes(conversation, 'read')

    messages_qs = conversation.messages.select_related(
        'sender',
        'sender__profile'
    ).order_by('-created_at')

    latest_messages = list(messages_qs[:MESSAGE_PAGE_SIZE])
    latest_messages.reverse()
    oldest_message_id = latest_messages[0].id if latest_messages else None
    has_older_messages = bool(
        oldest_message_id and messages_qs.filter(id__lt=oldest_message_id).exists()
    )

    other_user = None

    if conversation.conversation_type == 'private':
        other_user = conversation.get_private_chat_user(request.user)

    return render(request, 'chat/conversation_detail.html', {
        'conversation': conversation,
        'other_user': other_user,
        'form': form,
        'chat_messages': latest_messages,
        'oldest_message_id': oldest_message_id,
        'has_older_messages': has_older_messages,
    })


@login_required
def load_older_messages(request, conversation_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )

    try:
        before_id = int(request.GET.get('before', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid message cursor.'}, status=400)

    older_messages = list(
        Message.objects.filter(
            conversation=conversation,
            id__lt=before_id
        ).select_related(
            'sender',
            'sender__profile'
        ).order_by('-created_at')[:MESSAGE_PAGE_SIZE]
    )

    older_messages.reverse()
    next_before = older_messages[0].id if older_messages else None
    has_more = bool(
        next_before and Message.objects.filter(
            conversation=conversation,
            id__lt=next_before
        ).exists()
    )

    html = ''.join(
        render_to_string(
            'chat/includes/message_item.html',
            {
                'message': message,
                'conversation': conversation,
                'request': request,
            },
            request=request
        )
        for message in older_messages
    )

    return JsonResponse({
        'html': html,
        'next_before': next_before,
        'has_more': has_more,
    })


@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupConversationForm(request.user, request.POST, request.FILES)

        if form.is_valid():
            conversation = form.save(commit=False)
            conversation.conversation_type = 'group'
            conversation.created_by = request.user
            conversation.save()
            form.save_m2m()
            conversation.participants.add(request.user)
            notify_conversation_inboxes(conversation, 'created')
            messages.success(request, 'Group chat created successfully.')
            return redirect('chat:conversation_detail', conversation_id=conversation.id)
    else:
        form = GroupConversationForm(request.user)

    return render(request, 'chat/create_group.html', {'form': form})


@login_required
def add_group_member(request, conversation_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        conversation_type='group',
        created_by=request.user
    )

    if request.method == 'POST':
        user_id = request.POST.get('user_id')

        if not user_id:
            messages.error(request, 'Please select a user.')
            return redirect('chat:conversation_detail', conversation_id=conversation.id)

        user = get_object_or_404(CustomUser, id=user_id)

        if not request.user.is_friend_with(user):
            messages.error(request, 'You can add only your friends.')
            return redirect('chat:conversation_detail', conversation_id=conversation.id)

        if conversation.participants.filter(id=user.id).exists():
            messages.info(request, 'This user is already a group member.')
            return redirect('chat:conversation_detail', conversation_id=conversation.id)

        conversation.participants.add(user)

        Notification.objects.create(
            recipient=user,
            sender=request.user,
            notification_type='group_added',
            text=(
                f'{request.user.first_name} {request.user.last_name} '
                f'added you to the group "{conversation.name}".'
            ),
            url=f'/chat/{conversation.id}/'
        )

        notify_conversation_inboxes(conversation, 'member_added')
        messages.success(request, 'Member added successfully.')

    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
def remove_group_member(request, conversation_id, user_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        conversation_type='group',
        created_by=request.user
    )
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method != 'POST':
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    if user == request.user:
        messages.error(request, 'Use the Leave group button to leave the group.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    if not conversation.participants.filter(id=user.id).exists():
        messages.error(request, 'This user is not a group member.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    removed_user_id = user.id
    conversation.participants.remove(user)
    notify_conversation_inboxes(conversation, 'member_removed')

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_inbox_{removed_user_id}',
        {
            'type': 'conversation_updated',
            'conversation_id': conversation.id,
            'action': 'removed',
        }
    )

    messages.success(request, 'Member removed successfully.')
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
def leave_group(request, conversation_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        conversation_type='group',
        participants=request.user
    )

    if request.method == 'POST':
        leaving_user_id = request.user.id
        remaining_participants = conversation.participants.exclude(id=request.user.id)

        if conversation.created_by == request.user:
            new_admin = remaining_participants.first()

            if new_admin:
                conversation.created_by = new_admin
                conversation.save(update_fields=['created_by'])
            else:
                conversation.delete()
                messages.success(request, 'The group was deleted.')
                return redirect('chat:conversation_list')

        conversation.participants.remove(request.user)
        notify_conversation_inboxes(conversation, 'member_left')

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_inbox_{leaving_user_id}',
            {
                'type': 'conversation_updated',
                'conversation_id': conversation.id,
                'action': 'left',
            }
        )

        messages.success(request, 'You left the group.')

    return redirect('chat:conversation_list')
