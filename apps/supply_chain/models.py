"""
Models for FlightFix ERP & Supply Chain Integration module.
"""

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.inventory.models import SparePart


class SupplierStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    INACTIVE = 'INACTIVE', _('Inactive')
    SUSPENDED = 'SUSPENDED', _('Suspended')


class SupplierType(models.TextChoices):
    OEM = 'OEM', _('Original Equipment Manufacturer (OEM)')
    AUTHORIZED_DISTRIBUTOR = 'AUTHORIZED_DISTRIBUTOR', _('Authorized Distributor')
    THIRD_PARTY = 'THIRD_PARTY', _('Third-Party Supplier')
    LOGISTICS_PROVIDER = 'LOGISTICS_PROVIDER', _('Logistics Provider')
    OTHER = 'OTHER', _('Other')


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    APPROVED = 'APPROVED', _('Approved')
    ORDERED = 'ORDERED', _('Ordered')
    PARTIALLY_RECEIVED = 'PARTIALLY_RECEIVED', _('Partially Received')
    RECEIVED = 'RECEIVED', _('Received')
    CANCELLED = 'CANCELLED', _('Cancelled')


class PurchaseOrderPriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class Supplier(models.Model):
    """
    Represents an aircraft parts OEM, distributor, or maintenance materials vendor.
    """
    supplier_code = models.CharField(
        _('supplier code'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique supplier identifier normalized to uppercase (e.g. VEND-BOEING-01).')
    )
    name = models.CharField(
        _('supplier name'),
        max_length=150,
        help_text=_('Company or commercial legal entity name.')
    )
    contact_person = models.CharField(
        _('contact person'),
        max_length=100,
        blank=True,
        default=''
    )
    email = models.EmailField(
        _('email address'),
        blank=True,
        default=''
    )
    phone = models.CharField(
        _('phone number'),
        max_length=30,
        blank=True,
        default=''
    )
    address = models.TextField(
        _('physical address'),
        blank=True,
        default=''
    )
    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True,
        default=''
    )
    country = models.CharField(
        _('country'),
        max_length=100,
        blank=True,
        default=''
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=SupplierStatus.choices,
        default=SupplierStatus.ACTIVE,
        db_index=True
    )
    supplier_type = models.CharField(
        _('supplier type'),
        max_length=30,
        choices=SupplierType.choices,
        default=SupplierType.AUTHORIZED_DISTRIBUTOR,
        db_index=True
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        ordering = ['supplier_code']
        indexes = [
            models.Index(fields=['supplier_code']),
            models.Index(fields=['status']),
            models.Index(fields=['supplier_type']),
        ]

    def __str__(self):
        return f"{self.supplier_code} - {self.name} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.supplier_code:
            self.supplier_code = self.supplier_code.strip().upper()

    def save(self, *args, **kwargs):
        if self.supplier_code:
            self.supplier_code = self.supplier_code.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    """
    Represents an ERP purchase order for procurement of spare parts and maintenance consumables.
    """
    po_number = models.CharField(
        _('purchase order number'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique purchase order identifier (e.g. PO-2026-0001).')
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name=_('supplier'),
        help_text=_('Supplier supplying the ordered spare parts.')
    )
    order_date = models.DateField(
        _('order date'),
        default=timezone.now,
        help_text=_('Date when purchase order was officially created.')
    )
    expected_delivery_date = models.DateField(
        _('expected delivery date'),
        help_text=_('Promised supplier arrival date.')
    )
    actual_delivery_date = models.DateField(
        _('actual delivery date'),
        null=True,
        blank=True,
        help_text=_('Date when goods were received into warehouse.')
    )
    status = models.CharField(
        _('PO status'),
        max_length=25,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
        db_index=True
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=PurchaseOrderPriority.choices,
        default=PurchaseOrderPriority.MEDIUM,
        db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_purchase_orders',
        verbose_name=_('created by')
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_orders',
        verbose_name=_('approved by')
    )
    approved_at = models.DateTimeField(
        _('approved at'),
        null=True,
        blank=True
    )
    delivery_address = models.TextField(
        _('delivery address'),
        blank=True,
        default='',
        help_text=_('Destination warehouse or airport hangar bay location.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('Purchase Order')
        verbose_name_plural = _('Purchase Orders')
        ordering = ['-order_date', '-created_at']
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['order_date']),
            models.Index(fields=['expected_delivery_date']),
        ]

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        errors = {}

        if self.po_number:
            self.po_number = self.po_number.strip().upper()

        # 1. Date chronological sequence
        if self.order_date and self.expected_delivery_date:
            if self.expected_delivery_date < self.order_date:
                errors['expected_delivery_date'] = _('Expected delivery date cannot be before order date.')

        if self.order_date and self.actual_delivery_date:
            if self.actual_delivery_date < self.order_date:
                errors['actual_delivery_date'] = _('Actual delivery date cannot be before order date.')

        # 2. Re-activation check on cancelled orders
        if self.pk:
            previous = PurchaseOrder.objects.filter(pk=self.pk).values('status').first()
            if previous and previous['status'] == PurchaseOrderStatus.CANCELLED and self.status != PurchaseOrderStatus.CANCELLED:
                errors['status'] = _('Cancelled purchase orders cannot be reopened or reactivated.')

        # 3. Active supplier requirement when creating or approving
        if self.supplier_id:
            supplier_obj = getattr(self, 'supplier', None) or Supplier.objects.filter(pk=self.supplier_id).first()
            if supplier_obj and supplier_obj.status != SupplierStatus.ACTIVE:
                # If creating new or moving to approved
                if not self.pk or self.status == PurchaseOrderStatus.APPROVED:
                    errors['supplier'] = _(
                        f"Supplier '{supplier_obj.name}' is {supplier_obj.get_status_display().lower()} "
                        "and cannot be used for new or approved purchase orders."
                    )

        # 4. Approval requirements
        if self.status == PurchaseOrderStatus.APPROVED:
            if not self.approved_by_id:
                errors['approved_by'] = _('Approved purchase orders must specify an approved_by user.')
            if not self.approved_at:
                self.approved_at = timezone.now()

        # 5. Received requirements
        if self.status == PurchaseOrderStatus.RECEIVED and not self.actual_delivery_date:
            self.actual_delivery_date = timezone.now().date()

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.po_number:
            self.po_number = self.po_number.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    """
    Represents an individual line item of spare parts within a PurchaseOrder.
    """
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('purchase order')
    )
    spare_part = models.ForeignKey(
        SparePart,
        on_delete=models.PROTECT,
        related_name='purchase_order_items',
        verbose_name=_('spare part'),
        help_text=_('Inventory spare part being procured.')
    )
    quantity_ordered = models.PositiveIntegerField(
        _('quantity ordered'),
        validators=[MinValueValidator(1, message=_('Quantity ordered must be greater than zero.'))]
    )
    quantity_received = models.PositiveIntegerField(
        _('quantity received'),
        default=0,
        help_text=_('Quantity verified and received into inventory.')
    )
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'), message=_('Unit price cannot be negative.'))],
        help_text=_('Unit purchase price agreed with supplier.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('Purchase Order Item')
        verbose_name_plural = _('Purchase Order Items')
        ordering = ['id']
        unique_together = [('purchase_order', 'spare_part')]
        indexes = [
            models.Index(fields=['purchase_order', 'spare_part']),
        ]

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.spare_part.part_number} (Ordered: {self.quantity_ordered}, Recv: {self.quantity_received})"

    @property
    def line_total(self):
        """Calculates total cost for this line item."""
        return (self.quantity_ordered or 0) * (self.unit_price or Decimal('0.00'))

    @property
    def quantity_pending(self):
        """Calculates quantity remaining to be received."""
        return max(0, (self.quantity_ordered or 0) - (self.quantity_received or 0))

    def clean(self):
        super().clean()
        errors = {}

        if self.quantity_ordered is not None and self.quantity_ordered <= 0:
            errors['quantity_ordered'] = _('Quantity ordered must be greater than zero.')

        if self.quantity_received is not None:
            if self.quantity_received < 0:
                errors['quantity_received'] = _('Quantity received cannot be negative.')
            elif self.quantity_ordered is not None and self.quantity_received > self.quantity_ordered:
                errors['quantity_received'] = _('Quantity received cannot exceed quantity ordered.')

        if self.unit_price is not None and self.unit_price < Decimal('0.00'):
            errors['unit_price'] = _('Unit price cannot be negative.')

        # Check duplicate spare part inside the same PO
        if self.purchase_order_id and self.spare_part_id:
            qs = PurchaseOrderItem.objects.filter(
                purchase_order_id=self.purchase_order_id,
                spare_part_id=self.spare_part_id
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors['spare_part'] = _('This spare part is already added to this purchase order.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
