def find_products(products, query):
    query = query.lower()
    hits = []
    for product in products:
        for tag in product.tags:
            if query in tag.lower():
                hits.append(product)
        if query in product.name.lower():
            hits.append(product)
    return hits
