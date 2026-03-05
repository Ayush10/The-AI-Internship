"""Return eligibility and initiation tools — queries Supabase REST API."""

import os
from datetime import datetime, timezone, timedelta

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

RETURN_WINDOW_DAYS = 30


def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _get_order(order_id: str) -> dict | None:
    """Fetch an order from Supabase REST API."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None
    url = f"{SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}&select=*"
    resp = httpx.get(url, headers=_supabase_headers(), timeout=10)
    if resp.status_code == 200:
        rows = resp.json()
        return rows[0] if rows else None
    return None


def check_return_eligibility(order_id: str) -> dict:
    """Check if an order is eligible for return.

    Queries the Supabase database to check the order status and delivery date.
    An order is eligible for return if it was delivered within the last 30 days
    and has not already been returned or refunded.

    Args:
        order_id: The order ID to check eligibility for.

    Returns:
        A dict with:
        - eligible: Whether the order can be returned (bool)
        - reason: Explanation of the eligibility decision (str)
        - return_by_date: Deadline for return if eligible (str or null)
        - order_details: Summary of the order (dict)
    """
    order = _get_order(order_id)

    if not order:
        return {
            "eligible": False,
            "reason": f"Order #{order_id} not found in our system.",
            "return_by_date": None,
            "order_details": None,
        }

    status = order.get("status", "")
    product = order.get("product", "Unknown")
    amount = order.get("amount", 0)
    delivery_date_str = order.get("delivery_date")

    # Not delivered yet
    if status in ("pending", "shipped"):
        return {
            "eligible": False,
            "reason": f"Order #{order_id} ({product}) has not been delivered yet (status: {status}). Returns can only be initiated after delivery.",
            "return_by_date": None,
            "order_details": {"product": product, "amount": float(amount), "status": status},
        }

    # Already returned or refunded
    if status in ("returned", "refunded"):
        return {
            "eligible": False,
            "reason": f"Order #{order_id} ({product}) has already been {status}. No further return action is possible.",
            "return_by_date": None,
            "order_details": {"product": product, "amount": float(amount), "status": status},
        }

    # Check return window
    if delivery_date_str:
        delivery_date = datetime.fromisoformat(delivery_date_str.replace("Z", "+00:00"))
        return_deadline = delivery_date + timedelta(days=RETURN_WINDOW_DAYS)
        now = datetime.now(timezone.utc)

        if now > return_deadline:
            return {
                "eligible": False,
                "reason": f"Order #{order_id} ({product}) was delivered on {delivery_date.strftime('%b %d, %Y')}. The {RETURN_WINDOW_DAYS}-day return window expired on {return_deadline.strftime('%b %d, %Y')}.",
                "return_by_date": None,
                "order_details": {"product": product, "amount": float(amount), "status": status, "delivery_date": delivery_date_str},
            }

        return {
            "eligible": True,
            "reason": f"Order #{order_id} ({product}, ${amount}) is eligible for return. Delivered on {delivery_date.strftime('%b %d, %Y')}, within the {RETURN_WINDOW_DAYS}-day return window.",
            "return_by_date": return_deadline.strftime("%Y-%m-%d"),
            "order_details": {"product": product, "amount": float(amount), "status": status, "delivery_date": delivery_date_str},
        }

    return {
        "eligible": False,
        "reason": f"Order #{order_id} ({product}) has no delivery date recorded. Please contact support for assistance.",
        "return_by_date": None,
        "order_details": {"product": product, "amount": float(amount), "status": status},
    }


def initiate_return(order_id: str, reason: str) -> dict:
    """Initiate a return for an eligible order.

    First validates return eligibility, then updates the order status to 'returned'
    in Supabase and generates an RMA (Return Merchandise Authorization) number.

    Args:
        order_id: The order ID to initiate a return for.
        reason: The customer's reason for returning the product.

    Returns:
        A dict with:
        - rma_id: The return authorization number (str)
        - status: The return status (str)
        - instructions: Steps the customer should follow (str)
        - order_details: Summary of the returned order (dict)
    """
    # Check eligibility first
    eligibility = check_return_eligibility(order_id)
    if not eligibility["eligible"]:
        return {
            "rma_id": None,
            "status": "rejected",
            "instructions": eligibility["reason"],
            "order_details": eligibility.get("order_details"),
        }

    # Generate RMA number
    timestamp = int(datetime.now(timezone.utc).timestamp())
    rma_id = f"RMA-{order_id}-{timestamp}"

    # Update order status in Supabase
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        url = f"{SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}"
        httpx.patch(
            url,
            headers=_supabase_headers(),
            json={"status": "returned", "return_eligible": False},
            timeout=10,
        )

    return {
        "rma_id": rma_id,
        "status": "initiated",
        "instructions": (
            f"Return authorized. Your RMA number is {rma_id}.\n\n"
            "Please follow these steps:\n"
            "1. Pack the item securely in its original packaging if possible.\n"
            "2. Include this RMA number on the outside of the package.\n"
            "3. Ship to our returns center within 7 business days.\n"
            "4. A prepaid shipping label has been sent to your email.\n"
            "5. Refund will be processed within 3-5 business days after we receive the item."
        ),
        "order_details": eligibility.get("order_details"),
    }
