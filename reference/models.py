from django.db import models
from core.models import (
    CommonControlField,
)
from wagtail.models import Orderable
from wagtail.admin.panels import FieldPanel, InlinePanel
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from core.forms import CoreAdminModelForm


class Reference(CommonControlField, ClusterableModel):
    mixed_citation = models.TextField(_("Mixed Citation"), null=False, blank=True)

    estatus = models.IntegerField(default=0) 

    panels = [
        FieldPanel('mixed_citation'),
        InlinePanel('element_citation', label=_("Cited Elements"))
    ]

    base_form_class = CoreAdminModelForm

    def __str__(self):
        return self.mixed_citation

    class Meta:
        verbose_name = _("Referência")
        verbose_name_plural = _("Referências")


class ElementCitation(Orderable):
    reference = ParentalKey(
        Reference, on_delete=models.SET_NULL, related_name="element_citation", null=True
    )
    marked = models.JSONField(_("Marked"), default=dict, blank=True)
    marked_xml = models.TextField(_("Marked XML"), blank=True)

    score = models.IntegerField(
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(1),  # Mínimo 1
            MaxValueValidator(10)  # Máximo 10
        ],
        help_text=_("Rating from 1 to 10")
    )

    panels = [
            FieldPanel("marked"),
            FieldPanel("marked_xml"),
            FieldPanel("score"),
            ]
