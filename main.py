from beevo.client import BeevoClient
from beevo.product import ProductAPI
from beevo.options import OptionsAPI
from beevo.variants import VariantsAPI

client = BeevoClient(
    url="https://amarhouse.beevo.com/admin-api?languageCode=pt_PT",
    token="TOKEN",
    cookie="COOKIE"
)

product_api = ProductAPI(client)
options_api = OptionsAPI(client)
variants_api = VariantsAPI(client)

# 1. Create product
product = product_api.create_product("Lampada Teste", "lampada-teste")
product_id = product["createProduct"]["id"]

# 2. Create option group
group = options_api.create_option_group(
    code="temperatura-de-cor",
    name="Temperatura de Cor",
    options=[
        {"code": "2000k", "name": "2000K"},
        {"code": "3000k", "name": "3000K"}
    ]
)

group_id = group["createProductOptionGroup"]["id"]

# 3. Attach option group
options_api.add_option_group_to_product(product_id, group_id)

# 4. Create variant (example simplified)
variant = variants_api.create_variant(
    product_id=product_id,
    sku="LAMP-2000",
    price=10.99,
    stock=5,
    option_ids=["OPTION_ID_2000K"]
)

print(variant)