# FlightFix: Enhancing Aircraft Maintenance Efficiency - Backend

FlightFix is a web platform designed to streamline aircraft maintenance, inspections, work orders, and regulatory compliance.

---

## Step 1: User Management & Authentication (RBAC)

Authentication is implemented using Django REST Framework and JSON Web Tokens (JWT) via `djangorestframework-simplejwt`.

### Supported Roles
- `ADMIN`: Full administrative control over users, aircraft, and work orders.
- `SAFETY_OFFICER`: Manages inspections, compliance records, and incident reporting.
- `CONTRACTS_MANAGER`: Manages service level agreements, maintenance contracts, and vendors.
- `FIELD_TECHNICIAN`: Executes assigned maintenance tasks, logs work orders, and records parts used.

---

## Authentication Endpoints

Base URL: `http://127.0.0.1:8000/api/auth/`

### 1. Register New User
* **URL**: `/api/auth/register/`
* **Method**: `POST`
* **Authentication**: None (Public)
* **Request Body**:
  ```json
  {
    "username": "tech_sarah",
    "email": "sarah@flightfix.com",
    "password": "SecurePassword123!",
    "first_name": "Sarah",
    "last_name": "Connor",
    "phone": "+1-555-0199",
    "role": "FIELD_TECHNICIAN"
  }
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "status": "success",
    "message": "User registered successfully.",
    "user": {
      "id": 1,
      "username": "tech_sarah",
      "email": "sarah@flightfix.com",
      "first_name": "Sarah",
      "last_name": "Connor",
      "phone": "+1-555-0199",
      "role": "FIELD_TECHNICIAN",
      "is_active": true,
      "is_staff": false,
      "created_at": "2026-11-18T17:20:00Z",
      "updated_at": "2026-11-18T17:20:00Z"
    },
    "role": "FIELD_TECHNICIAN",
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>"
  }
  ```
* **Error Response (400 Bad Request)**:
  ```json
  {
    "email": ["A user with this email already exists."],
    "password": ["Password must contain at least 8 characters."]
  }
  ```

---

### 2. User Login
* **URL**: `/api/auth/login/`
* **Method**: `POST`
* **Authentication**: None (Public)
* **Request Body**: (Supports username OR email)
  ```json
  {
    "username": "tech_sarah",
    "password": "SecurePassword123!"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>",
    "user": {
      "id": 1,
      "username": "tech_sarah",
      "email": "sarah@flightfix.com",
      "first_name": "Sarah",
      "last_name": "Connor",
      "phone": "+1-555-0199",
      "role": "FIELD_TECHNICIAN",
      "is_active": true,
      "is_staff": false,
      "created_at": "2026-11-18T17:20:00Z",
      "updated_at": "2026-11-18T17:20:00Z"
    },
    "role": "FIELD_TECHNICIAN"
  }
  ```
* **Error Response (400 Bad Request)**:
  ```json
  {
    "non_field_errors": ["Invalid credentials. Please verify your username/email and password."]
  }
  ```

---

### 3. Refresh Access Token
* **URL**: `/api/auth/refresh/`
* **Method**: `POST`
* **Authentication**: None
* **Request Body**:
  ```json
  {
    "refresh": "<jwt_refresh_token>"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "access": "<new_jwt_access_token>"
  }
  ```
* **Error Response (401 Unauthorized)**:
  ```json
  {
    "detail": "Token is invalid or expired",
    "code": "token_not_valid"
  }
  ```

---

### 4. Current User Profile
* **URL**: `/api/auth/me/`
* **Method**: `GET`
* **Authentication**: `Bearer <jwt_access_token>` in `Authorization` header
* **Success Response (200 OK)**:
  ```json
  {
    "id": 1,
    "username": "tech_sarah",
    "email": "sarah@flightfix.com",
    "first_name": "Sarah",
    "last_name": "Connor",
    "phone": "+1-555-0199",
    "role": "FIELD_TECHNICIAN",
    "is_active": true,
    "is_staff": false,
    "created_at": "2026-11-18T17:20:00Z",
    "updated_at": "2026-11-18T17:20:00Z"
  }
  ```
* **Error Response (401 Unauthorized)**:
  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```

---

## Role-Based Permissions
Located in `apps.accounts.permissions`:
- `IsAdmin`: Restricted to `ADMIN` role or superusers.
- `IsSafetyOfficer`: Restricted to `SAFETY_OFFICER` role or superusers.
- `IsContractsManager`: Restricted to `CONTRACTS_MANAGER` role or superusers.
- `IsFieldTechnician`: Restricted to `FIELD_TECHNICIAN` role or superusers.
- `IsAdminOrSafetyOfficer`: Accessible by `ADMIN` and `SAFETY_OFFICER` roles.

---

## Step 2: Aircraft & Equipment Management (Epic P05-E04)

Manages aircraft fleet assets and major equipment components (US11, US12, US13).

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions (GET, POST, PUT, PATCH, DELETE).
- **SAFETY_OFFICER**: Add, view, update, and search (GET, POST, PUT, PATCH). Deletions are forbidden.
- **CONTRACTS_MANAGER**: View, search, and track records (GET, HEAD, OPTIONS).
- **FIELD_TECHNICIAN**: View records (GET, HEAD, OPTIONS).
- **Unauthenticated**: All endpoints rejected (401 Unauthorized).

---

### Aircraft Endpoints
Base URL: `http://127.0.0.1:8000/api/aircraft/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/aircraft/` | List aircraft (paginated, searchable, filterable) |
| `POST` | `/api/aircraft/` | Register new aircraft |
| `GET` | `/api/aircraft/{id}/` | Retrieve aircraft details including installed equipment |
| `PUT` | `/api/aircraft/{id}/` | Full update of aircraft record |
| `PATCH` | `/api/aircraft/{id}/` | Partial update of aircraft record |
| `DELETE` | `/api/aircraft/{id}/` | Delete aircraft (Admin only) |

#### Filtering & Search Parameters
- `?search=<term>`: Searches `registration_number`, `model`, `aircraft_type`, `manufacturer`, `serial_number`.
- `?status=<ACTIVE|MAINTENANCE|GROUNDED|RETIRED>`: Filters by status.
- `?manufacturer=<name>`: Filters by manufacturer (e.g. `Boeing`, `Airbus`).
- `?aircraft_type=<type>`: Filters by aircraft type.
- `?page=<number>`: Page number (default: 1).
- `?page_size=<number>`: Results per page (default: 10, max: 100).

#### Example Aircraft Payload (`POST /api/aircraft/`)
```json
{
  "registration_number": "VT-FF101",
  "aircraft_type": "Commercial Jet",
  "model": "Boeing 737-800",
  "manufacturer": "Boeing",
  "serial_number": "MSN-30101",
  "status": "ACTIVE",
  "manufacture_date": "2018-05-15",
  "service_entry_date": "2018-08-20",
  "notes": "Operating on domestic trunk routes."
}
```

---

### Equipment Endpoints
Base URL: `http://127.0.0.1:8000/api/equipment/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/equipment/` | List equipment components (paginated, searchable, filterable) |
| `POST` | `/api/equipment/` | Register new equipment |
| `GET` | `/api/equipment/{id}/` | Retrieve equipment details |
| `PUT` | `/api/equipment/{id}/` | Full update of equipment record |
| `PATCH` | `/api/equipment/{id}/` | Partial update of equipment record |
| `DELETE` | `/api/equipment/{id}/` | Delete equipment (Admin only) |

#### Filtering & Search Parameters
- `?search=<term>`: Searches `equipment_code`, `name`, `manufacturer`, `serial_number`, `location`.
- `?status=<OPERATIONAL|UNDER_MAINTENANCE|IN_STORAGE|DECOMMISSIONED>`: Filters by status.
- `?equipment_type=<ENGINE|AVIONICS|LANDING_GEAR|HYDRAULICS|SAFETY|APU|OTHER>`: Filters by component type.
- `?manufacturer=<name>`: Filters by manufacturer.
- `?aircraft=<id_or_tail_number>`: Filters equipment assigned to specific aircraft.
- `?page=<number>&page_size=<number>`: Pagination controls.

#### Example Equipment Payload (`POST /api/equipment/`)
```json
{
  "equipment_code": "EQ-ENG-501",
  "name": "LEAP-1A Turbofan Engine",
  "equipment_type": "ENGINE",
  "manufacturer": "CFM International",
  "serial_number": "SN-LEAP-909",
  "status": "OPERATIONAL",
  "aircraft": 1,
  "location": "Wing Position 1",
  "notes": "Overhauled in Q3."
}
```

---

## Step 3: Maintenance Planning & Scheduling (`apps.maintenance_planning`)

Manages aircraft maintenance schedules, inspection cycles, and associated actionable tasks.

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions on schedules and tasks.
- **SAFETY_OFFICER**: Add, view, update, and search schedules and tasks (`GET`, `POST`, `PUT`, `PATCH`). Deletions are forbidden.
- **CONTRACTS_MANAGER**: View, search, and track schedules and tasks (`GET`, `HEAD`, `OPTIONS`).
- **FIELD_TECHNICIAN**: View schedules and tasks assigned to them (`GET`, `HEAD`, `OPTIONS`).
- **Unauthenticated**: Access rejected (`401 Unauthorized`).

---

### Maintenance Schedule Endpoints
Base URL: `http://127.0.0.1:8000/api/maintenance/schedules/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/maintenance/schedules/` | List schedules (paginated, searchable, filterable) |
| `POST` | `/api/maintenance/schedules/` | Create a new maintenance schedule |
| `GET` | `/api/maintenance/schedules/{id}/` | Retrieve schedule details (includes nested tasks) |
| `PUT` | `/api/maintenance/schedules/{id}/` | Full update of maintenance schedule |
| `PATCH` | `/api/maintenance/schedules/{id}/` | Partial update of maintenance schedule |
| `DELETE` | `/api/maintenance/schedules/{id}/` | Delete maintenance schedule (Admin only) |

#### Filtering & Search Parameters
- `?search=<term>`: Searches `title`, `description`, `aircraft__registration_number`, `aircraft__model`, `assigned_to__username`.
- `?status=<PLANNED|IN_PROGRESS|COMPLETED|CANCELLED>`: Filters by status.
- `?priority=<LOW|MEDIUM|HIGH|CRITICAL>`: Filters by priority.
- `?maintenance_type=<PREVENTIVE|CORRECTIVE|INSPECTION|OVERHAUL>`: Filters by maintenance type.
- `?aircraft=<id_or_tail_number>`: Filters by aircraft ID or registration number.
- `?assigned_to=<id_or_username>`: Filters by assigned technician ID or username.
- `?planned_date=<YYYY-MM-DD>`: Filters by scheduled planned start date.
- `?due_date=<YYYY-MM-DD>`: Filters by latest due date.
- `?page=<number>&page_size=<number>`: Pagination controls (default: 10).

#### Example Schedule Payload (`POST /api/maintenance/schedules/`)
```json
{
  "aircraft": 1,
  "title": "A-Check 500 Flight Hour Inspection",
  "description": "Comprehensive routine airframe and engine inspection.",
  "maintenance_type": "INSPECTION",
  "priority": "HIGH",
  "planned_date": "2026-12-01",
  "due_date": "2026-12-05",
  "status": "PLANNED",
  "assigned_to": 2,
  "notes": "Coordinate with Hangar Bay 3 crew."
}
```

---

### Maintenance Task Endpoints
Base URL: `http://127.0.0.1:8000/api/maintenance/tasks/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/maintenance/tasks/` | List individual tasks (paginated, searchable, filterable) |
| `POST` | `/api/maintenance/tasks/` | Create a new task within a schedule |
| `GET` | `/api/maintenance/tasks/{id}/` | Retrieve task details |
| `PUT` | `/api/maintenance/tasks/{id}/` | Full update of task record |
| `PATCH` | `/api/maintenance/tasks/{id}/` | Partial update of task record |
| `DELETE` | `/api/maintenance/tasks/{id}/` | Delete task (Admin only) |

#### Filtering & Search Parameters
- `?search=<term>`: Searches `task_name`, `description`, `schedule__title`, `schedule__aircraft__registration_number`.
- `?status=<PENDING|IN_PROGRESS|COMPLETED|SKIPPED>`: Filters by task status.
- `?schedule=<schedule_id>`: Filters tasks belonging to a specific schedule.

#### Example Task Payload (`POST /api/maintenance/tasks/`)
```json
{
  "schedule": 1,
  "task_name": "Inspect Main Landing Gear Actuators",
  "description": "Check for hydraulic fluid leakage and micro-cracks.",
  "task_order": 1,
  "status": "PENDING",
  "estimated_hours": "3.50",
  "notes": "Use magnifying scope."
}
```

---

## Step 4: Work Order Management (`apps.work_orders`)

Manages maintenance work orders, technician task tracking, priority scheduling, and execution findings.

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions on work orders (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
- **SAFETY_OFFICER**: Add, view, update, and search work orders (`GET`, `POST`, `PUT`, `PATCH`). Deletions are forbidden (`403 Forbidden`).
- **CONTRACTS_MANAGER**: View, search, and track all work orders (`GET`, `HEAD`, `OPTIONS`). Modifications forbidden (`403 Forbidden`).
- **FIELD_TECHNICIAN**: View-only access (`GET`, `HEAD`, `OPTIONS`) restricted strictly to work orders **assigned to them**. Unassigned or other technicians' work orders are not visible. Modifications are forbidden (`403 Forbidden`).
- **Unauthenticated**: All requests rejected (`401 Unauthorized`).

---

### Work Order Endpoints
Base URL: `http://127.0.0.1:8000/api/work-orders/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/work-orders/` | List work orders (paginated, searchable, filterable) | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (own only) |
| `POST` | `/api/work-orders/` | Create a new work order (`created_by` auto-assigned) | ADMIN, SAFETY_OFFICER |
| `GET` | `/api/work-orders/{id}/` | Retrieve full work order details | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (assigned only) |
| `PUT` | `/api/work-orders/{id}/` | Full update of work order record | ADMIN, SAFETY_OFFICER |
| `PATCH` | `/api/work-orders/{id}/` | Partial update of work order record | ADMIN, SAFETY_OFFICER |
| `DELETE` | `/api/work-orders/{id}/` | Delete work order | ADMIN only |

#### Filtering, Search & Ordering Parameters
- `?search=<term>`: Searches across `work_order_number`, `title`, `description`, `findings`, `corrective_action`, `aircraft__registration_number`, `aircraft__model`, and `assigned_to__username`.
- `?status=<OPEN|ASSIGNED|IN_PROGRESS|ON_HOLD|COMPLETED|CANCELLED>`: Filter by work order status.
- `?priority=<LOW|MEDIUM|HIGH|CRITICAL>`: Filter by priority.
- `?work_order_type=<PREVENTIVE|CORRECTIVE|INSPECTION|EMERGENCY>`: Filter by work order type.
- `?aircraft=<id_or_registration>`: Filter by aircraft primary key or registration number.
- `?assigned_to=<id_or_username>`: Filter by assigned technician primary key or username.
- `?maintenance_schedule=<id>`: Filter by linked maintenance schedule.
- `?planned_start_date=<YYYY-MM-DD>`: Filter by planned start date.
- `?planned_completion_date=<YYYY-MM-DD>`: Filter by planned completion date.
- `?ordering=<field>`: Order results by fields such as `-created_at`, `priority`, `planned_start_date`, etc.
- `?page=<number>&page_size=<number>`: Pagination controls (default: 10, max: 100).

#### Example Work Order Creation Request (`POST /api/work-orders/`)
```json
{
  "work_order_number": "WO-2026-0001",
  "aircraft": 1,
  "maintenance_schedule": 1,
  "title": "Replace Main Gear Brake Assembly",
  "description": "Perform scheduled removal and replacement of left main gear brake assembly.",
  "work_order_type": "CORRECTIVE",
  "priority": "HIGH",
  "status": "OPEN",
  "assigned_to": 2,
  "planned_start_date": "2026-12-01",
  "planned_completion_date": "2026-12-03",
  "estimated_hours": "6.50",
  "notes": "Ensure torque limits comply with AMM Chapter 32-42-01."
}
```

#### Example Work Order Response (`201 Created` / `200 OK`)
```json
{
  "id": 1,
  "work_order_number": "WO-2026-0001",
  "aircraft": 1,
  "aircraft_registration": "VT-FF101",
  "aircraft_model": "Boeing 737-800",
  "maintenance_schedule": 1,
  "maintenance_schedule_title": "A-Check 500 Flight Hour Inspection",
  "title": "Replace Main Gear Brake Assembly",
  "description": "Perform scheduled removal and replacement of left main gear brake assembly.",
  "work_order_type": "CORRECTIVE",
  "work_order_type_display": "Corrective",
  "priority": "HIGH",
  "priority_display": "High",
  "status": "OPEN",
  "status_display": "Open",
  "assigned_to": 2,
  "assigned_to_username": "tech_sarah",
  "created_by": 1,
  "created_by_username": "admin_john",
  "planned_start_date": "2026-12-01",
  "planned_completion_date": "2026-12-03",
  "actual_start_date": null,
  "actual_completion_date": null,
  "estimated_hours": "6.50",
  "actual_hours": null,
  "findings": "",
  "corrective_action": "",
  "notes": "Ensure torque limits comply with AMM Chapter 32-42-01.",
  "created_at": "2026-11-19T04:30:00Z",
  "updated_at": "2026-11-19T04:30:00Z"
}
```

---

## Step 5: Spare Parts Inventory (`apps.inventory`)

Manages aircraft spare parts, warehouse stock levels, reorder thresholds, and tracks full transaction logs (receipts, issues, returns, and audit adjustments).

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions on spare parts and inventory transactions (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
- **SAFETY_OFFICER**: Add, view, and update spare parts and transactions (`GET`, `POST`, `PUT`, `PATCH`). Deletions are forbidden (`403 Forbidden`).
- **CONTRACTS_MANAGER**: View, search, and track spare parts and transaction logs (`GET`, `HEAD`, `OPTIONS`). Modifications are forbidden (`403 Forbidden`).
- **FIELD_TECHNICIAN**: View, search, and check stock levels and transaction logs (`GET`, `HEAD`, `OPTIONS`). Modifications are forbidden (`403 Forbidden`).
- **Unauthenticated**: All requests rejected (`401 Unauthorized`).

---

### Spare Part Endpoints
Base URL: `http://127.0.0.1:8000/api/inventory/parts/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/inventory/parts/` | List spare parts (paginated, searchable, filterable) | All Authenticated |
| `POST` | `/api/inventory/parts/` | Register a new spare part | ADMIN, SAFETY_OFFICER |
| `GET` | `/api/inventory/parts/{id}/` | Retrieve spare part details + recent transactions | All Authenticated |
| `PUT` | `/api/inventory/parts/{id}/` | Full update of spare part record | ADMIN, SAFETY_OFFICER |
| `PATCH` | `/api/inventory/parts/{id}/` | Partial update of spare part record | ADMIN, SAFETY_OFFICER |
| `DELETE` | `/api/inventory/parts/{id}/` | Delete spare part | ADMIN only |

#### Filtering, Search & Ordering Parameters
- `?search=<term>`: Searches across `part_number`, `name`, `description`, `manufacturer`, `manufacturer_part_number`, `category`, `location`, `supplier`.
- `?status=<IN_STOCK|LOW_STOCK|OUT_OF_STOCK|DISCONTINUED>`: Filter by stock status.
- `?category=<category>`: Filter by category (e.g. `AVIONICS`, `ENGINE`, `HYDRAULICS`, `LANDING_GEAR`, `CABIN`, `HARDWARE`, etc.).
- `?manufacturer=<name>`: Case-insensitive manufacturer search.
- `?supplier=<name>`: Case-insensitive supplier search.
- `?location=<name>`: Case-insensitive warehouse/bin search.
- `?low_stock=true`: Filters items with `LOW_STOCK` status or `quantity_in_stock <= minimum_stock_level`.
- `?ordering=<field>`: Order results (e.g. `part_number`, `quantity_in_stock`, `unit_price`, `-created_at`).
- `?page=<number>&page_size=<number>`: Pagination controls (default: 10, max: 100).

#### Example Spare Part Creation Request (`POST /api/inventory/parts/`)
```json
{
  "part_number": "PN-HYD-737-01",
  "name": "Hydraulic Pressure Relief Valve",
  "description": "Main hydraulic return line pressure relief valve assembly.",
  "category": "HYDRAULICS",
  "manufacturer": "Parker Aerospace",
  "manufacturer_part_number": "PK-PRV-990",
  "quantity_in_stock": 15,
  "minimum_stock_level": 5,
  "unit_price": "1250.00",
  "location": "Warehouse-1 / Bin-H04",
  "supplier": "Aero Supply Global"
}
```

---

### Inventory Transaction Endpoints
Base URL: `http://127.0.0.1:8000/api/inventory/transactions/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/inventory/transactions/` | List transaction logs (paginated, searchable, filterable) | All Authenticated |
| `POST` | `/api/inventory/transactions/` | Create transaction (`RECEIPT`, `ISSUE`, `ADJUSTMENT`, `RETURN`) | ADMIN, SAFETY_OFFICER |
| `GET` | `/api/inventory/transactions/{id}/` | Retrieve transaction details | All Authenticated |
| `PUT` | `/api/inventory/transactions/{id}/` | Update transaction reference/notes | ADMIN, SAFETY_OFFICER |
| `PATCH` | `/api/inventory/transactions/{id}/` | Partial update reference/notes | ADMIN, SAFETY_OFFICER |
| `DELETE` | `/api/inventory/transactions/{id}/` | Delete transaction | ADMIN only |

#### Filtering & Search Parameters
- `?search=<term>`: Searches `reference`, `notes`, `spare_part__part_number`, `spare_part__name`, `performed_by__username`.
- `?spare_part=<id_or_part_number>`: Filter transactions for a specific part.
- `?transaction_type=<RECEIPT|ISSUE|ADJUSTMENT|RETURN>`: Filter by movement type.
- `?performed_by=<user_id_or_username>`: Filter by user who logged the transaction.
- `?date_from=<YYYY-MM-DD>` / `?date_to=<YYYY-MM-DD>`: Filter by transaction date range.

#### Example Inventory Transaction Creation Request (`POST /api/inventory/transactions/`)
```json
{
  "spare_part": 1,
  "transaction_type": "ISSUE",
  "quantity": 2,
  "reference": "WO-2026-0001",
  "notes": "Issued to technician for scheduled hydraulic valve replacement."
}
```

#### Example Inventory Transaction Response (`201 Created`)
```json
{
  "id": 1,
  "spare_part": 1,
  "spare_part_number": "PN-HYD-737-01",
  "spare_part_name": "Hydraulic Pressure Relief Valve",
  "transaction_type": "ISSUE",
  "transaction_type_display": "Issue",
  "quantity": 2,
  "reference": "WO-2026-0001",
  "performed_by": 1,
  "performed_by_username": "admin_john",
  "notes": "Issued to technician for scheduled hydraulic valve replacement.",
  "created_at": "2026-11-19T05:30:00Z"
}
```

---

## Step 6: Maintenance Execution & Documentation (`apps.maintenance_execution`)

Manages real-time technician maintenance execution, tracking labor hours, technical findings, corrective actions, and regulatory sign-off documentation (Certificates of Release to Service, QA checklists).

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions on maintenance executions and documentation records (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
- **SAFETY_OFFICER**: Add, view, and update execution and sign-off records (`GET`, `POST`, `PUT`, `PATCH`). Deletions are forbidden (`403 Forbidden`).
- **CONTRACTS_MANAGER**: View and track execution records and compliance documentation (`GET`, `HEAD`, `OPTIONS`). Modifications are forbidden (`403 Forbidden`).
- **FIELD_TECHNICIAN**: View and update **only execution records and documentation assigned to them** (`GET`, `PUT`, `PATCH`). Unauthorized access to other technicians' records or deletions are forbidden (`403 Forbidden`).
- **Unauthenticated**: All requests rejected (`401 Unauthorized`).

---

### Maintenance Execution Records Endpoints
Base URL: `http://127.0.0.1:8000/api/maintenance-execution/records/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/maintenance-execution/records/` | List execution records (paginated, searchable, filterable) | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (assigned only) |
| `POST` | `/api/maintenance-execution/records/` | Log new maintenance execution record | ADMIN, SAFETY_OFFICER, FIELD_TECHNICIAN (own) |
| `GET` | `/api/maintenance-execution/records/{id}/` | Retrieve execution details + compliance documents | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (assigned only) |
| `PUT` | `/api/maintenance-execution/records/{id}/` | Full update of execution record | ADMIN, SAFETY_OFFICER, FIELD_TECHNICIAN (assigned only) |
| `PATCH` | `/api/maintenance-execution/records/{id}/` | Partial update of execution record | ADMIN, SAFETY_OFFICER, FIELD_TECHNICIAN (assigned only) |
| `DELETE` | `/api/maintenance-execution/records/{id}/` | Delete execution record | ADMIN only |

#### Filtering, Search & Ordering Parameters
- `?search=<term>`: Searches across `work_order__work_order_number`, `aircraft__registration_number`, `aircraft__model`, `executed_by__username`, `work_performed`, `findings`, `corrective_actions`, `remarks`.
- `?status=<PENDING|IN_PROGRESS|PAUSED|COMPLETED|CANCELLED>`: Filter by execution status.
- `?work_order=<id_or_number>`: Filter by work order ID or work order number.
- `?aircraft=<id_or_registration>`: Filter by aircraft ID or registration number.
- `?executed_by=<id_or_username>`: Filter by assigned technician.
- `?start_date=<YYYY-MM-DD>&end_date=<YYYY-MM-DD>`: Filter by date range.
- `?ordering=<field>`: Order results (e.g. `-created_at`, `started_at`, `completed_at`, `actual_labor_hours`).
- `?page=<number>&page_size=<number>`: Pagination controls (default: 10, max: 100).

#### Example Execution Record Request (`POST /api/maintenance-execution/records/`)
```json
{
  "work_order": 1,
  "executed_by": 2,
  "status": "COMPLETED",
  "started_at": "2026-11-19T06:00:00Z",
  "completed_at": "2026-11-19T09:30:00Z",
  "actual_labor_hours": "3.50",
  "work_performed": "Removed worn main gear brake rotor and stator assemblies. Cleaned wheel hub and torque plate. Installed new carbon heat pack.",
  "findings": "Rotor friction material thickness measured 0.08 in, below AMM wear limit.",
  "corrective_actions": "Replaced brake pack with serviceable assembly PN-BRK-737-01. Torqued retention bolts to 85 ft-lb.",
  "remarks": "Brake pressure test completed successfully with zero hydraulic seepage."
}
```

---

### Maintenance Documentation Endpoints
Base URL: `http://127.0.0.1:8000/api/maintenance-execution/documentation/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/maintenance-execution/documentation/` | List compliance records (searchable, filterable) | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (assigned only) |
| `POST` | `/api/maintenance-execution/documentation/` | Create technical certificate / sign-off record | ADMIN, SAFETY_OFFICER |
| `GET` | `/api/maintenance-execution/documentation/{id}/` | Retrieve technical document details | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (assigned only) |
| `PUT` | `/api/maintenance-execution/documentation/{id}/` | Full update of documentation record | ADMIN, SAFETY_OFFICER |
| `PATCH` | `/api/maintenance-execution/documentation/{id}/` | Partial update / Sign-off approval | ADMIN, SAFETY_OFFICER |
| `DELETE` | `/api/maintenance-execution/documentation/{id}/` | Delete documentation record | ADMIN only |

#### Example Compliance Sign-Off Request (`POST /api/maintenance-execution/documentation/`)
```json
{
  "execution": 1,
  "document_type": "RELEASE_TO_SERVICE",
  "document_number": "CRS-2026-0042",
  "title": "Certificate of Release to Service - Brake Replacement",
  "issuing_authority": "FlightFix QA & Airworthiness Division",
  "document_reference": "DMS://2026/AIRCRAFT/VT-FF101/CRS-0042.pdf",
  "sign_off_status": "SIGNED",
  "signed_off_by": 1,
  "signed_off_at": "2026-11-19T10:00:00Z",
  "remarks": "The work described above was carried out in accordance with applicable airworthiness regulations and AMM Chapter 32."
}
```

---

## Step 7: Airworthiness & Regulatory Compliance (`apps.compliance`)

Manages Airworthiness Directives (ADs), Service Bulletins (SBs), regulatory inspection mandates, and compliance verification audit records.

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions on compliance requirements and verification audit records (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
- **SAFETY_OFFICER**: Add, view, update requirements and verify compliance records (`GET`, `POST`, `PUT`, `PATCH`). Deletions are forbidden (`403 Forbidden`).
- **CONTRACTS_MANAGER**: View, search, and track all compliance requirements and audit records (`GET`, `HEAD`, `OPTIONS`). Modifications are forbidden (`403 Forbidden`).
- **FIELD_TECHNICIAN**: View compliance requirements and audit records **strictly relevant to aircraft or maintenance tasks assigned to them** (`GET`, `HEAD`, `OPTIONS`). Unrelated fleet records are filtered out, and modifications/deletions are forbidden (`403 Forbidden`).
- **Unauthenticated**: All requests rejected (`401 Unauthorized`).

---

### Compliance Requirements Endpoints
Base URL: `http://127.0.0.1:8000/api/compliance/requirements/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/compliance/requirements/` | List requirements (paginated, searchable, filterable) | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (relevant) |
| `POST` | `/api/compliance/requirements/` | Register new regulatory requirement | ADMIN, SAFETY_OFFICER |
| `GET` | `/api/compliance/requirements/{id}/` | Retrieve requirement details + verification audit history | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (relevant) |
| `PUT` | `/api/compliance/requirements/{id}/` | Full update of requirement record | ADMIN, SAFETY_OFFICER |
| `PATCH` | `/api/compliance/requirements/{id}/` | Partial update of requirement record | ADMIN, SAFETY_OFFICER |
| `DELETE` | `/api/compliance/requirements/{id}/` | Delete requirement | ADMIN only |

#### Filtering, Search & Ordering Parameters
- `?search=<term>`: Searches `requirement_code`, `title`, `description`, `issuing_authority`, `aircraft__registration_number`, `assigned_to__username`.
- `?status=<OPEN|IN_PROGRESS|COMPLIANT|NON_COMPLIANT|EXPIRED>`: Filter by compliance status.
- `?priority=<LOW|MEDIUM|HIGH|CRITICAL>`: Filter by priority.
- `?regulation_type=<type>`: Filter by mandate type (`AIRWORTHINESS_DIRECTIVE`, `SERVICE_BULLETIN`, `INSPECTION_REQUIREMENT`, `SAFETY_REQUIREMENT`, `INTERNAL_POLICY`, `OTHER`).
- `?aircraft=<id_or_registration>`: Filter by aircraft.
- `?assigned_to=<id_or_username>`: Filter by assigned safety officer or engineer.
- `?due_date=<YYYY-MM-DD>` / `?effective_date=<YYYY-MM-DD>`: Filter by regulatory dates.
- `?ordering=<field>`: Order results (e.g. `due_date`, `priority`, `requirement_code`, `-created_at`).
- `?page=<number>&page_size=<number>`: Pagination controls (default: 10, max: 100).

#### Example Requirement Creation Request (`POST /api/compliance/requirements/`)
```json
{
  "requirement_code": "AD-2026-FAA-01",
  "title": "Wing Spar Ultrasonic Inspection",
  "description": "Mandatory repetitive eddy-current and ultrasonic inspection of rear wing spar web.",
  "regulation_type": "AIRWORTHINESS_DIRECTIVE",
  "issuing_authority": "Federal Aviation Administration (FAA)",
  "aircraft": 1,
  "effective_date": "2026-11-01",
  "due_date": "2026-12-15",
  "priority": "CRITICAL",
  "status": "IN_PROGRESS",
  "assigned_to": 2,
  "notes": "Verify calibrated ultrasonic probe model USN-60 before testing."
}
```

---

### Compliance Verification Records Endpoints
Base URL: `http://127.0.0.1:8000/api/compliance/records/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/compliance/records/` | List verification records (searchable, filterable) | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (relevant) |
| `POST` | `/api/compliance/records/` | Log new compliance verification record | ADMIN, SAFETY_OFFICER |
| `GET` | `/api/compliance/records/{id}/` | Retrieve verification record details | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER, FIELD_TECHNICIAN (relevant) |
| `PUT` | `/api/compliance/records/{id}/` | Full update of verification record | ADMIN, SAFETY_OFFICER |
| `PATCH` | `/api/compliance/records/{id}/` | Partial update / certify verification record | ADMIN, SAFETY_OFFICER |
| `DELETE` | `/api/compliance/records/{id}/` | Delete verification record | ADMIN only |

#### Example Compliance Verification Request (`POST /api/compliance/records/`)
```json
{
  "requirement": 1,
  "verification_status": "VERIFIED",
  "verified_by": 2,
  "verified_at": "2026-11-19T06:30:00Z",
  "evidence_reference": "NDT-REPORT-2026-88 / CRS-2026-0042",
  "findings": "Zero crack indications detected across left and right wing stations 240-300.",
  "remarks": "Complies in full with AD-2026-FAA-01 paragraph (g). Next inspection due in 500 flight cycles."
}
```

---

## Step 8: ERP & Supply Chain Integration (`apps.supply_chain`)

Manages vendors/suppliers, purchase orders, line items, delivery tracking, and automated inventory receiving workflows integrated with `apps.inventory.SparePart`.

### Role Permissions Matrix
- **ADMIN**: Full CRUD permissions on suppliers, purchase orders, and items; approve purchase orders; execute warehouse receiving workflows.
- **SAFETY_OFFICER**: Add, view, and update suppliers and purchase orders (`GET`, `POST`, `PUT`, `PATCH`); execute warehouse receiving workflows. Deletions are forbidden (`403 Forbidden`).
- **CONTRACTS_MANAGER**: Add, view, and update suppliers and purchase orders (`GET`, `POST`, `PUT`, `PATCH`); execute warehouse receiving workflows. Deletions are forbidden (`403 Forbidden`).
- **FIELD_TECHNICIAN**: View-only access (`GET`, `HEAD`, `OPTIONS`) to relevant procurement and parts information. Cannot create, edit, delete, or receive purchase orders (`403 Forbidden`).
- **Unauthenticated**: All requests rejected (`401 Unauthorized`).

---

### Suppliers Endpoints
Base URL: `http://127.0.0.1:8000/api/supply-chain/suppliers/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/supply-chain/suppliers/` | List suppliers (paginated, searchable, filterable) | All Authenticated |
| `POST` | `/api/supply-chain/suppliers/` | Register new supplier | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |
| `GET` | `/api/supply-chain/suppliers/{id}/` | Retrieve supplier details | All Authenticated |
| `PUT` | `/api/supply-chain/suppliers/{id}/` | Full update of supplier record | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |
| `PATCH` | `/api/supply-chain/suppliers/{id}/` | Partial update of supplier record | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |
| `DELETE` | `/api/supply-chain/suppliers/{id}/` | Delete supplier | ADMIN only |

#### Example Supplier Creation Request (`POST /api/supply-chain/suppliers/`)
```json
{
  "supplier_code": "VEND-PARKER-01",
  "name": "Parker Aerospace Supply Corporation",
  "contact_person": "David Miller",
  "email": "dmiller@parkeraero.com",
  "phone": "+1-555-0188",
  "address": "14300 Alton Parkway",
  "city": "Irvine",
  "country": "USA",
  "status": "ACTIVE",
  "supplier_type": "OEM",
  "notes": "Approved OEM supplier for Boeing and Airbus hydraulic assemblies."
}
```

---

### Purchase Orders Endpoints
Base URL: `http://127.0.0.1:8000/api/supply-chain/purchase-orders/`
All requests require header: `Authorization: Bearer <jwt_access_token>`

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/supply-chain/purchase-orders/` | List purchase orders (paginated, searchable, filterable) | All Authenticated |
| `POST` | `/api/supply-chain/purchase-orders/` | Create a new purchase order | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |
| `GET` | `/api/supply-chain/purchase-orders/{id}/` | Retrieve purchase order + line items | All Authenticated |
| `PUT` | `/api/supply-chain/purchase-orders/{id}/` | Full update of purchase order | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |
| `PATCH` | `/api/supply-chain/purchase-orders/{id}/` | Partial update of purchase order | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |
| `DELETE` | `/api/supply-chain/purchase-orders/{id}/` | Delete purchase order | ADMIN only |
| `POST` | `/api/supply-chain/purchase-orders/{id}/receive/` | Receive ordered quantities into inventory | ADMIN, SAFETY_OFFICER, CONTRACTS_MANAGER |

#### Example Purchase Order Creation Request (`POST /api/supply-chain/purchase-orders/`)
```json
{
  "po_number": "PO-2026-0001",
  "supplier": 1,
  "order_date": "2026-11-19",
  "expected_delivery_date": "2026-12-05",
  "priority": "HIGH",
  "status": "APPROVED",
  "delivery_address": "FlightFix Hangar Bay 1, Airport Cargo Complex",
  "notes": "Expedite shipment for scheduled A-Check maintenance."
}
```

---

### Custom Receiving Workflow (`POST /api/supply-chain/purchase-orders/{id}/receive/`)

Receives delivery quantities for line items, atomically updates inventory, and creates audit transactions.

#### Example Receiving Request:
```json
{
  "items": [
    {
      "purchase_order_item": 1,
      "quantity_received": 10
    }
  ],
  "notes": "Delivered via DHL Express Air Freight."
}
```

#### Automated Receiving Effects:
1. Validates that requested quantity does not exceed remaining pending quantity (`quantity_ordered - quantity_received`).
2. Atomically increments `PurchaseOrderItem.quantity_received`.
3. Creates `InventoryTransaction(type=RECEIPT, quantity=qty, reference=po.po_number, performed_by=request.user)`.
4. Automatically increments `inventory.SparePart.quantity_in_stock` and recalculates stock status (`IN_STOCK`, `LOW_STOCK`, `OUT_OF_STOCK`).
5. Updates `PurchaseOrder.status`:
   - Transitions to `RECEIVED` if all line items are completely fulfilled.
   - Transitions to `PARTIALLY_RECEIVED` if only partial quantities are received.
   - Sets `actual_delivery_date` on completion.

---

## Running Automated Tests

To execute tests against the Supabase PostgreSQL test database, use `--keepdb` to preserve database connection pooling:

```powershell
cd backend
# Run all tests
.\venv\Scripts\python.exe manage.py test --keepdb

# Run individual modules
.\venv\Scripts\python.exe manage.py test apps.accounts --keepdb
.\venv\Scripts\python.exe manage.py test apps.aircraft --keepdb
.\venv\Scripts\python.exe manage.py test apps.maintenance_planning --keepdb
.\venv\Scripts\python.exe manage.py test apps.work_orders --keepdb
.\venv\Scripts\python.exe manage.py test apps.inventory --keepdb
.\venv\Scripts\python.exe manage.py test apps.maintenance_execution --keepdb
.\venv\Scripts\python.exe manage.py test apps.compliance --keepdb
.\venv\Scripts\python.exe manage.py test apps.supply_chain --keepdb
.\venv\Scripts\python.exe manage.py test apps.mobile --keepdb
.\venv\Scripts\python.exe manage.py test apps.analytics --keepdb
```

---

## Step 9: Mobile App / Field Technician Support APIs

The `apps.mobile` module exposes safe, compact, high-performance REST APIs tailored specifically for `FIELD_TECHNICIAN` users to power mobile devices and React Native clients.

### Architecture & Database Rules
- **No new database models or tables required**: Reuses normalized models from `accounts`, `aircraft`, `maintenance_planning`, `work_orders`, `maintenance_execution`, `compliance`, and `inventory`.
- **Queryset-level isolation & IDOR prevention**: Technicians can only access and modify their assigned schedules, tasks, work orders, executions, and relevant aircraft.
- **Strict Role-Based Access Control**:
  - `401 Unauthorized`: Unauthenticated requests.
  - `403 Forbidden`: Authenticated requests from non-technician roles (`ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER`).
  - `200 OK / 201 Created`: Authenticated `FIELD_TECHNICIAN` users.
- **Tamper-Proofing Protected Fields**: Technicians can update execution fields on assigned work orders (`status`, `findings`, `corrective_action`, `actual_hours`, `notes`, `actual_start_date`, `actual_completion_date`), but cannot reassign technicians, change aircraft, or alter administrative priorities.
- **Information Protection**: Available spare parts inventory is exposed in a read-only view that strictly omits unit costs, supplier identities, and procurement metadata.

---

### Mobile API Endpoints

Base URL: `http://127.0.0.1:8000/api/mobile/`

| Method | Endpoint | Description | Role Access |
|---|---|---|---|
| `GET` | `/api/mobile/dashboard/` | Compact dashboard (technician profile, summary counts, assigned aircraft, tasks, work orders, recent executions) | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-tasks/` | List assigned maintenance tasks (supports status, planned_date, due_date, search, ordering, pagination) | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-tasks/{id}/` | Retrieve assigned task detail | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-work-orders/` | List assigned work orders (supports status, priority, aircraft, search, ordering, pagination) | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-work-orders/{id}/` | Retrieve assigned work order detail | FIELD_TECHNICIAN |
| `PATCH` | `/api/mobile/my-work-orders/{id}/` | Safe update of execution fields (`status`, `actual_hours`, `findings`, `corrective_action`, `notes`) | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-executions/` | List executions performed by logged-in technician | FIELD_TECHNICIAN |
| `POST` | `/api/mobile/my-executions/` | Create execution record for an assigned work order | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-executions/{id}/` | Retrieve execution record detail | FIELD_TECHNICIAN |
| `PATCH` | `/api/mobile/my-executions/{id}/` | Update execution narrative, hours, or status | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-aircraft/` | List aircraft relevant to technician's assigned tasks/work orders/executions | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-aircraft/{id}/` | Retrieve relevant aircraft detail | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-compliance/` | Read-only compliance records relevant to assigned aircraft | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/my-compliance/{id}/` | Retrieve relevant compliance record detail | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/available-parts/` | Read-only spare parts list (no pricing or supplier info) | FIELD_TECHNICIAN |
| `GET` | `/api/mobile/available-parts/{id}/` | Retrieve spare part stock status & location | FIELD_TECHNICIAN |

---

### Sample Field Technician Dashboard Response (`GET /api/mobile/dashboard/`)

```json
{
  "technician": {
    "id": 4,
    "username": "tech_alex",
    "name": "Alex Rivera",
    "first_name": "Alex",
    "last_name": "Rivera",
    "email": "tech_alex@flightfix.com",
    "phone": "+1-555-0144",
    "role": "FIELD_TECHNICIAN"
  },
  "summary": {
    "assigned_schedules": 1,
    "pending_tasks": 2,
    "open_work_orders": 1,
    "pending_compliance": 1
  },
  "assigned_aircraft": [
    {
      "id": 1,
      "registration_number": "N101FF",
      "aircraft_type": "Commercial Passenger",
      "model": "Boeing 737-800",
      "manufacturer": "Boeing",
      "serial_number": "SN-737-101",
      "status": "MAINTENANCE",
      "status_display": "Under Maintenance"
    }
  ],
  "tasks": [
    {
      "id": 1,
      "schedule": 1,
      "schedule_title": "737 500-Hour Inspection",
      "aircraft_registration": "N101FF",
      "aircraft_model": "Boeing 737-800",
      "task_name": "Inspect Left Wing Actuators",
      "description": "Check hydraulic actuator seal integrity.",
      "task_order": 1,
      "status": "IN_PROGRESS",
      "status_display": "In Progress",
      "estimated_hours": "3.50",
      "planned_date": "2026-11-19",
      "due_date": "2026-11-26",
      "priority": "HIGH",
      "priority_display": "High"
    }
  ],
  "work_orders": [
    {
      "id": 1,
      "work_order_number": "WO-2026-0001",
      "aircraft": 1,
      "aircraft_registration": "N101FF",
      "aircraft_model": "Boeing 737-800",
      "title": "Replace Hydraulic Actuator O-Rings",
      "work_order_type": "CORRECTIVE",
      "priority": "HIGH",
      "status": "IN_PROGRESS",
      "status_display": "In Progress",
      "actual_hours": "1.50"
    }
  ],
  "recent_executions": [
    {
      "id": 1,
      "work_order": 1,
      "work_order_number": "WO-2026-0001",
      "aircraft_registration": "N101FF",
      "status": "IN_PROGRESS",
      "status_display": "In Progress",
      "actual_labor_hours": "2.00",
      "work_performed": "Removed hydraulic panel and disassembled actuator casing."
    }
  ]
}
```

---

### Example Technician Work Order Execution Update (`PATCH /api/mobile/my-work-orders/1/`)

```json
{
  "status": "COMPLETED",
  "actual_hours": "4.50",
  "findings": "All seals replaced with new Viton rings.",
  "corrective_action": "Torqued casing bolts to 45 Nm.",
  "notes": "Ready for quality verification.",
  "actual_start_date": "2026-11-19",
  "actual_completion_date": "2026-11-19"
}
```

---

### Example Technician Execution Creation (`POST /api/mobile/my-executions/`)

```json
{
  "work_order": 1,
  "maintenance_task": 2,
  "status": "IN_PROGRESS",
  "actual_labor_hours": "1.50",
  "work_performed": "Applied Aeroshell 22 grease to actuator slide mechanisms.",
  "remarks": "Slide mechanism moving freely."
}
```
*Note*: `executed_by`, `created_by`, and `aircraft` are securely inferred from the logged-in user and validated work order assignment. IDOR attempts to log execution against other technicians' work orders are strictly rejected.

---

## Step 10: Analytics & Reporting APIs

The `apps.analytics` module provides high-performance, strictly read-only management analytics and operational reporting APIs across fleet operations, scheduled maintenance, spare parts inventory, airworthiness compliance, and supply chain procurement.

### Architecture & Database Rules
- **No new database models or tables**: Reuses existing models from all 9 prior modules without schema alterations.
- **ORM-Level Aggregation & Performance**: Utilizes `Count()`, `Sum()`, `F()`, `Q()`, and distinct subquery lookups directly in PostgreSQL to prevent N+1 queries and eliminate Cartesian join inflation.
- **Strict Role-Based Access Control**:
  - `ADMIN`: Full access across all management analytics.
  - `SAFETY_OFFICER`: Full access to maintenance, aircraft, safety, compliance, and operational analytics.
  - `CONTRACTS_MANAGER`: Full access to supply-chain, inventory, procurement, and operational analytics.
  - `FIELD_TECHNICIAN`: Restricted from management analytics (`403 Forbidden`).
  - Unauthenticated requests: Rejected (`401 Unauthorized`).
- **Strict Method Restrictions**: Read-only (`GET`, `HEAD`, `OPTIONS`). All state-mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`) return `405 Method Not Allowed`.
- **Date Range Validation**: Optional `start_date` and `end_date` parameters are validated in ISO `YYYY-MM-DD` format with explicit `start_date <= end_date` integrity enforcement (`400 Bad Request` on invalid input).

---

### Analytics Endpoints Catalog

Base URL: `http://127.0.0.1:8000/api/analytics/`

| Method | Endpoint | Description | Permitted Roles | Query Parameters |
|---|---|---|---|---|
| `GET` | `/api/analytics/dashboard/` | Executive management dashboard with fleet, maintenance, parts, compliance, and PO counts | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | None |
| `GET` | `/api/analytics/maintenance-summary/` | Maintenance KPIs: schedules, work orders, executions, completed vs pending, overdue counts | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | `start_date`, `end_date` (YYYY-MM-DD) |
| `GET` | `/api/analytics/aircraft-summary/` | Fleet breakdown by status, type, manufacturer, and per-aircraft maintenance activity | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | None |
| `GET` | `/api/analytics/inventory-summary/` | Inventory KPIs: stock levels, transaction counts, frequently issued parts, low-stock reorder alerts | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | None |
| `GET` | `/api/analytics/compliance-summary/` | Airworthiness directives & service bulletins status, priority, expired counts, and verification audits | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | None |
| `GET` | `/api/analytics/supply-chain-summary/` | Procurement KPIs: supplier statuses, purchase order priority/status, total order value, delivery progress | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | None |
| `GET` | `/api/analytics/technician-performance/` | Technician operational performance: assigned/completed work orders, executions, actual labor hours, task progress | `ADMIN`, `SAFETY_OFFICER`, `CONTRACTS_MANAGER` | None |

---

### Sample Management Dashboard Response (`GET /api/analytics/dashboard/`)

```json
{
  "total_aircraft": 2,
  "active_aircraft": 1,
  "total_maintenance_schedules": 3,
  "pending_maintenance_schedules": 2,
  "overdue_maintenance_schedules": 1,
  "completed_maintenance_schedules": 1,
  "total_work_orders": 2,
  "open_work_orders": 1,
  "open_in_progress_work_orders": 1,
  "completed_work_orders": 1,
  "total_maintenance_executions": 1,
  "total_spare_parts": 3,
  "low_stock_spare_parts": 1,
  "out_of_stock_spare_parts": 1,
  "open_compliance_requirements": 1,
  "non_compliant_requirements": 1,
  "expired_requirements": 1,
  "total_suppliers": 1,
  "active_suppliers": 1,
  "purchase_orders_by_status": {
    "DRAFT": 0,
    "APPROVED": 1,
    "ORDERED": 0,
    "PARTIALLY_RECEIVED": 0,
    "RECEIVED": 1,
    "CANCELLED": 0
  }
}
```

---

### Sample Maintenance Summary Response with Date Filtering (`GET /api/analytics/maintenance-summary/?start_date=2026-11-01&end_date=2026-11-30`)

```json
{
  "schedules_by_status": {
    "PLANNED": 1,
    "IN_PROGRESS": 1,
    "COMPLETED": 1,
    "CANCELLED": 0
  },
  "schedules_by_maintenance_type": {
    "PREVENTIVE": 1,
    "CORRECTIVE": 1,
    "INSPECTION": 1,
    "OVERHAUL": 0
  },
  "schedules_by_priority": {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 1,
    "CRITICAL": 1
  },
  "work_orders_by_status": {
    "OPEN": 0,
    "ASSIGNED": 0,
    "IN_PROGRESS": 1,
    "ON_HOLD": 0,
    "COMPLETED": 1,
    "CANCELLED": 0
  },
  "work_orders_by_priority": {
    "LOW": 0,
    "MEDIUM": 0,
    "HIGH": 1,
    "CRITICAL": 1
  },
  "executions_by_status": {
    "PENDING": 0,
    "IN_PROGRESS": 0,
    "PAUSED": 0,
    "COMPLETED": 1,
    "CANCELLED": 0
  },
  "completed_vs_pending_maintenance": {
    "completed_schedules": 1,
    "pending_schedules": 2,
    "completed_work_orders": 1,
    "pending_work_orders": 1
  },
  "overdue_maintenance_count": 1,
  "date_filter": {
    "start_date": "2026-11-01",
    "end_date": "2026-11-30"
  }
}
```

---

### Sample Technician Performance Response (`GET /api/analytics/technician-performance/`)

```json
{
  "total_technicians": 1,
  "technicians": [
    {
      "technician_id": 4,
      "technician_name": "Tim Tech",
      "username": "analytics_tech",
      "assigned_work_orders": 2,
      "completed_work_orders": 1,
      "maintenance_executions": 1,
      "total_actual_labor_hours": "6.00",
      "pending_tasks": 1,
      "completed_tasks": 1
    }
  ]
}
```
*Note*: Personal credentials, passwords, tokens, phone numbers, and emails are strictly omitted from reporting payloads.


