"""
Unit and integration tests for FlightFix ERP & Supply Chain Integration module.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.inventory.models import (
    SparePart,
    InventoryTransaction,
    StockStatus,
    PartCategory,
    TransactionType,
)
from apps.supply_chain.models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    SupplierStatus,
    SupplierType,
    PurchaseOrderStatus,
    PurchaseOrderPriority,
)

User = get_user_model()


class BaseSupplyChainTestCase(APITestCase):
    """
    Common setup for ERP & Supply Chain testing across all four user roles.
    """
    def setUp(self):
        # 1. Setup Users for all 4 roles
        self.admin_user = User.objects.create_user(
            username='erp_admin',
            email='erp_admin@flightfix.com',
            password='Password123!',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMIN,
        )
        self.safety_user = User.objects.create_user(
            username='erp_safety',
            email='erp_safety@flightfix.com',
            password='Password123!',
            first_name='Safety',
            last_name='Officer',
            role=User.Role.SAFETY_OFFICER,
        )
        self.contracts_user = User.objects.create_user(
            username='erp_contracts',
            email='erp_contracts@flightfix.com',
            password='Password123!',
            first_name='Contracts',
            last_name='Manager',
            role=User.Role.CONTRACTS_MANAGER,
        )
        self.tech_user = User.objects.create_user(
            username='erp_tech',
            email='erp_tech@flightfix.com',
            password='Password123!',
            first_name='Field',
            last_name='Technician',
            role=User.Role.FIELD_TECHNICIAN,
        )

        # 2. Setup JWT Tokens
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.safety_token = str(RefreshToken.for_user(self.safety_user).access_token)
        self.contracts_token = str(RefreshToken.for_user(self.contracts_user).access_token)
        self.tech_token = str(RefreshToken.for_user(self.tech_user).access_token)

        # 3. Setup Spare Parts from apps.inventory
        self.spare_part_1 = SparePart.objects.create(
            part_number='PN-ERP-VALVE-01',
            name='Fuel Control Shutoff Valve',
            description='High pressure dual solenoid shutoff valve.',
            category=PartCategory.ENGINE,
            manufacturer='Parker Aerospace',
            quantity_in_stock=10,
            minimum_stock_level=5,
            unit_price=Decimal('1200.00'),
            location='Hangar-1 / Shelf-E01',
        )
        self.spare_part_2 = SparePart.objects.create(
            part_number='PN-ERP-FILTER-02',
            name='Hydraulic System Micron Filter',
            description='5-micron high pressure return filter.',
            category=PartCategory.HYDRAULICS,
            manufacturer='Pall Aerospace',
            quantity_in_stock=5,
            minimum_stock_level=10,
            unit_price=Decimal('350.00'),
            location='Hangar-2 / Bin-F02',
        )

        # 4. Setup Active Supplier
        self.supplier = Supplier.objects.create(
            supplier_code='VEND-PARKER-01',
            name='Parker Aerospace Supply Corporation',
            contact_person='David Miller',
            email='dmiller@parkeraero.com',
            phone='+1-555-0188',
            address='14300 Alton Parkway',
            city='Irvine',
            country='USA',
            status=SupplierStatus.ACTIVE,
            supplier_type=SupplierType.OEM,
        )

        # 5. Inactive Supplier for testing validation
        self.inactive_supplier = Supplier.objects.create(
            supplier_code='VEND-DEFUNCT-02',
            name='Defunct Logistics Inc',
            contact_person='Jane Doe',
            status=SupplierStatus.INACTIVE,
            supplier_type=SupplierType.LOGISTICS_PROVIDER,
        )

        # 6. Sample Approved Purchase Order
        self.today = timezone.now().date()
        self.sample_po = PurchaseOrder.objects.create(
            po_number='PO-2026-0001',
            supplier=self.supplier,
            order_date=self.today,
            expected_delivery_date=self.today + timezone.timedelta(days=14),
            status=PurchaseOrderStatus.APPROVED,
            priority=PurchaseOrderPriority.HIGH,
            created_by=self.contracts_user,
            approved_by=self.admin_user,
            approved_at=timezone.now(),
            delivery_address='FlightFix Hangar Bay 1, Airport Cargo Complex',
        )

        # 7. Sample Purchase Order Item
        self.sample_item = PurchaseOrderItem.objects.create(
            purchase_order=self.sample_po,
            spare_part=self.spare_part_1,
            quantity_ordered=20,
            quantity_received=0,
            unit_price=Decimal('1150.00'),
        )

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def unauth(self):
        self.client.credentials()


class SupplierModelAndAPITests(BaseSupplyChainTestCase):
    """
    Tests covering Supplier model validations, uppercase normalization, duplicate checks, and RBAC permissions.
    """
    def test_supplier_creation_and_uppercase_normalization(self):
        supplier = Supplier.objects.create(
            supplier_code='  vend-boeing-parts  ',
            name='Boeing Global Distribution',
            contact_person='Sarah Connor',
            email='sconnor@boeing.com',
            status=SupplierStatus.ACTIVE,
            supplier_type=SupplierType.OEM,
        )
        self.assertEqual(supplier.supplier_code, 'VEND-BOEING-PARTS')

    def test_duplicate_supplier_code_rejected(self):
        with self.assertRaises(ValidationError):
            dup = Supplier(
                supplier_code='vend-parker-01',  # lowercase duplicate of VEND-PARKER-01
                name='Duplicate Parker Entity',
            )
            dup.save()

    def test_admin_full_crud_on_suppliers(self):
        self.auth_as(self.admin_token)
        payload = {
            'supplier_code': 'VEND-HONEYWELL-01',
            'name': 'Honeywell Aerospace Solutions',
            'contact_person': 'Robert Vance',
            'email': 'rvance@honeywell.com',
            'phone': '+1-555-9090',
            'city': 'Phoenix',
            'country': 'USA',
            'status': 'ACTIVE',
            'supplier_type': 'OEM',
        }
        create_resp = self.client.post('/api/supply-chain/suppliers/', payload, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        sup_id = create_resp.data['id']

        # Update
        patch_resp = self.client.patch(f'/api/supply-chain/suppliers/{sup_id}/', {'city': 'Tempe'}, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)

        # Delete
        del_resp = self.client.delete(f'/api/supply-chain/suppliers/{sup_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_contracts_manager_can_create_and_update_but_not_delete_supplier(self):
        self.auth_as(self.contracts_token)
        payload = {
            'supplier_code': 'VEND-COLLINS-01',
            'name': 'Collins Aerospace Distribution',
            'status': 'ACTIVE',
            'supplier_type': 'AUTHORIZED_DISTRIBUTOR',
        }
        create_resp = self.client.post('/api/supply-chain/suppliers/', payload, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        sup_id = create_resp.data['id']

        # Update
        patch_resp = self.client.patch(f'/api/supply-chain/suppliers/{sup_id}/', {'notes': 'Preferred vendor'}, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)

        # Delete must be forbidden (403)
        del_resp = self.client.delete(f'/api/supply-chain/suppliers/{sup_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_safety_officer_cannot_delete_supplier(self):
        self.auth_as(self.safety_token)
        del_resp = self.client.delete(f'/api/supply-chain/suppliers/{self.supplier.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_technician_read_only_access_to_suppliers(self):
        self.auth_as(self.tech_token)
        list_resp = self.client.get('/api/supply-chain/suppliers/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        detail_resp = self.client.get(f'/api/supply-chain/suppliers/{self.supplier.id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)

        # Modifications forbidden (403)
        post_resp = self.client.post('/api/supply-chain/suppliers/', {'supplier_code': 'FAIL'}, format='json')
        self.assertEqual(post_resp.status_code, status.HTTP_403_FORBIDDEN)

        del_resp = self.client.delete(f'/api/supply-chain/suppliers/{self.supplier.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_supplier_access_rejected(self):
        self.unauth()
        resp = self.client.get('/api/supply-chain/suppliers/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PurchaseOrderModelAndAPITests(BaseSupplyChainTestCase):
    """
    Tests covering PurchaseOrder model validations, status workflows, approval logic, and permissions.
    """
    def test_po_number_uppercase_normalization(self):
        po = PurchaseOrder.objects.create(
            po_number='  po-2026-norm-01  ',
            supplier=self.supplier,
            order_date=self.today,
            expected_delivery_date=self.today + timezone.timedelta(days=7),
            created_by=self.contracts_user,
        )
        self.assertEqual(po.po_number, 'PO-2026-NORM-01')

    def test_duplicate_po_number_rejected(self):
        with self.assertRaises(ValidationError):
            dup = PurchaseOrder(
                po_number='po-2026-0001',  # lowercase duplicate of self.sample_po
                supplier=self.supplier,
                order_date=self.today,
                expected_delivery_date=self.today + timezone.timedelta(days=7),
                created_by=self.contracts_user,
            )
            dup.save()

    def test_expected_delivery_date_before_order_date_rejected(self):
        with self.assertRaises(ValidationError):
            invalid_po = PurchaseOrder(
                po_number='PO-FAIL-DATES',
                supplier=self.supplier,
                order_date=self.today,
                expected_delivery_date=self.today - timezone.timedelta(days=2),  # before order_date
                created_by=self.contracts_user,
            )
            invalid_po.save()

    def test_inactive_supplier_rejected_for_new_po(self):
        with self.assertRaises(ValidationError):
            po_inactive = PurchaseOrder(
                po_number='PO-FAIL-SUPPLIER',
                supplier=self.inactive_supplier,
                order_date=self.today,
                expected_delivery_date=self.today + timezone.timedelta(days=5),
                created_by=self.contracts_user,
            )
            po_inactive.save()

    def test_approved_po_requires_approved_by(self):
        with self.assertRaises(ValidationError):
            po_unapproved = PurchaseOrder(
                po_number='PO-FAIL-APPROVE',
                supplier=self.supplier,
                order_date=self.today,
                expected_delivery_date=self.today + timezone.timedelta(days=5),
                status=PurchaseOrderStatus.APPROVED,
                approved_by=None,  # Missing required approved_by
                created_by=self.contracts_user,
            )
            po_unapproved.save()

    def test_cancelled_po_cannot_be_reopened(self):
        po = PurchaseOrder.objects.create(
            po_number='PO-TO-CANCEL',
            supplier=self.supplier,
            order_date=self.today,
            expected_delivery_date=self.today + timezone.timedelta(days=5),
            status=PurchaseOrderStatus.DRAFT,
            created_by=self.contracts_user,
        )
        # Cancel the PO
        po.status = PurchaseOrderStatus.CANCELLED
        po.save()

        # Attempt to reactivate to DRAFT or APPROVED
        po.status = PurchaseOrderStatus.DRAFT
        with self.assertRaises(ValidationError):
            po.save()

    def test_contracts_manager_can_create_purchase_order(self):
        self.auth_as(self.contracts_token)
        payload = {
            'po_number': 'PO-2026-CM-01',
            'supplier': self.supplier.id,
            'order_date': str(self.today),
            'expected_delivery_date': str(self.today + timezone.timedelta(days=10)),
            'priority': 'HIGH',
            'status': 'DRAFT',
            'delivery_address': 'Main Hangar Warehouse',
        }
        response = self.client.post('/api/supply-chain/purchase-orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['po_number'], 'PO-2026-CM-01')
        self.assertEqual(response.data['created_by_username'], self.contracts_user.username)

    def test_admin_can_approve_and_delete_purchase_order(self):
        self.auth_as(self.admin_token)
        po = PurchaseOrder.objects.create(
            po_number='PO-ADMIN-APPROVE',
            supplier=self.supplier,
            order_date=self.today,
            expected_delivery_date=self.today + timezone.timedelta(days=5),
            status=PurchaseOrderStatus.DRAFT,
            created_by=self.contracts_user,
        )
        # Approve
        patch_resp = self.client.patch(
            f'/api/supply-chain/purchase-orders/{po.id}/',
            {'status': 'APPROVED', 'approved_by': self.admin_user.id},
            format='json'
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data['status'], 'APPROVED')

        # Delete
        del_resp = self.client.delete(f'/api/supply-chain/purchase-orders/{po.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_search_and_filters_purchase_orders(self):
        self.auth_as(self.admin_token)
        # Search
        resp_search = self.client.get(f'/api/supply-chain/purchase-orders/?search={self.sample_po.po_number}')
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        results = resp_search.data.get('results', resp_search.data)
        self.assertTrue(len(results) >= 1)

        # Filter by status
        resp_status = self.client.get('/api/supply-chain/purchase-orders/?status=APPROVED')
        self.assertEqual(resp_status.status_code, status.HTTP_200_OK)
        for po in resp_status.data.get('results', resp_status.data):
            self.assertEqual(po['status'], 'APPROVED')

        # Filter by supplier
        resp_supp = self.client.get(f'/api/supply-chain/purchase-orders/?supplier={self.supplier.id}')
        self.assertEqual(resp_supp.status_code, status.HTTP_200_OK)
        for po in resp_supp.data.get('results', resp_supp.data):
            self.assertEqual(po['supplier'], self.supplier.id)


class PurchaseOrderItemTests(BaseSupplyChainTestCase):
    """
    Tests covering line item validation, line totals, duplicate spare part rejection, and quantity constraints.
    """
    def test_duplicate_spare_part_inside_same_po_rejected(self):
        with self.assertRaises(ValidationError):
            # self.sample_item already has spare_part_1 in sample_po
            dup_item = PurchaseOrderItem(
                purchase_order=self.sample_po,
                spare_part=self.spare_part_1,
                quantity_ordered=5,
                unit_price=Decimal('100.00'),
            )
            dup_item.save()

    def test_zero_or_negative_quantity_ordered_rejected(self):
        with self.assertRaises(ValidationError):
            item_neg = PurchaseOrderItem(
                purchase_order=self.sample_po,
                spare_part=self.spare_part_2,
                quantity_ordered=0,
                unit_price=Decimal('50.00'),
            )
            item_neg.save()

    def test_negative_unit_price_rejected(self):
        with self.assertRaises(ValidationError):
            item_neg_price = PurchaseOrderItem(
                purchase_order=self.sample_po,
                spare_part=self.spare_part_2,
                quantity_ordered=5,
                unit_price=Decimal('-25.00'),
            )
            item_neg_price.save()

    def test_quantity_received_cannot_exceed_ordered(self):
        with self.assertRaises(ValidationError):
            item_over = PurchaseOrderItem(
                purchase_order=self.sample_po,
                spare_part=self.spare_part_2,
                quantity_ordered=10,
                quantity_received=15,  # 15 > 10
                unit_price=Decimal('50.00'),
            )
            item_over.save()

    def test_line_total_and_pending_quantity_calculations(self):
        item = PurchaseOrderItem.objects.create(
            purchase_order=self.sample_po,
            spare_part=self.spare_part_2,
            quantity_ordered=10,
            quantity_received=4,
            unit_price=Decimal('350.00'),
        )
        self.assertEqual(item.line_total, Decimal('3500.00'))
        self.assertEqual(item.quantity_pending, 6)


class ReceivingWorkflowAndInventoryIntegrationTests(BaseSupplyChainTestCase):
    """
    Tests covering the /receive/ custom action, inventory integration, stock increments,
    InventoryTransaction creation, atomic rollbacks, and status transitions.
    """
    def test_partial_receiving_workflow(self):
        self.auth_as(self.contracts_token)
        initial_stock = self.spare_part_1.quantity_in_stock  # 10

        payload = {
            'items': [
                {
                    'purchase_order_item': self.sample_item.id,
                    'quantity_received': 8,
                }
            ],
            'notes': 'Partial delivery of 8 fuel valves by courier.',
        }
        response = self.client.post(
            f'/api/supply-chain/purchase-orders/{self.sample_po.id}/receive/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 1. PO status should be PARTIALLY_RECEIVED
        self.sample_po.refresh_from_db()
        self.assertEqual(self.sample_po.status, PurchaseOrderStatus.PARTIALLY_RECEIVED)

        # 2. Line item quantity_received should be updated
        self.sample_item.refresh_from_db()
        self.assertEqual(self.sample_item.quantity_received, 8)
        self.assertEqual(self.sample_item.quantity_pending, 12)

        # 3. SparePart stock should be incremented atomically
        self.spare_part_1.refresh_from_db()
        self.assertEqual(self.spare_part_1.quantity_in_stock, initial_stock + 8)

        # 4. InventoryTransaction of type RECEIPT should exist
        tx = InventoryTransaction.objects.filter(
            spare_part=self.spare_part_1,
            transaction_type=TransactionType.RECEIPT,
            reference=self.sample_po.po_number
        ).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.quantity, 8)
        self.assertEqual(tx.performed_by, self.contracts_user)

    def test_full_receiving_workflow_sets_received_status(self):
        self.auth_as(self.admin_token)
        initial_stock = self.spare_part_1.quantity_in_stock

        payload = {
            'items': [
                {
                    'purchase_order_item': self.sample_item.id,
                    'quantity_received': 20,  # All 20 units received
                }
            ],
            'notes': 'Full shipment verified at hangar inspection.',
        }
        response = self.client.post(
            f'/api/supply-chain/purchase-orders/{self.sample_po.id}/receive/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # PO status should become RECEIVED
        self.sample_po.refresh_from_db()
        self.assertEqual(self.sample_po.status, PurchaseOrderStatus.RECEIVED)
        self.assertIsNotNone(self.sample_po.actual_delivery_date)

        # SparePart stock incremented
        self.spare_part_1.refresh_from_db()
        self.assertEqual(self.spare_part_1.quantity_in_stock, initial_stock + 20)

    def test_over_receiving_rejected_with_atomic_rollback(self):
        self.auth_as(self.admin_token)
        initial_stock = self.spare_part_1.quantity_in_stock

        # Ordered is 20, attempting to receive 25
        payload = {
            'items': [
                {
                    'purchase_order_item': self.sample_item.id,
                    'quantity_received': 25,
                }
            ],
        }
        response = self.client.post(
            f'/api/supply-chain/purchase-orders/{self.sample_po.id}/receive/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

        # Ensure rollback: stock unchanged, received quantity unchanged
        self.sample_item.refresh_from_db()
        self.assertEqual(self.sample_item.quantity_received, 0)
        self.spare_part_1.refresh_from_db()
        self.assertEqual(self.spare_part_1.quantity_in_stock, initial_stock)

    def test_cannot_receive_on_draft_or_cancelled_po(self):
        self.auth_as(self.admin_token)
        draft_po = PurchaseOrder.objects.create(
            po_number='PO-DRAFT-RECEIVE',
            supplier=self.supplier,
            order_date=self.today,
            expected_delivery_date=self.today + timezone.timedelta(days=7),
            status=PurchaseOrderStatus.DRAFT,
            created_by=self.contracts_user,
        )
        draft_item = PurchaseOrderItem.objects.create(
            purchase_order=draft_po,
            spare_part=self.spare_part_2,
            quantity_ordered=5,
            unit_price=Decimal('50.00'),
        )
        payload = {
            'items': [{'purchase_order_item': draft_item.id, 'quantity_received': 2}]
        }
        response = self.client.post(
            f'/api/supply-chain/purchase-orders/{draft_po.id}/receive/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_field_technician_cannot_receive_purchase_orders(self):
        self.auth_as(self.tech_token)
        payload = {
            'items': [{'purchase_order_item': self.sample_item.id, 'quantity_received': 5}]
        }
        response = self.client.post(
            f'/api/supply-chain/purchase-orders/{self.sample_po.id}/receive/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
