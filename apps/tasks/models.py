from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TaskStudioTask(models.Model):
    """Model for TaskStudio tasks - separate from the existing session tasks"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic task information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Scheduling information
    scheduled_date = models.DateTimeField()
    estimated_duration = models.PositiveIntegerField(help_text="Duration in minutes")
    
    # Assignment and organization
    assigned_to = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, help_text="List of tags as strings")
    
    # User association
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taskstudio_tasks')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'scheduled_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.status})"
    
    @property
    def is_overdue(self):
        """Check if a scheduled task is overdue"""
        if self.status == 'scheduled' and self.scheduled_date < timezone.now():
            return True
        return False
    
    def get_duration_display(self):
        """Return formatted duration string"""
        hours = self.estimated_duration // 60
        minutes = self.estimated_duration % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
