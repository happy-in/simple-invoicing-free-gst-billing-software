import csv
import io

from src.models.product_bulk_update import ProductBulkUpdate


BASE = "/api/products/bulk-update"


def create_product(client, sku="BULK-1", name="Bulk test product"):
    response = client.post("/api/products/", json={
        "sku": sku, "name": name, "price": 100, "purchase_price": 70,
        "initial_quantity": 10, "gst_rate": 18, "hsn_sac": "01012100",
    })
    assert response.status_code == 200, response.text
    return response.json()["id"]


def preview(client, lines):
    response = client.post(f"{BASE}/preview", files={"file": ("changes.csv", lines, "text/csv")})
    assert response.status_code == 200, response.text
    return response.json()


def test_preview_zero_blank_inclusive_hsn_and_idempotent_save(client, db_session):
    product_id = create_product(client)
    exported = client.get(f"{BASE}/export")
    assert exported.status_code == 200
    rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert rows[0]["Product ID"] == str(product_id)
    assert rows[0]["HSN/SAC"] == "HSN:01012100"
    assert rows[0]["Replacement Stock"] == ""

    data = preview(client,
        "Product ID,Product Name,Purchase Price,Purchase Price GST,Selling Price,"
        "Selling Price GST,HSN/SAC,Replacement Stock\n"
        f"{product_id},Wrong name,0,Exclusive,236,Inclusive,HSN:01012910,\n")
    assert data["errors"] == []
    assert data["changes"][0]["fields"] == {
        "purchase_price": {"old": "70.00", "new": "0.00"},
        "price": {"old": "100.00", "new": "200.00"},
        "hsn_sac": {"old": "01012100", "new": "01012910"},
    }

    movement = client.post("/api/inventory/adjust", json={"product_id": product_id, "quantity": 5})
    assert movement.status_code == 200, movement.text
    for _ in range(2):
        response = client.post(f"{BASE}/confirm", json={"token": data["token"]})
        assert response.status_code == 200, response.text
        assert response.json() == {"updated": 1}
    product = client.get("/api/products/with-inventory").json()["items"][0]
    assert (product["purchase_price"], product["selling_price"], product["hsn_sac"]) == (0, 200, "01012910")
    assert product["current_stock"] == 15
    assert db_session.query(ProductBulkUpdate).count() == 1


def test_stock_is_separate_and_stale_preview_cannot_update_any_product(client):
    first = create_product(client)
    second = create_product(client, "BULK-2", "Second")
    content = (
        "Product ID,Selling Price,Selling Price GST,Replacement Stock\n"
        f"{first},200,Exclusive,0\n{second},300,Exclusive,\n"
    )
    data = preview(client, content)
    assert data["errors"] == []
    confirmation = {"token": data["token"]}
    assert client.post(f"{BASE}/confirm", json=confirmation).status_code == 400
    assert client.post("/api/inventory/adjust", json={"product_id": first, "quantity": 1}).status_code == 200
    confirmation["confirm_stock"] = True
    assert client.post(f"{BASE}/confirm", json=confirmation).status_code == 409
    assert client.get(f"/api/products/{second}").json()["price"] == 100

    confirmation["token"] = preview(client, content)["token"]
    assert client.post(f"{BASE}/confirm", json=confirmation).status_code == 200
    products = {product["id"]: product for product in client.get("/api/products/with-inventory").json()["items"]}
    assert products[first]["current_stock"] == 0
    assert products[second]["current_stock"] == 10


def test_rejects_unknown_ambiguous_duplicate_and_invalid_rows(client):
    first = create_product(client)
    second = create_product(client, "BULK-2", "Same name")
    create_product(client, "BULK-3", "Same name")
    data = preview(client,
        "Product ID,Product Name,Purchase Price,Purchase Price GST\n"
        "999999,Bulk test product,1,Exclusive\n"
        ",Same name,1,Exclusive\n"
        ",Bulk test product,1,Exclusive\n"
        f"{first},,1,Exclusive\n{second},,-1,Exclusive\n")
    assert data["token"] is None
    assert [error["row"] for error in data["errors"]] == [2, 3, 5, 6]
    assert data["changes"][0]["id"] == first
