import random
from django.core.management.base import BaseCommand
from posts.models import Post
from users.models import CustomUser, Friendship


class Command(BaseCommand):
    help = 'Creates demo users, friendships, and posts.'

    def handle(self, *args, **options):
        first_names = [
            'John',
            'Emma',
            'Michael',
            'Olivia',
            'Daniel',
            'Sophia',
            'David',
            'Emily',
            'James',
            'Isabella',
        ]

        last_names = [
            'Smith',
            'Johnson',
            'Brown',
            'Williams',
            'Jones',
            'Miller',
            'Davis',
            'Wilson',
            'Taylor',
            'Anderson',
        ]

        created_users = []

        for index in range(10):
            email = f'demo{index + 1}@example.com'

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_names[index],
                    'last_name': last_names[index],
                }
            )

            if created:
                user.set_password('DemoPassword123')
                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created user: {user.email}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'User already exists: {user.email}'
                    )
                )

            created_users.append(user)

        for user in created_users:
            current_posts_count = user.posts.count()

            posts_to_create = 2 - current_posts_count

            for post_number in range(posts_to_create):
                Post.objects.create(
                    author=user,
                    text=(
                        f'Demo post {post_number + 1} '
                        f'from {user.first_name} {user.last_name}.'
                    )
                )

        friendships_created = 0

        for user in created_users:
            possible_friends = [
                friend
                for friend in created_users
                if friend != user and not user.is_friend_with(friend)
            ]

            random.shuffle(possible_friends)

            for friend in possible_friends[:2]:
                user1, user2 = sorted(
                    [user, friend],
                    key=lambda current_user: current_user.id
                )

                friendship, created = Friendship.objects.get_or_create(
                    user1=user1,
                    user2=user2
                )

                if created:
                    friendships_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                'Demo data created successfully.'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Users processed: {len(created_users)}'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Friendships created: {friendships_created}'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Password for demo users: DemoPassword123'
            )
        )