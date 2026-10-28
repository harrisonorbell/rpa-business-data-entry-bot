import csv
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

# --------------------------------------------------
# Project paths
# --------------------------------------------------

project_path = Path(__file__).resolve().parent.parent

website_url = (project_path / "website" / "index.html").as_uri()
csv_path = project_path / "data" / "orders.csv"
results_path = project_path / "data" / "processing_results.csv"
processed_path = project_path / "data" / "processed_orders.json"
screenshots_path = project_path / "screenshots"

# Store browser data outside OneDrive
profile_path = Path.home() / ".coastal-orders-rpa-profile"

screenshots_path.mkdir(exist_ok=True)


# --------------------------------------------------
# Load customer orders
# --------------------------------------------------

with open(csv_path, newline="", encoding="utf-8") as file:
    orders = list(csv.DictReader(file))

print(f"Loaded {len(orders)} customer orders.")


# --------------------------------------------------
# Load previously processed order references
# --------------------------------------------------

if processed_path.exists():
    with open(processed_path, "r", encoding="utf-8") as file:
        processed_orders = set(json.load(file))
else:
    processed_orders = set()

print(f"Previously processed orders: {len(processed_orders)}")

results = []


# --------------------------------------------------
# Start browser automation
# --------------------------------------------------

with sync_playwright() as playwright:

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_path),
        headless=False
    )

    page = context.pages[0] if context.pages else context.new_page()
    page.goto(website_url)

    # --------------------------------------------------
    # Process customer orders
    # --------------------------------------------------

    for index, order in enumerate(orders, start=1):

        order_reference = order["order_reference"].strip()

        print(
            f"\nProcessing order {index}/{len(orders)}: "
            f"{order['customer_name']} ({order_reference})"
        )

        # ----------------------------------------------
        # Check for duplicates
        # ----------------------------------------------

        if order_reference in processed_orders:

            print(f"DUPLICATE: {order_reference} already processed")

            results.append({
                "order_reference": order_reference,
                "customer_name": order["customer_name"],
                "status": "DUPLICATE",
                "order_id": "",
                "details": "Order previously processed"
            })

            continue

        # ----------------------------------------------
        # Validate order data
        # ----------------------------------------------

        errors = []

        if not order_reference:
            errors.append("Missing order reference")

        if not order["customer_name"].strip():
            errors.append("Missing customer name")

        if not order["customer_email"].strip() or "@" not in order["customer_email"]:
            errors.append("Invalid customer email")

        if not order["product"].strip():
            errors.append("Missing product")

        try:
            quantity = int(order["quantity"])

            if quantity < 1:
                errors.append("Quantity must be greater than zero")

        except (ValueError, TypeError):
            errors.append("Invalid quantity")

        try:
            unit_price = float(order["unit_price"])

            if unit_price < 0:
                errors.append("Unit price cannot be negative")

        except (ValueError, TypeError):
            errors.append("Invalid unit price")

        if not order["delivery_address"].strip():
            errors.append("Missing delivery address")

        if errors:

            error_message = ", ".join(errors)

            print(f"SKIPPED: {error_message}")

            results.append({
                "order_reference": order_reference,
                "customer_name": order["customer_name"],
                "status": "SKIPPED",
                "order_id": "",
                "details": error_message
            })

            continue

        # ----------------------------------------------
        # Enter order into website
        # ----------------------------------------------

        try:

            # Enter customer name
            page.locator("#customerName").fill(
                order["customer_name"],
                timeout=3000
            )

            page.locator("#customerEmail").fill(order["customer_email"])
            page.locator("#product").fill(order["product"])
            page.locator("#quantity").fill(order["quantity"])
            page.locator("#unitPrice").fill(order["unit_price"])
            page.locator("#deliveryAddress").fill(order["delivery_address"])

            # Submit order
            page.locator("#submitOrder").click()

            # ------------------------------------------
            # Verify website confirmation
            # ------------------------------------------

            confirmation = page.locator("#message").inner_text()

            print(f"Result: {confirmation}")

            if "saved successfully!" in confirmation:

                order_id = (
                    confirmation.split(" saved successfully!")[0]
                    .replace("Order ", "")
                )

                results.append({
                    "order_reference": order_reference,
                    "customer_name": order["customer_name"],
                    "status": "SUCCESS",
                    "order_id": order_id,
                    "details": confirmation
                })

                # Remember successful order
                processed_orders.add(order_reference)

                with open(processed_path, "w", encoding="utf-8") as file:
                    json.dump(sorted(processed_orders), file, indent=4)

            else:

                print(f"FAILED: {confirmation}")

                results.append({
                    "order_reference": order_reference,
                    "customer_name": order["customer_name"],
                    "status": "FAILED",
                    "order_id": "",
                    "details": confirmation
                })

        # ----------------------------------------------
        # Handle unexpected browser errors
        # ----------------------------------------------

        except PlaywrightError as error:

            error_message = str(error).splitlines()[0]

            print(f"FAILED: {error_message}")

            results.append({
                "order_reference": order_reference,
                "customer_name": order["customer_name"],
                "status": "FAILED",
                "order_id": "",
                "details": error_message
            })

            # Capture evidence of the failure
            try:
                screenshot_file = screenshots_path / f"{order_reference}_failure.png"

                page.screenshot(path=str(screenshot_file))

                print(f"Screenshot saved: {screenshot_file.name}")

            except PlaywrightError:
                print("Could not capture failure screenshot.")

        # Brief delay to observe automation
        page.wait_for_timeout(500)

    print("\nAll orders processed.")

    page.wait_for_timeout(10000)

    context.close()


# --------------------------------------------------
# Export processing results
# --------------------------------------------------

with open(results_path, "w", newline="", encoding="utf-8") as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "order_reference",
            "customer_name",
            "status",
            "order_id",
            "details"
        ]
    )

    writer.writeheader()
    writer.writerows(results)


# --------------------------------------------------
# Print execution summary
# --------------------------------------------------

success_count = sum(
    result["status"] == "SUCCESS" for result in results
)

skipped_count = sum(
    result["status"] == "SKIPPED" for result in results
)

failed_count = sum(
    result["status"] == "FAILED" for result in results
)

duplicate_count = sum(
    result["status"] == "DUPLICATE" for result in results
)

print(f"\nProcessing report saved to: {results_path.name}")

print(
    f"Summary: {success_count} successful, "
    f"{skipped_count} skipped, "
    f"{failed_count} failed, "
    f"{duplicate_count} duplicates."
)