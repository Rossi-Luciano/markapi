# Third-party imports
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

# Local application imports
from config.menu import get_menu_order
from reference.data_utils import get_reference
from reference.models import Reference


class ReferenceCreateView(CreateView):
    def form_valid(self, form):
        # Obtener el contenido de mixed_citation del formulario
        mixed_citation_text = form.cleaned_data["mixed_citation"].strip()
        lineas = mixed_citation_text.split("\n")  # Dividir por saltos de línea

        # Crear un nuevo objeto Reference por cada línea válida
        for linea in lineas:
            linea = linea.strip()  # Eliminar espacios adicionales en cada línea
            if linea:  # Evitar procesar líneas vacías
                new_reference = Reference.objects.create(
                    mixed_citation=linea,
                    estatus=1,  # Estatus predeterminado
                    creator=self.request.user,  # Usuario asociado
                )
                get_reference.delay(new_reference.id)
                print(f"Creado Reference: {new_reference.mixed_citation}")

        # Redirigir después de la creación de los objetos
        return HttpResponseRedirect(self.get_success_url())


class ReferenceModelViewSet(SnippetViewSet):
    model = Reference
    add_view_class = ReferenceCreateView
    menu_name = "reference"
    menu_label = _("Referências")
    menu_icon = "openquote"
    menu_order = get_menu_order("reference")
    exclude_from_explorer = False
    list_per_page = 20
    add_to_admin_menu = True


register_snippet(ReferenceModelViewSet)
