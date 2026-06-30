from django.core.management.base import BaseCommand
from django.utils import timezone
from leads.models import FollowUp, Task, Meeting, Notification


class Command(BaseCommand):
    help = 'Create notifications for overdue tasks, due followups and today meetings'

    def handle(self, *args, **options):
        today = timezone.localdate()
        now = timezone.now()
        created = 0

        # followups due today
        for fu in FollowUp.objects.filter(status='pending', follow_up_date__date=today).select_related('lead'):
            # notify all admins and sales managers
            from django.contrib.auth.models import User
            for user in User.objects.filter(profile__role__in=['admin', 'sales_manager', 'sales_executive']):
                already = Notification.objects.filter(
                    user=user,
                    notif_type='followup_due',
                    link=f'/leads/{fu.lead.pk}/',
                    created_at__date=today
                ).exists()
                if not already:
                    Notification.objects.create(
                        user=user,
                        notif_type='followup_due',
                        title=f'Follow-up due: {fu.lead.name}',
                        message=f'Follow-up for "{fu.lead.name}" is due today.',
                        link=f'/leads/{fu.lead.pk}/',
                    )
                    created += 1

        # overdue tasks
        for task in Task.objects.filter(
            due_date__lt=today, status__in=['todo', 'in_progress']
        ).select_related('assigned_to', 'milestone__project'):
            if task.assigned_to:
                already = Notification.objects.filter(
                    user=task.assigned_to,
                    notif_type='task_overdue',
                    link=f'/projects/{task.milestone.project.pk}/',
                    created_at__date=today
                ).exists()
                if not already:
                    Notification.objects.create(
                        user=task.assigned_to,
                        notif_type='task_overdue',
                        title=f'Overdue task: {task.title}',
                        message=f'Task "{task.title}" in project "{task.milestone.project.name}" is overdue.',
                        link=f'/projects/{task.milestone.project.pk}/',
                    )
                    created += 1

        # meetings today
        for meeting in Meeting.objects.filter(
            scheduled_at__date=today, status='scheduled'
        ).select_related('created_by'):
            for attendee in meeting.attendees.all():
                already = Notification.objects.filter(
                    user=attendee,
                    notif_type='meeting_today',
                    link=f'/meetings/{meeting.pk}/',
                    created_at__date=today
                ).exists()
                if not already:
                    Notification.objects.create(
                        user=attendee,
                        notif_type='meeting_today',
                        title=f'Meeting today: {meeting.title}',
                        message=f'You have a meeting "{meeting.title}" scheduled for today.',
                        link=f'/meetings/{meeting.pk}/',
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} notifications.'))