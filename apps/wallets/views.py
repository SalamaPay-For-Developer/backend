from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models, transaction as db_transaction
from decimal import Decimal
import uuid
from .models import Wallet, LedgerEntry
from .savings_models import SavingsGoal, SavingsContribution
from .serializers import (
    WalletSerializer, LedgerEntrySerializer,
    SavingsGoalSerializer, SavingsContributionSerializer
)
from apps.accounts.models import User


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return Wallet.objects.all()
        return Wallet.objects.filter(
            models.Q(owner=user) | models.Q(business__owner=user) | models.Q(business__members__user=user)
        ).distinct()


class LedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LedgerEntry.objects.all()
    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return LedgerEntry.objects.all()
        return LedgerEntry.objects.filter(
            models.Q(wallet__owner=user) | models.Q(wallet__business__owner=user) | models.Q(wallet__business__members__user=user)
        ).distinct()


class SavingsGoalViewSet(viewsets.ModelViewSet):
    serializer_class = SavingsGoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavingsGoal.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        goal = self.get_object()
        amount = request.data.get('amount')
        if not amount:
            return Response({"detail": "Amount is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"detail": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            goal.saved_amount += amount
            if goal.saved_amount >= goal.target_amount:
                goal.status = SavingsGoal.Status.COMPLETED
            goal.save()
            contrib = SavingsContribution.objects.create(
                goal=goal,
                user=request.user,
                type=SavingsContribution.Type.DEPOSIT,
                amount=amount,
                reference=f"SV-{uuid.uuid4().hex[:10].upper()}",
                note=request.data.get('note', '')
            )

        return Response({
            "goal": SavingsGoalSerializer(goal).data,
            "contribution": SavingsContributionSerializer(contrib).data,
            "message": "Deposit successful"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        goal = self.get_object()
        amount = request.data.get('amount')
        if not amount:
            return Response({"detail": "Amount is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"detail": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)
        if amount > goal.saved_amount:
            return Response({"detail": "Insufficient savings."}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            goal.saved_amount -= amount
            if goal.saved_amount == 0:
                goal.status = SavingsGoal.Status.WITHDRAWN
            goal.save()
            contrib = SavingsContribution.objects.create(
                goal=goal,
                user=request.user,
                type=SavingsContribution.Type.WITHDRAW,
                amount=amount,
                reference=f"SV-{uuid.uuid4().hex[:10].upper()}",
                note=request.data.get('note', '')
            )

        return Response({
            "goal": SavingsGoalSerializer(goal).data,
            "contribution": SavingsContributionSerializer(contrib).data,
            "message": "Withdrawal successful"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def contributions(self, request, pk=None):
        goal = self.get_object()
        contribs = goal.contributions.all().order_by('-created_at')
        serializer = SavingsContributionSerializer(contribs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        goals = self.get_queryset()
        total_saved = goals.aggregate(total=models.Sum('saved_amount'))['total'] or Decimal('0.00')
        total_target = goals.aggregate(total=models.Sum('target_amount'))['total'] or Decimal('0.00')
        active_count = goals.filter(status=SavingsGoal.Status.ACTIVE).count()
        completed_count = goals.filter(status=SavingsGoal.Status.COMPLETED).count()
        return Response({
            "total_saved": str(total_saved),
            "total_target": str(total_target),
            "active_count": active_count,
            "completed_count": completed_count,
            "goals_count": goals.count(),
        })
