WAGTAIL_MENU_APPS_ORDER = [
    "sps_package_validation",
    "markup_doc",
    "scielo",
    "tracker",
    "model_ai",
    "django_celery_beat",
]


def get_menu_order(app_name):
    try:
        return WAGTAIL_MENU_APPS_ORDER.index(app_name) + 1
    except ValueError:
        return 9000
