from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, help_text="Search query string.")
    type = serializers.ChoiceField(
        choices=[
            "all",
            "products",
            "categories",
            "invoices",
            "employees",
            "restaurants",
            "customers",
            "suppliers",
        ],
        default="all",
        help_text="Filter search results by type.",
    )
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)
    offset = serializers.IntegerField(default=0, min_value=0)
