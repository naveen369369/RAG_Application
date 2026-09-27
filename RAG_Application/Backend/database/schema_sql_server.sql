-- ============================================================================
-- Support CRM Database Schema for Microsoft SQL Server (T-SQL)
-- Target: SQL Server 2016+ / Azure SQL Database
-- ============================================================================

-- Optional: Create Database if needed
-- CREATE DATABASE SupportCRM;
-- GO
-- USE SupportCRM;
-- GO

-- 1. DROP EXISTING TABLES IN REVERSE ORDER OF DEPENDENCY
IF OBJECT_ID(N'dbo.ticket_escalation_events', N'U') IS NOT NULL DROP TABLE dbo.ticket_escalation_events;
IF OBJECT_ID(N'dbo.support_tickets', N'U') IS NOT NULL DROP TABLE dbo.support_tickets;
IF OBJECT_ID(N'dbo.order_items', N'U') IS NOT NULL DROP TABLE dbo.order_items;
IF OBJECT_ID(N'dbo.orders', N'U') IS NOT NULL DROP TABLE dbo.orders;
IF OBJECT_ID(N'dbo.customers', N'U') IS NOT NULL DROP TABLE dbo.customers;
GO

-- ============================================================================
-- 2. TABLE: customers
-- Stores customer accounts, tiers (basic, premium, vip), and contact info.
-- Customer tier dictates SLA resolution time and priority escalation.
-- ============================================================================
CREATE TABLE dbo.customers (
    id                VARCHAR(32)   NOT NULL,
    name              NVARCHAR(120) NOT NULL,
    email             NVARCHAR(120) NOT NULL,
    phone             VARCHAR(50)   NULL,
    tier              VARCHAR(20)   NOT NULL CONSTRAINT DF_customers_tier DEFAULT ('basic'),
    account_status    VARCHAR(30)   NOT NULL CONSTRAINT DF_customers_status DEFAULT ('active'),
    preferred_contact VARCHAR(30)   NOT NULL CONSTRAINT DF_customers_contact DEFAULT ('email'),
    created_at        DATETIME2     NOT NULL CONSTRAINT DF_customers_created DEFAULT (SYSUTCDATETIME()),

    CONSTRAINT PK_customers PRIMARY KEY CLUSTERED (id),
    CONSTRAINT CK_customers_tier CHECK (tier IN ('basic', 'premium', 'vip')),
    CONSTRAINT CK_customers_status CHECK (account_status IN ('active', 'suspended', 'pending'))
);
GO

CREATE NONCLUSTERED INDEX IX_customers_email ON dbo.customers(email);
GO

-- ============================================================================
-- 3. TABLE: orders
-- Stores customer orders, fulfillment statuses, carriers, and tracking numbers.
-- ============================================================================
CREATE TABLE dbo.orders (
    id               VARCHAR(32)    NOT NULL,
    customer_id      VARCHAR(32)    NOT NULL,
    status           VARCHAR(30)    NOT NULL CONSTRAINT DF_orders_status DEFAULT ('processing'),
    carrier          VARCHAR(50)    NULL,
    tracking_number  VARCHAR(100)   NULL,
    order_total      DECIMAL(12, 2) NOT NULL CONSTRAINT DF_orders_total DEFAULT (0.00),
    shipping_address NVARCHAR(255)  NULL,
    order_date       DATETIME2      NOT NULL CONSTRAINT DF_orders_order_date DEFAULT (SYSUTCDATETIME()),
    delivered_date   DATETIME2      NULL,

    CONSTRAINT PK_orders PRIMARY KEY CLUSTERED (id),
    CONSTRAINT FK_orders_customers FOREIGN KEY (customer_id) 
        REFERENCES dbo.customers(id) ON DELETE CASCADE,
    CONSTRAINT CK_orders_status CHECK (status IN ('processing', 'shipped', 'delivered', 'cancelled', 'returned'))
);
GO

CREATE NONCLUSTERED INDEX IX_orders_customer_id ON dbo.orders(customer_id);
CREATE NONCLUSTERED INDEX IX_orders_tracking ON dbo.orders(tracking_number);
GO

-- ============================================================================
-- 4. TABLE: order_items
-- Stores line items for each order, including the physical item condition
-- ('unopened', 'opened', 'damaged', 'missing') queried by the LLM for refund logic.
-- ============================================================================
CREATE TABLE dbo.order_items (
    id             INT IDENTITY(1,1) NOT NULL,
    order_id       VARCHAR(32)       NOT NULL,
    product_name   NVARCHAR(150)     NOT NULL,
    sku            VARCHAR(50)       NULL,
    quantity       INT               NOT NULL CONSTRAINT DF_order_items_qty DEFAULT (1),
    unit_price     DECIMAL(12, 2)    NOT NULL CONSTRAINT DF_order_items_price DEFAULT (0.00),
    item_condition VARCHAR(30)       NOT NULL CONSTRAINT DF_order_items_condition DEFAULT ('unopened'),

    CONSTRAINT PK_order_items PRIMARY KEY CLUSTERED (id),
    CONSTRAINT FK_order_items_orders FOREIGN KEY (order_id)
        REFERENCES dbo.orders(id) ON DELETE CASCADE,
    CONSTRAINT CK_order_items_condition CHECK (item_condition IN ('unopened', 'opened', 'damaged', 'missing'))
);
GO

CREATE NONCLUSTERED INDEX IX_order_items_order_id ON dbo.order_items(order_id);
GO

-- ============================================================================
-- 5. TABLE: support_tickets
-- Stores customer inquiries and complaint tickets, linked to customer & order.
-- Queried live by the ReAct Agent using the ticket_lookup tool.
-- ============================================================================
CREATE TABLE dbo.support_tickets (
    id               VARCHAR(32)    NOT NULL,
    customer_id      VARCHAR(32)    NOT NULL,
    order_id         VARCHAR(32)    NULL,
    subject          NVARCHAR(255)  NOT NULL,
    description      NVARCHAR(MAX)  NOT NULL,
    category         VARCHAR(50)    NOT NULL CONSTRAINT DF_tickets_category DEFAULT ('general'),
    priority         VARCHAR(20)    NOT NULL CONSTRAINT DF_tickets_priority DEFAULT ('standard'),
    status           VARCHAR(30)    NOT NULL CONSTRAINT DF_tickets_status DEFAULT ('open'),
    resolution_notes NVARCHAR(MAX)  NULL,
    created_at       DATETIME2      NOT NULL CONSTRAINT DF_tickets_created DEFAULT (SYSUTCDATETIME()),
    updated_at       DATETIME2      NOT NULL CONSTRAINT DF_tickets_updated DEFAULT (SYSUTCDATETIME()),

    CONSTRAINT PK_support_tickets PRIMARY KEY CLUSTERED (id),
    CONSTRAINT FK_tickets_customers FOREIGN KEY (customer_id)
        REFERENCES dbo.customers(id) ON DELETE NO ACTION,
    CONSTRAINT FK_tickets_orders FOREIGN KEY (order_id)
        REFERENCES dbo.orders(id) ON DELETE NO ACTION,
    CONSTRAINT CK_tickets_priority CHECK (priority IN ('low', 'standard', 'high', 'urgent')),
    CONSTRAINT CK_tickets_status CHECK (status IN ('open', 'in_progress', 'escalated', 'waiting_customer', 'resolved', 'closed')),
    CONSTRAINT CK_tickets_category CHECK (category IN ('shipping', 'return_refund', 'billing', 'technical', 'account', 'general'))
);
GO

CREATE NONCLUSTERED INDEX IX_support_tickets_customer_id ON dbo.support_tickets(customer_id);
CREATE NONCLUSTERED INDEX IX_support_tickets_order_id ON dbo.support_tickets(order_id);
CREATE NONCLUSTERED INDEX IX_support_tickets_status ON dbo.support_tickets(status);
GO

-- ============================================================================
-- 5. TABLE: ticket_escalation_events
-- Chronological audit trail for escalated support tickets.
-- Consumed by MCP Server 2 (Ticket History Server) via JSON-RPC.
-- ============================================================================
CREATE TABLE dbo.ticket_escalation_events (
    id          INT           IDENTITY(1,1) NOT NULL,
    ticket_id   VARCHAR(32)   NOT NULL,
    timestamp   DATETIME2     NOT NULL CONSTRAINT DF_escalation_timestamp DEFAULT (SYSUTCDATETIME()),
    actor       VARCHAR(100)  NOT NULL,
    action      VARCHAR(50)   NOT NULL,
    note        NVARCHAR(MAX) NOT NULL,

    CONSTRAINT PK_ticket_escalation_events PRIMARY KEY CLUSTERED (id),
    CONSTRAINT FK_escalation_ticket FOREIGN KEY (ticket_id)
        REFERENCES dbo.support_tickets(id) ON DELETE CASCADE
);
GO

CREATE NONCLUSTERED INDEX IX_escalation_ticket_id ON dbo.ticket_escalation_events(ticket_id);
CREATE NONCLUSTERED INDEX IX_escalation_timestamp ON dbo.ticket_escalation_events(timestamp);
GO

-- ============================================================================
-- 6. INITIAL SEED DATA
-- Default customer tiers, orders, items, and active tickets
-- ============================================================================
INSERT INTO dbo.customers (id, name, email, phone, tier, account_status, preferred_contact) VALUES
('C001', 'Alice Johnson', 'alice.johnson@example.com', '+1-555-0101', 'basic',   'active',    'email'),
('C002', 'Bob Smith',     'bob.smith@example.com',     '+1-555-0102', 'premium', 'active',    'phone'),
('C003', 'Carol White',   'carol.white@example.com',   '+1-555-0103', 'premium', 'active',    'email'),
('C004', 'David Lee',     'david.lee@example.com',     '+1-555-0104', 'basic',   'suspended', 'email'),
('C005', 'Eva Martinez',  'eva.martinez@example.com',  '+1-555-0105', 'vip',     'active',    'dedicated_rep');
GO

INSERT INTO dbo.orders (id, customer_id, status, carrier, tracking_number, order_total, shipping_address, order_date, delivered_date) VALUES
('ORD-1001', 'C001', 'delivered',  'FedEx', 'FDX-9982341',         129.99, '742 Evergreen Terrace, Springfield, OR', DATEADD(DAY, -10, SYSUTCDATETIME()), DATEADD(DAY, -7, SYSUTCDATETIME())),
('ORD-1002', 'C002', 'shipped',    'UPS',   '1Z9999999999999999',  249.50, '221B Baker St, London, UK',             DATEADD(DAY, -3, SYSUTCDATETIME()),  NULL),
('ORD-1003', 'C003', 'delivered',  'DHL',   'DHL-55441209',        89.00,  '100 Tech Blvd, Austin, TX',             DATEADD(DAY, -5, SYSUTCDATETIME()),  DATEADD(DAY, -1, SYSUTCDATETIME())),
('ORD-1004', 'C005', 'processing', 'FedEx', 'FDX-11223344',        1450.00,'1 Penthouse Way, Manhattan, NY',        DATEADD(HOUR, -12, SYSUTCDATETIME()), NULL);
GO

INSERT INTO dbo.order_items (order_id, product_name, sku, quantity, unit_price, item_condition) VALUES
('ORD-1001', 'Wireless Noise-Cancelling Headphones', 'TECH-WNC-01', 1, 129.99, 'opened'),
('ORD-1002', 'Mechanical Ergonomic Keyboard',        'KEY-RGB-09',  1, 149.50, 'unopened'),
('ORD-1002', 'USB-C Dual 4K Docking Station',        'DOCK-4K-02',  1, 100.00, 'unopened'),
('ORD-1003', 'Smart Water Bottle with Sensor',       'BTL-TEMP-04', 1, 89.00,  'damaged'),
('ORD-1004', 'Ultra-Wide 49-inch Curved Monitor',    'MON-49-CURV', 1, 1450.00,'unopened');
GO

INSERT INTO dbo.support_tickets (id, customer_id, order_id, subject, description, category, priority, status, resolution_notes) VALUES
('TCK-1001', 'C001', 'ORD-1001', 'Refund requested for opened headphones', 'I opened and tested the headphones, but they feel uncomfortable on my ears. Can I still return them for a refund?', 'return_refund', 'standard', 'open', NULL),
('TCK-1002', 'C002', 'ORD-1002', 'Address change request for in-transit package', 'I need to redirect my keyboard delivery to my office address because I will be traveling this week.', 'shipping', 'high', 'in_progress', NULL),
('TCK-1003', 'C003', 'ORD-1003', 'Package arrived damaged - crushed box', 'The smart water bottle package arrived completely crushed and the screen is cracked. Photos are ready.', 'return_refund', 'high', 'open', NULL),
('TCK-1004', 'C004', NULL,       'Account suspended - need access to billing invoices', 'My account shows suspended status when logging in. I need access to download past invoices for tax purposes.', 'account', 'standard', 'escalated', 'Billing supervisor unlocked invoice download portal and verified 2FA authentication.');
GO

INSERT INTO dbo.ticket_escalation_events (ticket_id, timestamp, actor, action, note) VALUES
-- TCK-1004 Escalation Audit Trail (Account Suspended - Tax Invoices)
('TCK-1004', '2024-02-10 08:35:00', 'L1-Agent-Sarah',       'opened',             'Ticket received from customer portal regarding account suspension and tax invoice urgency.'),
('TCK-1004', '2024-02-10 10:15:00', 'L1-Agent-Sarah',       'escalated',          'Escalated to Tier-2 Billing: L1 lacks authority to override suspended account security block.'),
('TCK-1004', '2024-02-10 13:40:00', 'L2-Supervisor-Marcus', 'approved_override',  'Supervisor Marcus verified customer tax registration and approved temporary read-only invoice access.'),
('TCK-1004', '2024-02-10 15:00:00', 'billing-bot',           'resolved',           'Sent secure 1-time link for past tax invoices. Customer confirmed successful download.'),

-- TCK-1002 Escalation Audit Trail (Address Change In-Transit)
('TCK-1002', '2024-02-12 09:00:00', 'L1-Agent-Emma',        'opened',             'Customer requested reroute of keyboard delivery to office address.'),
('TCK-1002', '2024-02-12 11:30:00', 'L1-Agent-Emma',        'escalated',          'Package already in-transit with UPS. Escalated to Logistics Supervisor for carrier intercept.'),
('TCK-1002', '2024-02-12 14:00:00', 'L2-Supervisor-Raj',    'approved_override',  'UPS Delivery Intercept fee waived; submitted new address to carrier portal.'),

-- TCK-1003 Escalation Audit Trail (Damaged Item)
('TCK-1003', '2024-02-08 14:10:00', 'L1-Agent-Priya',       'opened',             'Customer reported smart water bottle arrived completely crushed.'),
('TCK-1003', '2024-02-08 15:00:00', 'L1-Agent-Priya',       'pending_customer',   'Requested customer submit photos of damaged box and cracked bottle display.'),

-- TCK-1001 Escalation Audit Trail (Opened Item Return)
('TCK-1001', '2024-01-10 09:05:00', 'L1-Agent-Priya',       'opened',             'Return request received for opened noise-cancelling headphones.'),
('TCK-1001', '2024-01-10 10:30:00', 'L1-Agent-Priya',       'pending_customer',   'Awaiting customer clarification: defect vs personal comfort change-of-mind.');
GO

-- Verification query
SELECT 'Customers' AS Entity, COUNT(*) AS TotalCount FROM dbo.customers
UNION ALL
SELECT 'Orders', COUNT(*) FROM dbo.orders
UNION ALL
SELECT 'OrderItems', COUNT(*) FROM dbo.order_items
UNION ALL
SELECT 'SupportTickets', COUNT(*) FROM dbo.support_tickets
UNION ALL
SELECT 'TicketEscalationEvents', COUNT(*) FROM dbo.ticket_escalation_events;
GO
