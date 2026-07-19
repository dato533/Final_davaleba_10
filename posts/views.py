from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import PostForm, CommentForm, RepostForm
from .models import Post, PostMedia, Comment, Like
from users.models import Notification
from django.urls import reverse
from django.db.models import Q

import os
from django.conf import settings


# def save_post_media(post, media_files):
#     for media_file in media_files:
#         if media_file.content_type.startswith('image/'):
#             media_type = 'image'
#         else:
#             media_type = 'video'

#         PostMedia.objects.create(post=post, file=media_file, media_type=media_type)


# def save_post_media(post, media_files):
#     print('MEDIA_ROOT:', settings.MEDIA_ROOT)

#     for media_file in media_files:
#         if media_file.content_type.startswith('image/'):
#             media_type = 'image'
#         else:
#             media_type = 'video'

#         media = PostMedia.objects.create(
#             post=post,
#             file=media_file,
#             media_type=media_type
#         )

#         print('FILE NAME:', media.file.name)
#         print('FILE PATH:', media.file.path)
#         print('FILE EXISTS:', os.path.exists(media.file.path))


import logging
import os

from django.conf import settings

from .models import PostMedia


logger = logging.getLogger(__name__)


def save_post_media(post, media_files):
    logger.warning('MEDIA_ROOT: %s', settings.MEDIA_ROOT)

    for media_file in media_files:
        if media_file.content_type.startswith('image/'):
            media_type = 'image'
        else:
            media_type = 'video'

        media = PostMedia.objects.create(
            post=post,
            file=media_file,
            media_type=media_type
        )

        logger.warning('FILE NAME: %s', media.file.name)
        logger.warning('FILE PATH: %s', media.file.path)
        logger.warning('FILE EXISTS: %s', os.path.exists(media.file.path))


@login_required
def feed(request):
    feed_type = request.GET.get('type', 'friends')

    friends = request.user.get_friends().select_related('profile')
    friend_ids = friends.values_list('id', flat=True)

    posts_query = Post.objects.select_related(
        'author',
        'author__profile'
    ).prefetch_related(
        'media',
        'likes',
        'comments'
    )

    if feed_type == 'all':
        posts = posts_query.all()
    else:
        posts = posts_query.filter(
            Q(author=request.user) |
            Q(author_id__in=friend_ids)
        )

    user_reactions = {
        reaction.post_id: reaction.reaction_type
        for reaction in Like.objects.filter(
            user=request.user,
            post__in=posts
        )
    }

    for post in posts:
        post.user_reaction = user_reactions.get(post.id)

    recent_friends = friends[:6]

    recent_notifications = request.user.notifications.select_related(
        'sender',
        'sender__profile'
    )[:5]

    return render(request, 'posts/feed.html', {
        'posts': posts,
        'feed_type': feed_type,
        'recent_friends': recent_friends,
        'recent_notifications': recent_notifications,
    })


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()

            media_files = form.cleaned_data.get('media_files')

            if media_files:
                save_post_media(post, media_files)

            messages.success(request, 'Your post was created successfully.')
            return redirect('posts:feed')
    else:
        form = PostForm()

    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_detail(request, post_id):
    post = Post.objects.select_related(
        'author',
        'author__profile',
        'shared_post',
        'shared_post__author',
        'shared_post__author__profile'
    ).prefetch_related(
        'media',
        'likes',
        'comments__author',
        'comments__author__profile'
    ).filter(
        id=post_id
    ).first()

    if not post:
        messages.error(request, 'This post no longer exists.')
        return redirect('posts:feed')

    comment_form = CommentForm()

    user_reaction = post.likes.filter(
        user=request.user
    ).first()

    next_url = request.GET.get('next')

    return render(request, 'posts/post_detail.html', {
        'post': post,
        'comment_form': comment_form,
        'user_reaction': user_reaction,
        'next_url': next_url,
    })


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post.objects.prefetch_related('media'), id=post_id)

    if post.author != request.user:
        messages.error(request, 'You are not allowed to edit this post.')
        return redirect('posts:post_detail', post_id=post.id)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            media_files = form.cleaned_data.get('media_files')
            deleted_media_ids = request.POST.getlist('deleted_media')
            current_media_count = post.media.exclude(id__in=deleted_media_ids).count()
            new_media_count = len(media_files) if media_files else 0

            if current_media_count + new_media_count > 10:
                messages.error(request, f'You can add only {10 - current_media_count} more files.')
            else:
                form.save()

                if deleted_media_ids:
                    post.media.filter(id__in=deleted_media_ids).delete()

                if media_files:
                    save_post_media(post, media_files)

                messages.success(request, 'Your post was updated successfully.')
                return redirect('posts:post_detail', post_id=post.id)
    else:
        form = PostForm(instance=post)

    return render(request, 'posts/edit_post.html', {'form': form, 'post': post})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        messages.error(request, 'You are not allowed to delete this post.')
        return redirect(
            'posts:post_detail',
            post_id=post.id
        )

    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Your post was deleted successfully.')
        return redirect('posts:feed')

    return render(
        request,
        'posts/delete_post.html',
        {'post': post}
    )


@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        reaction_type = request.POST.get('reaction_type', 'like')

        allowed_reactions = {
            'like',
            'love',
            'haha',
            'wow',
            'sad',
            'angry',
        }

        if reaction_type not in allowed_reactions:
            reaction_type = 'like'

        reaction = Like.objects.filter(
            user=request.user,
            post=post
        ).first()

        if reaction:
            if reaction.reaction_type == reaction_type:
                reaction.delete()

                Notification.objects.filter(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='like',
                    url=f'/{post.id}/'
                ).delete()
            else:
                reaction.reaction_type = reaction_type
                reaction.save()

                if post.author != request.user:
                    Notification.objects.update_or_create(
                        recipient=post.author,
                        sender=request.user,
                        notification_type='like',
                        url=f'/{post.id}/',
                        defaults={
                            'text': (
                                f'{request.user.first_name} '
                                f'{request.user.last_name} reacted to your post.'
                            )
                        }
                    )
        else:
            Like.objects.create(
                user=request.user,
                post=post,
                reaction_type=reaction_type
            )

            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='like',
                    text=(
                        f'{request.user.first_name} '
                        f'{request.user.last_name} reacted to your post.'
                    ),
                    url=f'/{post.id}/'
                )

    next_url = request.POST.get('next')

    if next_url:
        return redirect(next_url)

    return redirect(
        'posts:post_detail',
        post_id=post.id
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()

            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='comment',
                    text=(
                        f'{request.user.first_name} '
                        f'{request.user.last_name} commented on your post.'
                    ),
                    url=f'/{post.id}/#comments'
                )

            messages.success(
                request,
                'Your comment was added successfully.'
            )

    return redirect(
        f'{reverse("posts:post_detail", args=[post.id])}#comments'
    )


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.author != request.user:
        messages.error(request, 'You are not allowed to delete this comment.')
        return redirect(
            'posts:post_detail',
            post_id=comment.post.id
        )

    if request.method == 'POST':
        post_id = comment.post.id
        comment.delete()
        messages.success(request, 'Your comment was deleted successfully.')

        return redirect(
            'posts:post_detail',
            post_id=post_id
        )

    return redirect(
        'posts:post_detail',
        post_id=comment.post.id
    )


@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.author != request.user:
        messages.error(request, 'You are not allowed to edit this comment.')
        return redirect(
            'posts:post_detail',
            post_id=comment.post.id
        )

    if request.method == 'POST':
        form = CommentForm(
            request.POST,
            instance=comment
        )

        if form.is_valid():
            form.save()
            messages.success(request, 'Your comment was updated successfully.')

            return redirect(
                'posts:post_detail',
                post_id=comment.post.id
            )
    else:
        form = CommentForm(instance=comment)

    return render(
        request,
        'posts/edit_comment.html',
        {
            'form': form,
            'comment': comment
        }
    )


@login_required
def repost_post(request, post_id):
    original_post = get_object_or_404(Post, id=post_id)

    if original_post.shared_post:
        original_post = original_post.shared_post

    if request.method == 'POST':
        form = RepostForm(request.POST)

        if form.is_valid():
            repost = Post.objects.create(
                author=request.user,
                text=form.cleaned_data['text'],
                shared_post=original_post
            )

            if original_post.author != request.user:
                Notification.objects.create(
                    recipient=original_post.author,
                    sender=request.user,
                    notification_type='repost',
                    text=(
                        f'{request.user.first_name} '
                        f'{request.user.last_name} shared your post.'
                    ),
                    url=f'/{repost.id}/'
                )

            messages.success(request, 'Post shared successfully.')

            return redirect(
                'posts:post_detail',
                post_id=repost.id
            )
    else:
        form = RepostForm()

    return render(request, 'posts/repost_post.html', {
        'form': form,
        'original_post': original_post
    })


