const orderForm = document.getElementById("orderForm");
const message = document.getElementById("message");
const ordersTable = document.getElementById("ordersTable");

let orders = JSON.parse(localStorage.getItem("coastalOrders") || "[]");

function displayOrders() {
    ordersTable.innerHTML = "";

    if (orders.length === 0) {
        ordersTable.innerHTML = `
            <tr>
                <td colspan="6" class="empty">
                    No orders have been submitted yet.
                </td>
            </tr>
        `;
        return;
    }

    orders.forEach(order => {
        const row = document.createElement("tr");

        const values = [
            order.id,
            order.customerName,
            order.product,
            order.quantity,
            `$${order.total.toFixed(2)}`,
            order.status
        ];

        values.forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        ordersTable.appendChild(row);
    });
}

orderForm.addEventListener("submit", function(event) {
    event.preventDefault();

    const customerName = document.getElementById("customerName").value.trim();
    const customerEmail = document.getElementById("customerEmail").value.trim();
    const product = document.getElementById("product").value.trim();
    const quantity = Number(document.getElementById("quantity").value);
    const unitPrice = Number(document.getElementById("unitPrice").value);
    const deliveryAddress = document.getElementById("deliveryAddress").value.trim();

    if (
        !customerName ||
        !customerEmail ||
        !product ||
        !deliveryAddress ||
        !Number.isInteger(quantity) ||
        quantity < 1 ||
        !Number.isFinite(unitPrice) ||
        unitPrice < 0
    ) {
        message.textContent = "Please enter valid order details.";
        message.className = "message error";
        return;
    }

    const order = {
        id: `ORD-${crypto.randomUUID()}`,
        customerName,
        customerEmail,
        product,
        quantity,
        unitPrice,
        deliveryAddress,
        total: quantity * unitPrice,
        status: "Saved",
        createdAt: new Date().toISOString()
    };

    orders.push(order);
    localStorage.setItem("coastalOrders", JSON.stringify(orders));

    message.textContent = `Order ${order.id} saved successfully!`;
    message.className = "message success";

    orderForm.reset();
    displayOrders();
});

displayOrders();