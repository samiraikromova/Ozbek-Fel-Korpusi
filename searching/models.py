from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=250, blank=True)
    author = models.CharField(max_length=250, blank=True, null=True)
    file = models.FileField(upload_to='articles/')
    style = models.CharField(max_length=250, blank=True, null=True, default='badiy')

    def __str__(self):
        return f"{self.author} - {self.title}"
