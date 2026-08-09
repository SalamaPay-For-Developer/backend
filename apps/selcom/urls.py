from django.urls import path
from .views import (
    WalletNameLookupView,
    BankNameLookupView,
    SendMoneyView,
    IMTTransactionStatusView,
    UtilityPaymentView,
    UtilityLookupView,
    UtilityPaymentStatusView,
    WalletCashinView,
    WalletCashinLookupView,
    WalletCashinStatusView,
    SelcomPesaCashinView,
    SelcomPesaLookupView,
    SelcomPesaStatusView,
    AgentCashoutView,
    AgentCashoutStatusView,
    FloatBalanceView,
    QwiksendProcessView,
    QwiksendLookupView,
    QwiksendStatusView,
    VCNCreateView,
    VCNCreateStatusView,
    VCNChangeStatusView,
    VCNShowView,
    VCNStatusView,
    VCNSetLimitView,
    CreateOrderMinimalView,
    CancelOrderView,
    ListOrdersView,
    StoredCardsView,
    DeleteCardView,
    CardPaymentView,
    WalletPaymentView,
    SelcomPesaPaymentView,
    CreateTillAliasView,
    WalletPushUssdView,
    C2BQueryStatusView,
    InitiatePosPaymentView,
    PosPaymentStatusView,
)

urlpatterns = [
    # IMT
    path('wallet-name-lookup/', WalletNameLookupView.as_view(), name='wallet-name-lookup'),
    path('bank-name-lookup/', BankNameLookupView.as_view(), name='bank-name-lookup'),
    path('send-money/', SendMoneyView.as_view(), name='imt-send-money'),
    path('transaction-status/', IMTTransactionStatusView.as_view(), name='imt-transaction-status'),

    # Utility Payments
    path('utility-payment/', UtilityPaymentView.as_view(), name='utility-payment'),
    path('utility-lookup/', UtilityLookupView.as_view(), name='utility-lookup'),
    path('utility-payment/status/', UtilityPaymentStatusView.as_view(), name='utility-payment-status'),

    # Wallet Cashin
    path('wallet-cashin/', WalletCashinView.as_view(), name='wallet-cashin'),
    path('wallet-cashin/lookup/', WalletCashinLookupView.as_view(), name='wallet-cashin-lookup'),
    path('wallet-cashin/status/', WalletCashinStatusView.as_view(), name='wallet-cashin-status'),

    # Selcom Pesa
    path('selcompesa/cashin/', SelcomPesaCashinView.as_view(), name='selcompesa-cashin'),
    path('selcompesa/lookup/', SelcomPesaLookupView.as_view(), name='selcompesa-lookup'),
    path('selcompesa/status/', SelcomPesaStatusView.as_view(), name='selcompesa-status'),

    # Agent Cashout
    path('agent-cashout/', AgentCashoutView.as_view(), name='agent-cashout'),
    path('agent-cashout/status/', AgentCashoutStatusView.as_view(), name='agent-cashout-status'),

    # Float Account
    path('float/balance/', FloatBalanceView.as_view(), name='float-balance'),

    # Qwiksend (Bank Transfer)
    path('qwiksend/process/', QwiksendProcessView.as_view(), name='qwiksend-process'),
    path('qwiksend/lookup/', QwiksendLookupView.as_view(), name='qwiksend-lookup'),
    path('qwiksend/status/', QwiksendStatusView.as_view(), name='qwiksend-status'),

    # VCN
    path('vcn/create/', VCNCreateView.as_view(), name='vcn-create'),
    path('vcn/create-status/', VCNCreateStatusView.as_view(), name='vcn-create-status'),
    path('vcn/change-status/', VCNChangeStatusView.as_view(), name='vcn-change-status'),
    path('vcn/show/', VCNShowView.as_view(), name='vcn-show'),
    path('vcn/status/', VCNStatusView.as_view(), name='vcn-status'),
    path('vcn/set-limit/', VCNSetLimitView.as_view(), name='vcn-set-limit'),

    # Checkout
    path('checkout/create-order-minimal/', CreateOrderMinimalView.as_view(), name='create-order-minimal'),
    path('checkout/cancel-order/', CancelOrderView.as_view(), name='cancel-order'),
    path('checkout/list-orders/', ListOrdersView.as_view(), name='list-orders'),
    path('checkout/stored-cards/', StoredCardsView.as_view(), name='stored-cards'),
    path('checkout/delete-card/', DeleteCardView.as_view(), name='delete-card'),
    path('checkout/card-payment/', CardPaymentView.as_view(), name='card-payment'),
    path('checkout/wallet-payment/', WalletPaymentView.as_view(), name='wallet-payment'),
    path('checkout/selcompesa-payment/', SelcomPesaPaymentView.as_view(), name='selcompesa-payment'),
    path('checkout/create-till-alias/', CreateTillAliasView.as_view(), name='create-till-alias'),

    # C2B / Wallet Pull
    path('wallet/push-ussd/', WalletPushUssdView.as_view(), name='wallet-push-ussd'),
    path('c2b/query-status/', C2BQueryStatusView.as_view(), name='c2b-query-status'),

    # POS
    path('pos/initiate/', InitiatePosPaymentView.as_view(), name='pos-initiate'),
    path('pos/status/', PosPaymentStatusView.as_view(), name='pos-status'),
]
