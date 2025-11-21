---
title: "Design the SQL schema for a simple e-commerce platform with Products, Customers, and Orders. How would you model the many-to-many relationship between Orders and Products?"
date: 2025-11-21
categories: [System Design, Database Design]
tags: [sql, schema, ecommerce, database, many-to-many, relational, normalisation]
toc: true
layout: post
---

As Principal Software Engineers, designing robust and scalable database schemas is a fundamental skill. For an e-commerce platform, even a simple one, understanding how to model relationships between core entities like Customers, Products, and Orders is paramount. This post will walk you through designing a basic SQL schema and focus on the critical **many-to-many relationship** between Orders and Products.

## 1. The Core Concept

Imagine a bustling restaurant. A **customer** can place many **orders** over time. Each **order** can contain multiple **dishes**, and a single **dish** can appear in many different orders placed by various customers. This perfectly illustrates a many-to-many relationship.

> A **many-to-many relationship** (M:N) exists when multiple records in one table can be associated with multiple records in another table. In our e-commerce context, a single `Order` can include multiple `Products`, and a single `Product` can be included in multiple `Orders`.

## 2. Deep Dive & Architecture

To effectively manage these relationships in a **relational database**, we typically employ a technique called **normalization**. This involves breaking down data into separate tables and linking them using **foreign keys**.

### Core Entities Schema

We'll start by defining our three primary entities: `Customers`, `Products`, and `Orders`.

#### Customers

This table stores information about each individual customer.

sql
CREATE TABLE Customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    zip_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-   `customer_id`: A **primary key** (`PRIMARY KEY`), uniquely identifying each customer. `AUTO_INCREMENT` ensures new IDs are generated automatically.
-   `email`: Enforced as `UNIQUE` to prevent duplicate customer accounts and `NOT NULL`.

#### Products

This table holds details for all items available for purchase.

sql
CREATE TABLE Products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    category VARCHAR(100),
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);


-   `product_id`: The **primary key** for each product.
-   `price`: Uses `DECIMAL(10, 2)` for accurate monetary values.
-   `stock_quantity`: Tracks available inventory.

#### Orders

This table stores general information about each order placed. Each order belongs to a specific customer.

sql
CREATE TABLE Orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled') NOT NULL DEFAULT 'Pending',
    shipping_address VARCHAR(255),
    billing_address VARCHAR(255),
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);


-   `order_id`: The **primary key** for each order.
-   `customer_id`: A **foreign key** (`FOREIGN KEY`) linking back to the `Customers` table, establishing a **one-to-many relationship** (one customer can have many orders).
-   `total_amount`: The sum of all items in the order, calculated upon order creation/update.
-   `status`: An `ENUM` type to enforce specific order states.

### Modeling the Many-to-Many Relationship: Order_Items (Junction Table)

This is where we address the core challenge: an order can have multiple products, and a product can be in multiple orders. We solve this by introducing an **intermediate** or **junction table**, often called `Order_Items` or `Order_Products`. This table links `Orders` and `Products` and stores details specific to that particular item within that particular order.

sql
CREATE TABLE Order_Items (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL, -- Price at the time of order
    item_total DECIMAL(10, 2) NOT NULL, -- quantity * unit_price
    FOREIGN KEY (order_id) REFERENCES Orders(order_id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id),
    UNIQUE (order_id, product_id) -- Ensures a product appears only once per order
);


-   `order_item_id`: A **primary key** for each line item within an order.
-   `order_id`: A **foreign key** to the `Orders` table.
-   `product_id`: A **foreign key** to the `Products` table.
-   `quantity`: The number of units of that specific product within this order.
-   `unit_price`: **Crucially**, this stores the product's price *at the time the order was placed*. Product prices can change over time, so storing this value ensures historical accuracy for financial reporting and order details.
-   `item_total`: The calculated `quantity * unit_price`.
-   `UNIQUE (order_id, product_id)`: This composite unique constraint ensures that a particular product can only be listed once within a single order, but if the customer wants more, `quantity` is increased.

> **Pro Tip:** Always store the `unit_price` (and potentially `product_name`, `product_description`) directly in the `Order_Items` table. Relying solely on a `product_id` to fetch current product details would mean historical orders change their details if the product's price or name is updated, which is almost never desired for order integrity.

### Visualizing the Relationships


Customers (customer_id PK)
    |
    | One-to-Many
    V
Orders (order_id PK, customer_id FK)
    |
    | Many-to-Many (via Order_Items)
    V
Order_Items (order_item_id PK, order_id FK, product_id FK)
    ^
    | Many-to-Many (via Order_Items)
    |
Products (product_id PK)


## 3. Comparison / Trade-offs

The junction table approach is the **standard and recommended method** for handling many-to-many relationships in relational databases due to its adherence to database normalization principles. Let's compare it to a common, but ill-advised, alternative: denormalization.

| Feature / Approach       | Normalized (Junction Table)                       | Denormalized (Array/JSON in Orders Table)                               |
| :----------------------- | :------------------------------------------------ | :------------------------------------------------------------------------ |
| **Data Integrity**       | High. Referential integrity ensured by FKs.       | Low. No built-in database constraints, data can become inconsistent.      |
| **Data Redundancy**      | Minimal. Product details stored once.             | High. Product details (or IDs) duplicated across orders.                  |
| **Query Complexity**     | Requires `JOIN` operations to get full details.   | Simpler for basic "what products in this order?" (if IDs only).           |
| **Query Flexibility**    | Excellent. Easy to query "all orders for a product" or "all products in an order".                               | Poor. Complex to query products across multiple orders or aggregate data.  |
| **Scalability**          | Highly scalable. Handles large datasets efficiently.                                                                | Poor. Can lead to large `orders` table rows, inefficient indexing.       |
| **Schema Evolution**     | Easy to add new attributes to `Order_Items` (e.g., discounts).                                                  | Difficult. Requires complex schema migrations for embedded data.         |
| **Historical Accuracy**  | Excellent (e.g., `unit_price` captured at time of order).                                                              | Poor (if only IDs stored); complex if full product data embedded.         |
| **Storage Efficiency**   | Good. Only necessary linking data stored in junction table.                                                     | Can be poor if full product details are embedded repeatedly.             |

> **Warning:** While some NoSQL databases might encourage embedding document structures, in a **relational database context**, directly embedding lists of product IDs or product details within the `Orders` table (e.g., as a JSON string, comma-separated list, or array) is an **anti-pattern**. It sacrifices data integrity, leads to complex querying, and hinders performance for anything beyond the most trivial use cases.

## 4. Real-World Use Case

This schema design, particularly the use of a junction table for orders and products, is the backbone of virtually **every major e-commerce platform** globally. Think about companies like:

*   **Amazon**: When you buy multiple items, each item is a line entry, linked to your single order.
*   **Shopify**: Merchants rely on this structure to manage inventory, process orders, and generate sales reports.
*   **eBay**: Similar to Amazon, every transaction details specific items linked to a buyer's order.
*   **Target/Walmart (Online)**: Their internal systems use this model to track customer purchases, manage fulfillment, and analyze sales data.

The "Why" is clear:

1.  **Accuracy & Integrity**: It ensures that each product within an order is accurately recorded, including its specific quantity and the price *at the time of purchase*. This is crucial for financial reconciliation and preventing discrepancies if product prices change later.
2.  **Reporting & Analytics**: It enables powerful reporting. You can easily answer questions like:
    *   "What are the most popular products sold in the last quarter?"
    *   "Which customers frequently buy product X?"
    *   "What was the total revenue from orders containing product Y?"
3.  **Inventory Management**: By linking products to orders via quantities, inventory systems can accurately deduct stock when orders are placed and fulfilled.
4.  **Flexibility**: The design is flexible enough to allow for future enhancements, such as adding discounts per item, return status, or even tracking specific product serial numbers directly within the `Order_Items` table, without altering the core `Products` or `Orders` tables.

In conclusion, a well-designed SQL schema, utilizing normalization and junction tables for many-to-many relationships, is critical for building a scalable, maintainable, and data-consistent e-commerce platform.