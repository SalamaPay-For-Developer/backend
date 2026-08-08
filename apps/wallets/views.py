from rest_framework import viewsets, permissions
from django.db import models
from .models import Wallet, LedgerEntry
from .serializers import WalletSerializer, LedgerEntrySerializer
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
