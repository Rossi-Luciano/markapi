import os

from django.db.models.signals import pre_save
from wagtail.images import get_image_model


def ensure_image_title(sender, instance, **kwargs):
    if (instance.title or "").strip():
        return
    if not instance.file:
        return
    basename = os.path.basename(instance.file.name)
    instance.title = os.path.splitext(basename)[0]


pre_save.connect(ensure_image_title, sender=get_image_model())
