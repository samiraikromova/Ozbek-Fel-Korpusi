# searching/models.py
import os, re
from django.db import models
from django.conf import settings

class Article(models.Model):
    STYLE_CHOICES = [
        ('badiiy',       'Badiiy uslub'),
        ('ilmiy',        'Ilmiy uslub'),
        ('publitsistik', 'Publitsistik uslub'),
        ('rasmiy',       'Rasmiy uslub'),
    ]
    GENRE_CHOICES = [
        ('nasriy', 'Nasriy'),
        ('sheriy', 'She’riy'),
        ('ilmiy', 'Ilmiy'),
        ('publitsistik', 'Publitsistik'),
        ('rasmiy', 'Rasmiy'),
    ]

    author     = models.CharField(max_length=200, default='',  blank=True )
    title      = models.CharField(max_length=200)
    style      = models.CharField(max_length=20, choices=STYLE_CHOICES, default='badiiy', blank=True)
    genre      = models.CharField(max_length=20, choices=GENRE_CHOICES, null=True, blank=True)
    pub_year   = models.PositiveSmallIntegerField(null=True, blank=True)
    file       = models.FileField(upload_to='articles/')
    word_count = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """On every save, recalculate word_count from the file."""
        super().save(*args, **kwargs)
        path = os.path.join(settings.MEDIA_ROOT, self.file.name)
        if os.path.exists(path):
            text = open(path, 'r', encoding='utf-8').read()
            wc = len(re.findall(r'\w+', text, re.UNICODE))
            # update without recursion
            Article.objects.filter(pk=self.pk).update(word_count=wc)
            self.word_count = wc

    def __str__(self):
        return f"{self.author} – {self.title}"
