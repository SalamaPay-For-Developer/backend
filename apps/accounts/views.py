from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate
import random
from .models import User, Business, BusinessMember, BusinessKYC, KYCDocument
from .serializers import (
    UserSerializer, BusinessSerializer, BusinessMemberSerializer,
    BusinessKYCSerializer, KYCDocumentSerializer
)
from apps.core.sms_service import send_otp_sms, send_password_reset_sms
from apps.core.email_service import send_welcome_email, send_otp_email, send_password_reset_email


def generate_otp_code():
    return str(random.randint(100000, 999999))


class OTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp_code = request.data.get('otp_code')

        if not phone_number or not otp_code:
            return Response(
                {"detail": "Phone number and OTP code are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.otp_verified:
            return Response(
                {"detail": "Account is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.otp_verified = True
        user.is_verified = True
        user.save(update_fields=['otp_verified', 'is_verified'])

        return Response({
            "detail": "Account verified successfully.",
            "phone_number": user.phone_number,
            "verified": True
        })


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response(
                {"detail": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(phone_number=phone_number)
            send_password_reset_sms(phone_number)
            if user.email:
                send_password_reset_email(user.email, user.full_name)
        except User.DoesNotExist:
            pass

        return Response({
            "detail": "If this phone number exists, a reset code has been sent.",
            "phone_number": phone_number
        })


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        new_password = request.data.get('new_password')

        if not phone_number or not new_password:
            return Response(
                {"detail": "Phone number and new password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {"detail": "Password must be at least 6 characters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({"detail": "Password reset successfully."})


class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response(
                {"detail": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.otp_verified:
            return Response(
                {"detail": "Account is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_code = generate_otp_code()
        success, _ = send_otp_sms(phone_number, otp_code)
        if user.email:
            send_otp_email(user.email, otp_code, user.full_name)

        if success:
            return Response({"detail": "OTP code sent successfully."})
        else:
            return Response(
                {"detail": "Failed to send OTP. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            phone_number = response.data.get('phone_number')
            full_name = response.data.get('full_name', '')
            email = response.data.get('email')
            if phone_number:
                otp_code = generate_otp_code()
                send_otp_sms(phone_number, otp_code)
                if email:
                    send_welcome_email(email, full_name, phone_number)
                    send_otp_email(email, otp_code, full_name)
        return response

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_businesses(self, request):
        businesses = Business.objects.filter(owner=request.user)
        serializer = BusinessSerializer(businesses, many=True)
        return Response(serializer.data)


class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return Business.objects.all()
        member_business_ids = BusinessMember.objects.filter(user=user, is_active=True).values_list('business_id', flat=True)
        return Business.objects.filter(models.Q(owner=user) | models.Q(id__in=member_business_ids)).distinct()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def kyc(self, request, pk=None):
        business = self.get_object()
        kyc, created = BusinessKYC.objects.get_or_create(business=business)
        serializer = BusinessKYCSerializer(kyc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        business.kyc_status = Business.KYCStatus.PENDING
        business.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve_kyc(self, request, pk=None):
        if request.user.role != User.Role.ADMIN:
            return Response({"error": "Only admins can approve KYC"}, status=status.HTTP_403_FORBIDDEN)
        business = self.get_object()
        business.kyc_status = Business.KYCStatus.APPROVED
        business.save()
        if hasattr(business, 'kyc'):
            business.kyc.reviewed_by = request.user
            business.kyc.reviewed_at = timezone.now()
            business.kyc.save()
        return Response({"message": "Business KYC approved"})

    @action(detail=True, methods=['post'])
    def reject_kyc(self, request, pk=None):
        if request.user.role != User.Role.ADMIN:
            return Response({"error": "Only admins can reject KYC"}, status=status.HTTP_403_FORBIDDEN)
        business = self.get_object()
        business.kyc_status = Business.KYCStatus.REJECTED
        business.save()
        if hasattr(business, 'kyc'):
            business.kyc.reviewed_by = request.user
            business.kyc.reviewed_at = timezone.now()
            business.kyc.rejection_reason = request.data.get('reason', '')
            business.kyc.save()
        return Response({"message": "Business KYC rejected"})

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        business = self.get_object()
        if request.method == 'POST':
            serializer = BusinessMemberSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(business=business, invited_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        members = business.members.all()
        serializer = BusinessMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def switch(self, request, pk=None):
        """Switch active business for the current user session."""
        business = self.get_object()
        membership = BusinessMember.objects.filter(business=business, user=request.user, is_active=True).first()
        if not membership and business.owner != request.user:
            return Response({"error": "You are not a member of this business"}, status=status.HTTP_403_FORBIDDEN)
        serializer = BusinessSerializer(business)
        return Response({"active_business": serializer.data})


class BusinessMemberViewSet(viewsets.ModelViewSet):
    queryset = BusinessMember.objects.all()
    serializer_class = BusinessMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.ADMIN:
            return BusinessMember.objects.all()
        member_business_ids = BusinessMember.objects.filter(user=user, is_active=True).values_list('business_id', flat=True)
        return BusinessMember.objects.filter(business_id__in=member_business_ids)
