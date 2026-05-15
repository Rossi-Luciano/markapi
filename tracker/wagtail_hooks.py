from django.utils.translation import gettext_lazy as _
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register

from config.menu import get_menu_order

from .models import GeneralEvent, XMLDocumentEvent


class XMLDocumentEventModelAdmin(ModelAdmin):
    model = XMLDocumentEvent
    inspect_view_enabled = True
    menu_label = _("Eventos de documento XML")
    menu_icon = "history"
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 10

    list_display = (
        "xml_document",
        "error_type",
        "data",
        "message",
        "created",
    )
    list_filter = ("error_type",)
    search_fields = (
        "message",
        "data",
    )
    inspect_view_fields = (
        "xml_document",
        "error_type",
        "data",
        "message",
        "created",
    )


class GeneralEventModelAdmin(ModelAdmin):
    model = GeneralEvent
    inspect_view_enabled = True
    menu_label = _("Eventos gerais")
    menu_icon = "history"
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 10

    list_display = (
        "item",
        "action",
        "exception_type",
        "exception_msg",
        "created",
    )
    list_filter = (
        "action",
        "exception_type",
    )
    search_fields = (
        "exception_msg",
        "detail",
        "action",
        "item",
    )
    inspect_view_fields = (
        "action",
        "item",
        "exception_type",
        "exception_msg",
        "traceback",
        "detail",
        "created",
    )


class EventModelAdminGroup(ModelAdminGroup):
    menu_name = "tracker"
    menu_icon = "history"
    menu_label = _("Rastreio de eventos")
    menu_order = get_menu_order("tracker")
    items = (GeneralEventModelAdmin, XMLDocumentEventModelAdmin)


modeladmin_register(EventModelAdminGroup)
