"""Record confirmed catalogue updates and their idempotency keys."""

from src.models.product_bulk_update import ProductBulkUpdate


def up(conn):
    ProductBulkUpdate.__table__.create(bind=conn, checkfirst=True)
