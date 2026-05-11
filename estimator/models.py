from django.db import models
from django.contrib.auth.models import User


class TailorProfile(models.Model):
    """Extended profile for each tailor user."""
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    institution = models.CharField(max_length=200, default='University of Zululand')
    bio         = models.TextField(blank=True)
    avatar_initials = models.CharField(max_length=4, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.avatar_initials and self.user:
            first = self.user.first_name[:1].upper() if self.user.first_name else ''
            last  = self.user.last_name[:1].upper()  if self.user.last_name  else ''
            self.avatar_initials = (first + last) or self.user.username[:2].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile({self.user.username})"


class EstimateHistory(models.Model):
    """Stores every prediction made by a tailor."""
    GARMENT_CHOICES = [
        ('Blouse', 'Blouse'), ('Coat', 'Coat'), ('Dress', 'Dress'),
        ('Hoodie', 'Hoodie'), ('Jacket', 'Jacket'), ('Jersey', 'Jersey'),
        ('Shirt', 'Shirt'), ('Shorts', 'Shorts'), ('Skirt', 'Skirt'),
        ('Suit', 'Suit'), ('Tracksuit', 'Tracksuit'), ('Trousers', 'Trousers'),
    ]
    FABRIC_CHOICES = [
        ('Cotton', 'Cotton'), ('Denim', 'Denim'), ('Leather', 'Leather'),
        ('Linen', 'Linen'), ('Nylon', 'Nylon'), ('Polyester', 'Polyester'),
        ('Silk', 'Silk'), ('Wool', 'Wool'),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='estimates')
    garment        = models.CharField(max_length=50, choices=GARMENT_CHOICES)
    fabric_type    = models.CharField(max_length=50, choices=FABRIC_CHOICES)
    fabric_m       = models.FloatField()
    price_per_m    = models.FloatField()
    material_cost  = models.FloatField()
    labour_cost    = models.FloatField(default=0)
    overhead_cost  = models.FloatField(default=0)
    total_cost     = models.FloatField()
    label          = models.CharField(max_length=200, blank=True)  # auto-generated display label
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = f"{self.fabric_type} {self.garment} – R{self.total_cost:,.2f}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} | {self.label}"
