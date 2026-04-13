from flask import current_app

from ..services import TbBuy


def enrich_products_with_sales(products):
    if not products:
        return products

    product_ids = []
    for product in products:
        try:
            product_id = int(product.get('id'))
        except (TypeError, ValueError, AttributeError):
            continue
        if product_id not in product_ids:
            product_ids.append(product_id)

    if not product_ids:
        return products

    resp = TbBuy(current_app).get_json('/order_products/sales', params={
        'product_ids': ','.join([str(v) for v in product_ids]),
        'limit': 0,
    }, check_code=False)
    sales_rows = resp.get('data', {}).get('product_sales', [])
    sales_map = {
        int(row['product_id']): int(row.get('sales') or 0)
        for row in sales_rows
        if row.get('product_id') is not None
    }

    for product in products:
        try:
            product_id = int(product.get('id'))
        except (TypeError, ValueError, AttributeError):
            product['sales'] = 0
            continue
        product['sales'] = sales_map.get(product_id, 0)

    return products
