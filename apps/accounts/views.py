from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import models
from .models import User, Business, BusinessMember, BusinessKYC, KYCDocument
from .serializers import (
    UserSerializer, BusinessSerializer, BusinessMemberSerializer,
    BusinessKYCSerializer, KYCDocumentSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

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
