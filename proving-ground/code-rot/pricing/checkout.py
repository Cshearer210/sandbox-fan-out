from pricing import discount
from promo import discount as d2
def total(p): return discount.apply_discount(p, 10)
