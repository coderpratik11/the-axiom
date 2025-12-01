---
title: "Design a hotel booking system. The main challenge is handling concurrency: how do you prevent two users from booking the same last available room at the same time?"
date: 2025-12-01
categories: [System Design, Concurrency]
tags: [hotel booking, system design, concurrency, distributed systems, locking, transactions, database]
toc: true
layout: post
---

The challenge of ensuring data consistency in highly concurrent systems is a cornerstone of robust software design. In the context of a hotel booking system, this translates directly to preventing the dreaded "double booking" – a scenario where two users simultaneously attempt to book the very last available room, and both succeed. This not only leads to frustrated customers but also operational nightmares for the hotel.

As Principal Software Engineers, designing systems that flawlessly handle such edge cases is part of our core responsibility. Let's delve into how we can tackle this.

## 1. The Core Concept

Imagine a popular concert where only one ticket remains. Multiple fans are frantically trying to purchase it online at the exact same moment. How does the system ensure that only *one* fan gets the ticket, and the others are immediately informed it's sold out, without any ambiguity or error? This is the essence of the problem we're solving.

> **Concurrency Control** is a mechanism in a multi-user system designed to ensure that when multiple operations occur simultaneously, the integrity and consistency of the data are maintained. It prevents **race conditions** and other data anomalies, guaranteeing that the final state of the system is correct and predictable. For hotel bookings, this specifically means ensuring a room is only booked once, even if multiple requests arrive at the same instant for the *same* last available room.

## 2. Deep Dive & Architecture

To prevent double bookings, our booking system needs a robust concurrency control strategy. We'll explore a couple of primary approaches often used in production systems.

### Database Transactions with Locking

The most fundamental way to ensure data consistency in a multi-user environment is through database transactions combined with locking mechanisms.

#### Pessimistic Locking

**Pessimistic locking** assumes that conflicts are likely to occur, so it acquires a lock on the resource (e.g., a database row representing a room) *before* performing any operations. This lock prevents other transactions from accessing or modifying the resource until the current transaction completes.

**Booking Flow with Pessimistic Locking:**

1.  **User Request:** A user selects a room and dates, then clicks "Book Now."
2.  **Service Initiates Transaction:** The backend booking service starts a database transaction.
3.  **Acquire Lock:** The service attempts to select the specific room record for update.
    sql
    -- Example for PostgreSQL or MySQL
    SELECT room_id, status FROM Rooms 
    WHERE room_id = 'XYZ-101' AND availability_date = '2025-01-01' 
    FOR UPDATE;
    
    This `FOR UPDATE` clause tells the database to lock this specific row. If another transaction has already locked it, this query will block until the lock is released.
4.  **Check Availability:** Once the lock is acquired, the service checks the `status` column.
    *   If `status` is 'available', proceed.
    *   If `status` is already 'booked' (meaning another transaction had already processed it and committed before this transaction acquired the lock after waiting), the current transaction rolls back and informs the user the room is no longer available.
5.  **Update Status:** If available, the service updates the room's status to 'booked' and creates a new booking record.
    sql
    UPDATE Rooms SET 
        status = 'booked', 
        booked_by_user_id = 'user123', 
        booking_time = NOW() 
    WHERE room_id = 'XYZ-101' AND availability_date = '2025-01-01';
    
    INSERT INTO Bookings (booking_id, room_id, user_id, check_in_date, ...) 
    VALUES ('B-001', 'XYZ-101', 'user123', '2025-01-01', ...);
    
6.  **Commit Transaction:** The transaction is committed. This releases the lock and makes the changes permanent and visible to all other transactions.
7.  **Response:** The user receives a booking confirmation.

> **Pro Tip:** Database transactions are ACID (Atomicity, Consistency, Isolation, Durability) compliant. They are critical for ensuring that either all operations within a logical unit of work succeed or none do. `FOR UPDATE` ensures Isolation by preventing concurrent modifications.

#### Optimistic Locking

**Optimistic locking** assumes that conflicts are rare. Instead of locking resources upfront, it allows transactions to proceed concurrently. It only checks for conflicts at the *point of writing* by using a version number or timestamp. If a conflict is detected (i.e., the resource was modified by another transaction since it was read), the current transaction fails and typically retries or informs the user.

**Booking Flow with Optimistic Locking:**

1.  **User Request & Read:** User clicks "Book Now." The service reads the room's current state, including a `version` number (e.g., `version=1`).
    sql
    SELECT room_id, status, version FROM Rooms 
    WHERE room_id = 'XYZ-101' AND availability_date = '2025-01-01';
    
2.  **Process Booking Logic:** The service performs its business logic, assuming the room is available.
3.  **Attempt Update:** When trying to update the room status, the service includes the `version` number it initially read in the `WHERE` clause.
    sql
    UPDATE Rooms SET 
        status = 'booked', 
        booked_by_user_id = 'user123', 
        booking_time = NOW(), 
        version = version + 1 
    WHERE room_id = 'XYZ-101' AND availability_date = '2025-01-01' 
    AND status = 'available' AND version = 1; -- Crucial check!
    
4.  **Check Update Result:**
    *   If the `UPDATE` query affects 1 row, it means no other transaction modified the room since it was read. The booking is successful.
    *   If the `UPDATE` query affects 0 rows, it means another transaction already booked the room (changing `status` or `version`). The current booking fails, and the user is informed. The application might retry the booking process if appropriate (e.g., suggesting another room).

#### Distributed Locks

In a microservices architecture, a single database might not be the only shared resource. Services running on different machines might need to coordinate access to a shared resource or a critical section of code. **Distributed locks** (using services like Redis with Redlock, Apache ZooKeeper, or etcd) provide a way for these independent services to acquire and release locks across a distributed system.

*   A service requests a lock for `room:XYZ-101`.
*   If granted, it proceeds with its booking logic (which might still involve a database transaction).
*   It releases the lock upon completion.

> **Warning:** Distributed locks add significant complexity. Proper handling of lock expiry, re-entrancy, and what happens if a service holding a lock crashes is critical to avoid deadlocks or inconsistent states.

## 3. Comparison / Trade-offs

Choosing between pessimistic and optimistic locking often depends on the expected contention levels and performance requirements.

| Feature               | Pessimistic Locking                                     | Optimistic Locking                                     |
| :-------------------- | :------------------------------------------------------ | :----------------------------------------------------- |
| **Mechanism**         | Explicitly locks resources at read time, blocking others | Checks for conflicts at write time using version/timestamp |
| **Concurrency**       | Lower. Blocks other transactions from modifying locked resources. | Higher. Allows more concurrent reads/writes initially, only failing on conflict. |
| **Conflict Handling** | Prevents conflicts by serialization.                    | Detects conflicts after they occur, requiring retry or rollback. |
| **Performance**       | Can degrade under high contention due to lock waiting/deadlocks. | Generally better under low contention. Can degrade under very high contention (frequent retries). |
| **Deadlocks**         | Possible. Requires careful transaction design, detection, and resolution. | Not possible (no explicit long-held locks).            |
| **Implementation**    | Simpler in transactional databases (`FOR UPDATE`).      | Requires application-level logic for version checks and retry mechanisms. |
| **User Experience**   | Users might experience longer waits if contention is high. | Users might get "room no longer available" errors more frequently if contention is high, potentially requiring retries. |
| **Use Case**          | High data integrity critical, low to moderate contention, short transactions. | High concurrency desired, conflicts are rare/acceptable to retry, longer transactions. |

For a hotel booking system, especially at the final booking step, **pessimistic locking** within a database transaction is often preferred for its strong consistency guarantees. It reduces the chance of showing a "room not available" error *after* a user has gone through most of the booking flow, providing a more definitive "yes" or "no" early on in the critical section. However, availability checks during the browsing phase might use more optimistic approaches or caching.

## 4. Real-World Use Case

This concurrency control problem is ubiquitous in any system where a limited resource can be claimed by multiple users simultaneously.

**Online Travel Agencies (OTAs)** like **Booking.com**, **Expedia**, and **Airbnb** are prime examples. These platforms handle millions of searches, availability checks, and booking attempts every day.

**Why are these mechanisms crucial for them?**

*   **Customer Trust:** Double booking a room is a terrible customer experience. It leads to frustration, potential cancellations, and a loss of trust in the platform. These systems must guarantee that if a user receives a confirmation, the room is unequivocally theirs.
*   **Operational Efficiency:** For hotels, managing double bookings is a logistical nightmare, potentially requiring upgrades, relocations, or even finding alternative accommodation for guests. Robust concurrency prevents these costly operational issues.
*   **Inventory Management:** OTAs often integrate with various Property Management Systems (PMS) of hotels. Accurately reflecting real-time availability and reducing inventory only once is fundamental to their business model.

In practice, large-scale OTAs often employ a layered approach:

1.  **Caching and eventual consistency** for initial room searches and display (e.g., showing a room *might* be available).
2.  **Optimistic locking** or `soft holds` for rooms when a user adds them to their cart or proceeds to payment (reserving it for a short period, subject to final confirmation).
3.  **Pessimistic locking** (database transactions) or **distributed locks** for the final, critical step of confirming and committing the booking, ensuring absolute atomicity and consistency.

By carefully selecting and combining these concurrency control strategies, these platforms maintain high availability, data integrity, and a reliable user experience, even under immense load.