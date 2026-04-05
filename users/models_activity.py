from django.db import models
from django.conf import settings
from products.models import Product

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ("view", "Viewed Product"),
        ("cart_add", "Added to Cart"),
        ("wishlist_add", "Added to Wishlist"),
        ("order", "Placed Order"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    extra = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} {self.get_activity_type_display()} {self.product or ''} at {self.timestamp}"
