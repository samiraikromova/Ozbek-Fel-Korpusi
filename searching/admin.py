from django.contrib import admin
from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'style', 'genre', 'pub_year')
    list_filter = ('style', 'genre')
    search_fields = ('title', 'author')