from django.db import models
from apps.core.models import BaseModel
from django.conf import settings
from decimal import Decimal


class SavingsGoal(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_goals')
    title = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    saved_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='TZS')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    target_date = models.DateField(null=True, blank=True)
    color = models.CharField(max_length=20, default='#10B981')

    def __str__(self):
        return f"{self.title} - {self.saved_amount}/{self.target_amount} {self.currency}"

    @property
    def progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return min(int((self.saved_amount / self.target_amount) * 100), 100)

    @property
    def is_complete(self):
        return self.saved_amount >= self.target_amount


class SavingsContribution(BaseModel):
    class Type(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAW = 'WITHDRAW', 'Withdraw'

    goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='contributions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=Type.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=50, unique=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.type} - {self.amount} - {self.goal.title}"
