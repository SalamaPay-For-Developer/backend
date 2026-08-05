from django.db import models
from apps.core.models import BaseModel
from django.conf import settings
from decimal import Decimal


class Wallet(BaseModel):
    class WalletType(models.TextChoices):
        PERSONAL = 'PERSONAL', 'Personal'
        BUSINESS = 'BUSINESS', 'Business'

    wallet_type = models.CharField(max_length=10, choices=WalletType.choices, default=WalletType.PERSONAL)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallets', null=True, blank=True)
    business = models.ForeignKey('accounts.Business', on_delete=models.CASCADE, related_name='wallets', null=True, blank=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='TZS')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.wallet_type == self.WalletType.BUSINESS and self.business:
            return f"Business Wallet: {self.business.business_name} - {self.balance} {self.currency}"
        if self.owner:
            return f"Personal Wallet: {self.owner.phone_number} - {self.balance} {self.currency}"
        return f"Wallet {self.id} - {self.balance} {self.currency}"

    def update_balance(self):
        """Recalculate balance from ledger entries."""
        credits = self.ledger_entries.filter(entry_type=LedgerEntry.EntryType.CREDIT).aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        debits = self.ledger_entries.filter(entry_type=LedgerEntry.EntryType.DEBIT).aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        self.balance = credits - debits
        self.save()

class LedgerEntry(BaseModel):
    class EntryType(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit (In)'
        DEBIT = 'DEBIT', 'Debit (Out)'

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='ledger_entries')
    transaction = models.ForeignKey('payments.Transaction', on_delete=models.PROTECT, related_name='ledger_entries')
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    narration = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.entry_type} - {self.amount} - Wallet: {self.wallet.id}"

    class Meta:
        verbose_name_plural = "Ledger Entries"
        ordering = ['-created_at']
