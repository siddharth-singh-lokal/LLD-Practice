"""
Product search + sponsored ranking — Strong Hire reference (60-90 min MC round).

HOW TO DERIVE STRUCTURE IN THE ROOM (first 5-8 min, before typing):
  1. Ops: add product, search by name, filter, sponsored on top, sort the rest
  2. Nouns: Product (data), ProductCatalog (storage), ProductSearchService (flow)
  3. What varies: sort policy -> SortStrategy; filter rules -> ProductFilter
  4. What stays in service: "sponsored block before non-sponsored" is a business rule
  5. Ship happy path first; extract RatingSortStrategy when they ask "sort by rating"

HIRE vs STRONG HIRE on THIS problem:
  Hire     = search() runs + one driver case
  Strong   = edge-case driver + second SortStrategy without editing search()
"""

from abc import ABC, abstractmethod
from typing import Optional


class Product:
    def __init__(
        self,
        id: int,
        name: str,
        brand: str,
        category: str,
        price: float,
        sponsored: bool = False,
    ):
        self.id = id
        self.name = name
        self.brand = brand
        self.category = category
        self.price = price
        self.sponsored = sponsored


class ProductCatalog:
    """SRP: storage only. Search logic does not live here."""

    def __init__(self):
        self._products: list[Product] = []

    def add_product(self, product: Product) -> None:
        self._products.append(product)

    def get_all(self) -> list[Product]:
        # SH polish: return a copy so callers cannot mutate internal catalog.
        return list(self._products)


class ProductFilter(ABC):
    """
    Filter rule varies (brand, price, category).
    SH rule: config in __init__, matches() takes only Product.
    Then search() can loop: all(f.matches(p) for f in filters)
    """

    @abstractmethod
    def matches(self, product: Product) -> bool:
        pass


class BrandFilter(ProductFilter):
    def __init__(self, brand: str):
        self.brand = brand

    def matches(self, product: Product) -> bool:
        return product.brand == self.brand


class MaxPriceFilter(ProductFilter):
    def __init__(self, max_price: float):
        self.max_price = max_price

    def matches(self, product: Product) -> bool:
        return product.price <= self.max_price


class SearchQueryFilter(ProductFilter):
    def __init__(self, query: str):
        self.query = query.lower()

    def matches(self, product: Product) -> bool:
        return self.query in product.name.lower()


class SortStrategy(ABC):
    """
    Strategy: sort policy varies (price today, rating tomorrow).
    OCP: add RatingSortStrategy without touching ProductSearchService.search().
    """

    @abstractmethod
    def sort(self, products: list[Product]) -> list[Product]:
        pass


class PriceSortStrategy(SortStrategy):
    def __init__(self, descending: bool = False):
        # Default ascending (cheapest first) unless prompt says otherwise.
        self.descending = descending

    def sort(self, products: list[Product]) -> list[Product]:
        return sorted(
            products,
            key=lambda product: product.price,
            reverse=self.descending,
        )


class RatingSortStrategy(SortStrategy):
    """
    SH extension class: swap this in at minute ~35 when interviewer says
    "sort by rating instead of price". search() stays unchanged.
    """

    def __init__(
        self,
        product_ratings: dict[int, float],
        descending: bool = True,
    ):
        self.product_ratings = product_ratings
        self.descending = descending

    def sort(self, products: list[Product]) -> list[Product]:
        return sorted(
            products,
            key=lambda product: self.product_ratings.get(product.id, 0.0),
            reverse=self.descending,
        )


class ProductSearchService:
    """
    Orchestrates the flow. Has-a catalog + sort strategy (composition).
    Does NOT store filters permanently — passed per search call.
    """

    def __init__(
        self,
        catalog: ProductCatalog,
        sort_strategy: SortStrategy,
    ):
        self.catalog = catalog
        self.sort_strategy = sort_strategy

    def search(
        self,
        query: str,
        filters: Optional[list[ProductFilter]] = None,
    ) -> list[Product]:
        filters = filters or []

        products = self.catalog.get_all()

        # Query is always applied; extra filters are optional.
        all_filters = [SearchQueryFilter(query)] + filters

        products = [
            product
            for product in products
            if all(filter.matches(product) for filter in all_filters)
        ]

        sponsored = [product for product in products if product.sponsored]
        non_sponsored = [product for product in products if not product.sponsored]

        # SH: define order WITHIN each block, not just "sponsored first".
        # Say out loud: sponsored block on top, same sort policy inside each block.
        sponsored = self.sort_strategy.sort(sponsored)
        non_sponsored = self.sort_strategy.sort(non_sponsored)

        return sponsored + non_sponsored


if __name__ == "__main__":
    catalog = ProductCatalog()
    ratings = {1: 4.8, 2: 4.5, 3: 4.9, 4: 4.2}

    price_service = ProductSearchService(
        catalog,
        PriceSortStrategy(descending=False),
    )

    catalog.add_product(
        Product(1, "iphone 15 phone", "Apple", "phone", 79999, sponsored=True)
    )
    catalog.add_product(Product(2, "iphone 14 phone", "Apple", "phone", 59999))
    catalog.add_product(
        Product(3, "galaxy s24 phone", "Samsung", "phone", 69999, sponsored=True)
    )
    catalog.add_product(Product(4, "pixel 8 phone", "Google", "phone", 49999))

    # --- Case 1: happy path (sponsored first + brand filter + price sort) ---
    results = price_service.search("phone", [BrandFilter("Apple")])
    names = [product.name for product in results]
    assert names == ["iphone 15 phone", "iphone 14 phone"]

    # --- Case 2: max price filter (proves MaxPriceFilter is wired) ---
    results = price_service.search("phone", [MaxPriceFilter(70000)])
    names = [product.name for product in results]
    assert names[0] == "galaxy s24 phone"  # sponsored block still on top
    assert "iphone 15" not in names  # 79999 filtered out

    # --- Case 3: no matches (boundary — SH driver always includes this) ---
    assert price_service.search("laptop", []) == []
    assert price_service.search("phone", [BrandFilter("OnePlus")]) == []

    # --- Case 4: extension — rating sort, search() unchanged (OCP = SH) ---
    rating_service = ProductSearchService(catalog, RatingSortStrategy(ratings))
    results = rating_service.search("phone", [])
    names = [product.name for product in results]
    assert names[0] == "galaxy s24 phone"  # highest-rated sponsored first
    assert names[1] == "iphone 15 phone"

    print("all checks passed")

"""
60-90 MIN ROUND TIMELINE (memorize):
  0-8 min   ops + entities on paper (4 boxes max)
  8-25 min  Product, Catalog, search() happy path (query match only)
  25-40 min filters + sponsored split + PriceSortStrategy
  40-55 min driver: happy + empty results + one extra filter
  55-70 min RatingSortStrategy when asked; explain OCP out loud
  70-90 min fix bugs interviewer points out; do NOT add pagination/cache/DB

OPENING SCRIPT:
  "In-memory catalog. search by name, optional brand/price filters,
   sponsored pinned on top, sort within each block. Strategy for sort,
   Filter objects for constraints. Out of scope: DB, pagination, fuzzy match."

FUTURE-YOU: CLASS STRUCTURE CHECKLIST
  - One class, one job (Product=data, Catalog=store, Service=flow)
  - Pattern only where it varies (sort, filters) — not on every noun
  - Config in __init__, not in matches()/search() extra params
  - Happy path first; extract ABC when 2nd implementation appears
  - Driver proves edges, not just success
  - If you cannot explain a line, it is not yours yet — reattempt blank file
"""
