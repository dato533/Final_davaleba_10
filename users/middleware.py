from datetime import timedelta
from django.utils import timezone
from .models import CustomUser


class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = timezone.now()
            last_activity = request.user.last_activity

            should_update = (
                not last_activity or
                current_time - last_activity >= timedelta(seconds=60)
            )

            if should_update:
                CustomUser.objects.filter(
                    id=request.user.id
                ).update(
                    last_activity=current_time
                )

                request.user.last_activity = current_time

        response = self.get_response(request)

        return response