---
title: "Revisit the Hotel Booking Problem: Database Schema and Concurrency Strategies"
date: 2025-07-15
categories: [System Design, Database Design]
tags: [concurrency, locking, database, hotelbooking, systemdesign, distributedtransactions, sql]
toc: true
layout: post
---

The challenge of efficiently and reliably managing bookings for limited resources is a classic in system design. Whether it's a hotel room, an airline seat, or an event ticket, ensuring that a resource is never double-booked, even under heavy concurrent demand, is paramount. This post dives into designing a robust database schema and exploring common locking strategies to tackle the **Hotel Booking Problem**.

## 1. The Core Concept

Imagine a popular hotel during peak season. Multiple guests, perhaps thousands across different booking platforms, might try to reserve the same room for overlapping dates simultaneously. Without proper controls, the system could inadvertently confirm bookings for more than one party, leading to disgruntled customers and operational nightmares.

> **Definition**: The **Hotel Booking Problem** refers to the challenge of ensuring atomicity and consistency in a multi-user environment where multiple clients may attempt to reserve the same limited resource (e.g., a hotel room) for overlapping time periods, preventing double bookings and maintaining data integrity. It's fundamentally a **concurrency control** problem.

It's akin to two people simultaneously reaching for the last cookie in a jar. Who gets it? A well-designed system ensures only one person's request is successfully fulfilled, while others are gracefully informed of the unavailability.

## 2. Deep Dive & Architecture

To solve this, we need a robust database schema that clearly defines our resources and bookings, coupled with a strategy to manage concurrent access.

### 2.1. Database Schema Design

Our schema needs to represent hotels, rooms, and most critically, the bookings themselves, along with their associated date ranges.

sql
-- Hotels Table
CREATE TABLE Hotels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Room Types Table (e.g., "Standard", "Deluxe", "Suite")
CREATE TABLE RoomTypes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    capacity INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Rooms Table (Specific physical rooms within a hotel)
CREATE TABLE Rooms (
    id SERIAL PRIMARY KEY,
    hotel_id INT NOT NULL REFERENCES Hotels(id),
    room_number VARCHAR(50) NOT NULL,
    room_type_id INT NOT NULL REFERENCES RoomTypes(id),
    price_per_night DECIMAL(10, 2) NOT NULL,
    -- Add a version column for optimistic locking if managing room-level attributes
    version INT DEFAULT 1, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (hotel_id, room_number) -- A room number must be unique per hotel
);

-- Users Table (Customers making bookings)
CREATE TABLE Users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bookings Table (The core of our problem)
CREATE TABLE Bookings (
    id SERIAL PRIMARY KEY,
    room_id INT NOT NULL REFERENCES Rooms(id),
    user_id INT NOT NULL REFERENCES Users(id),
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- e.g., 'pending', 'confirmed', 'cancelled'
    total_price DECIMAL(10, 2) NOT NULL,
    -- A version column for optimistic locking *on this specific booking record*
    -- Useful for concurrent updates to a booking's status or details
    version INT DEFAULT 1, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint: check_out_date must be after check_in_date
    CHECK (check_out_date > check_in_date)
);

-- Crucial for preventing double bookings: Exclusion Constraint
-- This ensures that for a given room, no two bookings have overlapping date ranges.
-- This example uses PostgreSQL's daterange type and GiST index.
-- Other databases might require application-level checks within a transaction or other approaches.
CREATE EXTENSION IF NOT EXISTS btree_gist; -- Required for GIST index on non-range types
ALTER TABLE Bookings ADD CONSTRAINT no_overlap_booking
EXCLUDE USING GIST (
    room_id WITH =,
    daterange(check_in_date, check_out_date, '[]') WITH && -- '[]' means inclusive of start/end dates
);

-- Indices for performance
CREATE INDEX idx_bookings_room_id ON Bookings (room_id);
CREATE INDEX idx_bookings_user_id ON Bookings (user_id);
CREATE INDEX idx_bookings_dates ON Bookings (check_in_date, check_out_date);


> **Pro Tip**: The `EXCLUDE USING GIST` constraint in PostgreSQL is incredibly powerful for solving date range overlap problems directly at the database level. If your database doesn't support similar exclusion constraints, you'll need to implement the overlap check logic carefully within a transaction.

### 2.2. Concurrency Control Strategies

Now, let's explore how we handle concurrent requests attempting to book the same room.

#### 2.2.1. Pessimistic Locking

**Pessimistic locking** assumes that conflicts are likely and prevents them by acquiring a lock on the resource *before* performing any operations. This means only one transaction can access the locked resource at a time.

**How it works:**
When a user attempts to book a room, the system first acquires an exclusive lock on the `Room` row or an advisory lock related to the room. This prevents other concurrent transactions from even checking the availability of that room for the duration of the current transaction. After verifying availability and inserting the booking, the lock is released.

**Example Pseudo-code (using SQL `FOR UPDATE`):**

sql
-- Transaction 1: User A tries to book Room X for 2025-08-01 to 2025-08-05
BEGIN;

-- 1. Acquire an exclusive lock on the specific Room row.
--    This prevents other transactions from modifying or locking this room.
SELECT id, version FROM Rooms WHERE id = <room_id> FOR UPDATE;

-- 2. Check for existing overlapping bookings for this room.
--    If an exclusion constraint is in place (as designed), this check is implicit
--    in the INSERT step. Otherwise, a SELECT COUNT(*) is needed.
--    For robustness, a check might still be performed to give better error messages.
SELECT COUNT(*) FROM Bookings
WHERE room_id = <room_id>
AND check_in_date < '2025-08-05' -- New check_out_date
AND check_out_date > '2025-08-01'; -- New check_in_date

-- 3. If no conflicts found (or if the database constraint will handle it):
INSERT INTO Bookings (room_id, user_id, check_in_date, check_out_date, status, total_price)
VALUES (<room_id>, <user_id_A>, '2025-08-01', '2025-08-05', 'confirmed', <calculated_price>);

COMMIT;
-- The lock on Rooms.<room_id> is released here.


#### 2.2.2. Optimistic Locking (with versioning)

**Optimistic locking** assumes that conflicts are rare. Instead of locking resources upfront, it allows multiple transactions to proceed. Conflicts are detected *only at the point of commit* by checking if the underlying data has changed since it was initially read. If a conflict is detected, the transaction is rolled back, and the user is typically prompted to retry.

**How it works (for booking a new room):**
For *preventing new overlapping bookings*, optimistic locking relies on a final database constraint (like our `EXCLUDE USING GIST`) or a transactional check-and-insert that atomically verifies availability. A `version` column is typically used to prevent concurrent *updates to the same record*.

Let's illustrate with the `version` column on the `Bookings` table, useful if we were *updating an existing booking* (e.g., changing its dates or status). For *new bookings*, the power lies in the database's ability to reject overlapping inserts.

**Example Pseudo-code (relying on DB exclusion constraint):**

sql
-- Transaction 1: User B tries to book Room Y for 2025-09-10 to 2025-09-15
BEGIN;

-- 1. Read room details and existing bookings without locking.
--    The system optimistically assumes the room is still available.
--    (No `FOR UPDATE` here).
SELECT id FROM Rooms WHERE id = <room_id>;
-- Optionally, application-level checks for overlap can be done here,
-- but the final guard is the DB constraint.

-- 2. Attempt to insert the new booking.
--    The `version` column for a new booking usually starts at 1.
INSERT INTO Bookings (room_id, user_id, check_in_date, check_out_date, status, total_price, version)
VALUES (<room_id>, <user_id_B>, '2025-09-10', '2025-09-15', 'pending', <calculated_price>, 1);

COMMIT;
-- If another transaction already inserted an overlapping booking,
-- the `EXCLUDE` constraint will cause this `INSERT` to fail.
-- The application must catch this error and inform the user to retry or that the room is unavailable.


> **Warning**: While `version` columns are central to optimistic locking, for the *specific problem of preventing date range overlaps for new bookings*, a database-level exclusion constraint (like in PostgreSQL) is generally more robust and performant than trying to manage overlaps purely with application-level version checks on a booking table without such a constraint. The `version` column is more directly applicable when *updating* an existing booking or managing a finite pool of *identical* resources.

## 3. Comparison / Trade-offs

Choosing between pessimistic and optimistic locking strategies involves understanding their inherent trade-offs.

### Pessimistic vs. Optimistic Locking

| Feature                 | Pessimistic Locking                                       | Optimistic Locking                                        |
| :---------------------- | :-------------------------------------------------------- | :-------------------------------------------------------- |
| **Concurrency**         | Lower; resources are locked, reducing parallel access.    | Higher; resources are not locked, allowing more parallel operations. |
| **Conflict Detection**  | Immediate; conflicts are prevented before they occur.     | Late; conflicts are detected at commit time.              |
| **Deadlocks**           | Possible; careful ordering of lock acquisition is needed. | Not applicable (no explicit locks held).                  |
| **Latency**             | Higher; waits for locks to be released.                   | Lower (on reads); but can incur retry overhead on conflicts. |
| **Application Logic**   | Simpler for conflict resolution (db handles it).          | More complex; requires retry mechanisms and conflict resolution. |
| **Use Case**            | High contention environments, critical sections, short transactions. | Low contention environments, long-running transactions, read-heavy workloads. |

### Database Constraints vs. Application-Level Locking

The `EXCLUDE USING GIST` constraint in PostgreSQL offers a very powerful, database-native approach to the date overlap problem. It's worth comparing against manual application-level locking.

| Feature                 | Database Exclusion Constraint (e.g., PostgreSQL)        | Application-level Pessimistic Locking (`FOR UPDATE`) |
| :---------------------- | :-------------------------------------------------------- | :--------------------------------------------------- |
| **Guarantees**          | Atomic, database-enforced integrity.                      | Relies on correct application logic and transaction boundaries. |
| **Complexity**          | Simpler application code (just `INSERT`), but initial DB setup can be complex for specific constraints. | More complex application logic to manage locks and ensure correctness. |
| **Performance**         | Highly optimized by the database's indexing.              | Can introduce overhead due to lock acquisition/release and potential contention. |
| **Database Portability**| Database-specific (e.g., PostgreSQL's `GIST`/`daterange`). | More broadly applicable across different SQL databases. |
| **Error Handling**      | `INSERT` simply fails, application catches error.         | Application handles explicit `FOR UPDATE` errors or deadlocks. |

> **Recommendation**: For the Hotel Booking Problem in a relational database, especially with PostgreSQL, combining an **optimistic approach** (attempt to insert without upfront locking) with a robust **database-level exclusion constraint** is often the most efficient and reliable solution. It leverages the database's power for atomic conflict resolution while allowing high concurrency. For databases without such constraints, a transactional approach with pessimistic locking on the `Room` row is the next best robust option.

## 4. Real-World Use Case

Concurrency control isn't just for hotels. This problem pattern is pervasive in systems dealing with **finite, shared resources**.

*   **Airline Ticketing Systems**: Ensuring a seat on a flight is only sold once, even when hundreds of people are trying to book simultaneously. Here, each seat for a specific flight is a unique resource with limited availability.
*   **Event Ticketing Platforms (e.g., Concerts, Sports)**: Preventing overselling of specific seats or general admission tickets. Similar to airlines, but often with more complex pricing tiers and group bookings.
*   **E-commerce Inventory Management**: When an item has limited stock (e.g., "only 3 left!"), ensuring that two customers don't successfully purchase the last available unit simultaneously, leading to an oversell situation.
*   **Meeting Room Booking Systems**: Preventing multiple meetings from being scheduled in the same room at the same time. This is a direct parallel to the hotel booking problem with date/time ranges.
*   **Healthcare Appointment Scheduling**: Ensuring a doctor's time slot or a specific medical device is booked by only one patient at a time.

**Why is it crucial?**
In all these scenarios, the cost of a **double booking** or **overselling** is high:
*   **Financial Loss**: Refunds, compensation, or lost revenue from unavailable resources.
*   **Customer Dissatisfaction**: Negative user experience, damage to reputation, lost trust.
*   **Operational Headaches**: Manual reconciliation, customer service escalations, logistical nightmares.

Robust database design and well-thought-out concurrency strategies are not just good practice; they are fundamental to the reliability and success of any system managing critical, shared resources.