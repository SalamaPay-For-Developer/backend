from rest_framework import serializers
from .models import Wallet, LedgerEntry
from .savings_models import SavingsGoal, SavingsContribution

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'

class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = '__all__'

class SavingsGoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = SavingsGoal
        fields = '__all__'
        read_only_fields = ('saved_amount', 'status')

class SavingsContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsContribution
        fields = '__all__'
        read_only_fields = ('reference',)
