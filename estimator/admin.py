from django.contrib import admin
from .models import TailorProfile, EstimateHistory


@admin.register(TailorProfile)
class TailorProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'institution', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'institution']


@admin.register(EstimateHistory)
class EstimateHistoryAdmin(admin.ModelAdmin):
    list_display   = ['user', 'garment', 'fabric_type', 'fabric_m',
                      'material_cost', 'total_cost', 'created_at']
    list_filter    = ['garment', 'fabric_type', 'created_at']
    search_fields  = ['user__email', 'garment', 'fabric_type']
    readonly_fields = ['created_at']
    ordering       = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
