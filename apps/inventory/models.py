"""
Models for FlightFix Spare Parts Inventory module.
"""

from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class StockStatus(models.TextChoices):
    IN_STOCK = 'IN_STOCK', _('In Stock')
    LOW_STOCK = 'LOW_STOCK', _('Low Stock')
    OUT_OF_STOCK = 'OUT_OF_STOCK', _('Out of Stock')
    DISCONTINUED = 'DISCONTINUED', _('Discontinued')


class PartCategory(models.TextChoices):
    AVIONICS = 'AVIONICS', _('Avionics')
    ENGINE = 'ENGINE', _('Engine & Propulsion')
    HYDRAULICS = 'HYDRAULICS', _('Hydraulics & Pneumatics')
    LANDING_GEAR = 'LANDING_GEAR', _('Landing Gear & Brakes')
    STRUCTURAL = 'STRUCTURAL', _('Structural & Airframe')
    ELECTRICAL = 'ELECTRICAL', _('Electrical & Power')
    CABIN = 'CABIN', _('Cabin & Interiors')
    HARDWARE = 'HARDWARE', _('Hardware & Fasteners')
    CONSUMABLE = 'CONSUMABLE', _('Consumables & Fluids')
    OTHER = 'OTHER', _('Other')


class TransactionType(models.TextChoices):
    RECEIPT = 'RECEIPT', _('Receipt')
    ISSUE = 'ISSUE', _('Issue')
    ADJUSTMENT = 'ADJUSTMENT', _('Adjustment')
    RETURN = 'RETURN', _('Return')


class SparePart(models.Model):
    """
    Represents an aircraft spare part, component, or consumable in inventory.
    """
    part_number = models.CharField(
        _('part number'),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_('Unique part number normalized to uppercase (e.g. PN-737-HYD-01).')
    )
    name = models.CharField(
        _('part name'),
        max_length=150,
        help_text=_('Descriptive name of the part.')
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
        help_text=_('Detailed part specifications or applications.')
    )
    category = models.CharField(
        _('category'),
        max_length=50,
        choices=PartCategory.choices,
        default=PartCategory.OTHER,
        db_index=True
    )
    manufacturer = models.CharField(
        _('manufacturer'),
        max_length=100,
        db_index=True,
        help_text=_('Original Equipment Manufacturer (OEM).')
    )
    manufacturer_part_number = models.CharField(
        _('manufacturer part number'),
        max_length=100,
        blank=True,
        default='',
        help_text=_('OEM part number if different from inventory part number.')
    )
    quantity_in_stock = models.IntegerField(
        _('quantity in stock'),
        default=0,
        validators=[MinValueValidator(0, message=_('Quantity in stock cannot be negative.'))],
        help_text=_('Current usable on-hand quantity.')
    )
    minimum_stock_level = models.IntegerField(
        _('minimum stock level'),
        default=0,
        validators=[MinValueValidator(0, message=_('Minimum stock level cannot be negative.'))],
        help_text=_('Reorder threshold quantity.')
    )
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'), message=_('Unit price cannot be negative.'))],
        help_text=_('Unit acquisition or replacement cost in standard currency.')
    )
    location = models.CharField(
        _('storage location'),
        max_length=100,
        help_text=_('Warehouse bin, shelf, rack, or bay location (e.g. Hangar-1 / Bin-B12).')
    )
    supplier = models.CharField(
        _('primary supplier'),
        max_length=100,
        blank=True,
        default='',
        help_text=_('Vendor or distributor name.')
    )
    status = models.CharField(
        _('stock status'),
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.OUT_OF_STOCK,
        db_index=True,
        help_text=_('Current stock availability status.')
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
        verbose_name = _('Spare Part')
        verbose_name_plural = _('Spare Parts')
        ordering = ['part_number']
        indexes = [
            models.Index(fields=['part_number']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['manufacturer']),
        ]

    def __str__(self):
        return f"{self.part_number} - {self.name} ({self.quantity_in_stock} in stock)"

    def clean(self):
        super().clean()
        errors = {}

        if self.part_number:
            self.part_number = self.part_number.strip().upper()

        if self.quantity_in_stock is not None and self.quantity_in_stock < 0:
            errors['quantity_in_stock'] = _('Quantity in stock cannot be negative.')

        if self.minimum_stock_level is not None and self.minimum_stock_level < 0:
            errors['minimum_stock_level'] = _('Minimum stock level cannot be negative.')

        if self.unit_price is not None and self.unit_price < Decimal('0.00'):
            errors['unit_price'] = _('Unit price cannot be negative.')

        if errors:
            raise ValidationError(errors)

    def update_stock_status(self):
        """
        Calculates and updates status based on quantity_in_stock and minimum_stock_level.
        If marked DISCONTINUED, the status is preserved.
        """
        if self.status == StockStatus.DISCONTINUED:
            return

        if self.quantity_in_stock <= 0:
            self.status = StockStatus.OUT_OF_STOCK
        elif self.quantity_in_stock <= self.minimum_stock_level:
            self.status = StockStatus.LOW_STOCK
        else:
            self.status = StockStatus.IN_STOCK

    def save(self, *args, **kwargs):
        if self.part_number:
            self.part_number = self.part_number.strip().upper()
        self.update_stock_status()
        self.full_clean()
        super().save(*args, **kwargs)


class InventoryTransaction(models.Model):
    """
    Audit log of inventory stock receipts, issues, adjustments, and returns.
    """
    spare_part = models.ForeignKey(
        SparePart,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('spare part'),
        help_text=_('Spare part affected by this transaction.')
    )
    transaction_type = models.CharField(
        _('transaction type'),
        max_length=20,
        choices=TransactionType.choices,
        db_index=True
    )
    quantity = models.PositiveIntegerField(
        _('quantity'),
        validators=[MinValueValidator(1, message=_('Transaction quantity must be greater than zero.'))],
        help_text=_('Number of units moved.')
    )
    reference = models.CharField(
        _('reference'),
        max_length=100,
        help_text=_('Work order number, PO number, RMA, or Audit reference.')
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='inventory_transactions',
        verbose_name=_('performed by'),
        help_text=_('User who authorized or logged this inventory transaction.')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        verbose_name = _('Inventory Transaction')
        verbose_name_plural = _('Inventory Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} ({self.quantity}) - {self.spare_part.part_number} by {self.performed_by}"

    def clean(self):
        super().clean()
        errors = {}

        if self.quantity is not None and self.quantity <= 0:
            errors['quantity'] = _('Transaction quantity must be greater than zero.')

        if self.transaction_type == TransactionType.ISSUE and self.spare_part_id and self.quantity is not None:
            # Check available stock if newly creating transaction
            if not self.pk:
                current_stock = self.spare_part.quantity_in_stock
                if current_stock < self.quantity:
                    errors['quantity'] = _(
                        f"Cannot issue {self.quantity} unit(s). Only {current_stock} available in stock."
                    )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()

        with transaction.atomic():
            if is_new:
                # Lock the spare part row for stock modification
                part = SparePart.objects.select_for_update().get(pk=self.spare_part_id)

                if self.transaction_type in (TransactionType.RECEIPT, TransactionType.RETURN):
                    part.quantity_in_stock += self.quantity
                elif self.transaction_type == TransactionType.ISSUE:
                    if part.quantity_in_stock < self.quantity:
                        raise ValidationError({
                            'quantity': _(f"Cannot issue {self.quantity} unit(s). Only {part.quantity_in_stock} available in stock.")
                        })
                    part.quantity_in_stock -= self.quantity
                elif self.transaction_type == TransactionType.ADJUSTMENT:
                    part.quantity_in_stock = self.quantity

                part.update_stock_status()
                part.save()
                self.spare_part = part

            super().save(*args, **kwargs)
