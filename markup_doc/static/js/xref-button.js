function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Verifica si el cookie empieza con el nombre que queremos
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCSRFTokenFromInput() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : null;
}

function get_cite(text){
    const path = window.location.pathname;
    const match = path.match(/edit\/(\d+)\//);  // Extrae el número entre 'edit/' y el siguiente '/'
    var pk_register = parseInt(match[1], 10);

    return fetch('/admin/extract-citation/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFTokenFromInput()
        },
        body: JSON.stringify({ 
                                text: text,
                                pk: pk_register
                            })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Cita extraída:", data);
        return data.refid;
        // Aquí podrías hacer algo con los resultados
    })
    .catch(error => {
        console.error("Error al extraer citas:", error);
    });
}

//document.addEventListener("DOMContentLoaded", function () {
function addXrefButtonToTextareas() {
    //var tab = document.querySelector('a[role="tab"][aria-selected="true"]');
    //if(tab.id !== 'tab-label-body'){
    //    return false;
    //}

    var frontTab = document.querySelector('#tab-body');

    if (frontTab) {

        // Espera a que el campo se cargue
        frontTab.querySelectorAll('textarea').forEach(function (textarea) {
            if(textarea.value.length < 50){
                return false;
            }

            // Evita insertar el botón más de una vez
            if (textarea.dataset.xrefButtonAdded === 'true') return;

            // Marca el textarea como procesado
            textarea.dataset.xrefButtonAdded = 'true';

            // Crea el botón
            const button = document.createElement('button');
            button.type = 'button';
            button.innerText = 'Add <xref>';
            button.style.margin = '5px';

            button.style.padding = "4px 8px";
            button.style.cursor = "pointer";
            button.style.marginLeft = "auto";

            button.style.backgroundColor = "#007d7e";  // fondo azul (Bootstrap-like)
            button.style.color = "white";
            button.style.fontWeight = "bold";

            button.addEventListener("mouseover", () => {
                button.style.backgroundColor = "#006465";
            });
            button.addEventListener("mouseout", () => {
                button.style.backgroundColor = "#007d7e";
            });


            // Crea el botón
            const btn2 = document.createElement('button');
            btn2.type = 'button';
            btn2.innerText = "Delete all <xref>";
            btn2.style.margin = '5px';

            btn2.style.padding = "4px 8px";
            btn2.style.cursor = "pointer";
            btn2.style.marginLeft = "auto";

            btn2.style.backgroundColor = "#007d7e";  // fondo azul (Bootstrap-like)
            btn2.style.color = "white";
            btn2.style.fontWeight = "bold";

            btn2.addEventListener("mouseover", () => {
                btn2.style.backgroundColor = "#006465";
            });
            btn2.addEventListener("mouseout", () => {
                btn2.style.backgroundColor = "#007d7e";
            });

            // Acción al hacer clic
            button.addEventListener('click', function () {
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const selectedText = textarea.value.substring(start, end);

                if (!selectedText) {
                    alert('Selecciona un texto para aplicar <xref>');
                    return;
                }

                var textClean = selectedText.replace('[style name="italic"]','').replace('[/style]','');
                //var cite = get_cite(textClean);

                get_cite(textClean).then(cite => {
                    // aquí ya tienes el valor real
                    const xrefWrapped = `<xref ref-type="bibr" rid="${cite}">${selectedText}</xref>`;
                    const newText = textarea.value.slice(0, start) + xrefWrapped + textarea.value.slice(end);
                    textarea.value = newText;
                });

            });

            btn2.addEventListener('click', function () {              
                // Reemplaza <xref ...>...</xref> por solo su contenido
                textarea.value = textarea.value.replace(/<xref\b[^>]*>(.*?)<\/xref>/gi, '$1');
            });

            // Agrega el botón justo después del textarea
            textarea.parentNode.insertBefore(button, textarea.nextSibling);

            textarea.parentNode.insertBefore(btn2, textarea.nextSibling);
        });
    }
}
//});

// Inicial: aplica en los visibles al cargar
document.addEventListener('DOMContentLoaded', function () {
    addXrefButtonToTextareas();
});


document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.w-tabs__tab').forEach(function(tabLink) {
        tabLink.addEventListener('click', function() {
            // Espera a que el contenido del tab se muestre
            setTimeout(function () {
                // ID del contenido al que apunta el tab
                const tabContentId = tabLink.getAttribute('href'); // por ejemplo: "#tab-xml"
                const tabContent = document.querySelector(tabContentId);

                if (tabContent) {
                    addXrefButtonToTextareas();
                }
            }, 100); // delay leve para permitir render
        });
    });
});
    

document.addEventListener("DOMContentLoaded", function () {
    var path = window.location.pathname;
    // Busca el campo por su ID (ajústalo si es diferente)
    if ( path.indexOf('markupxml/edit') == -1 ){
        return false;
    }
    var ids = ['collection', 'journal_title', 'short_title', 'title_nlm', 'acronym', 'issn', 'pissn', 'eissn', 'pubname']
    $.each(ids, function(i, val){
        const collectionField = document.querySelector('#id_'+val);
        if (collectionField) {
            collectionField.setAttribute('readonly', true);  // Solo lectura
            collectionField.classList.add('disabled');        // Para aplicar estilo visual
            // Agregar estilos Wagtail para apariencia "inactiva"
            collectionField.style.backgroundColor = 'var(--w-color-surface-field-inactive)';
            collectionField.style.borderColor = 'var(--w-color-border-field-inactive)';
            collectionField.style.color = 'var(--w-color-text-placeholder)';
            collectionField.style.cursor = 'not-allowed';
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const journalInput = document.querySelector("#id_journal");

    //if (!journalInput) return;

    // MutationObserver para detectar cambios en la selección del widget
    const journalWrapper = document.querySelector('[data-autocomplete-input-id="id_journal"]');

    if (!journalWrapper) return;

    const observer = new MutationObserver(() => {
        // Buscar el input hidden que contiene el valor
        const hiddenInput = journalWrapper.querySelector('input[type="hidden"][name="journal"]');
        if (!hiddenInput) return;
        
        let journalValue;

        try {
            journalValue = JSON.parse(hiddenInput.value);
        } catch (e) {
            return;
        }

        if (journalValue && journalValue.pk) {
            
            fetch('/admin/get_journal/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFTokenFromInput()
                },
                body: JSON.stringify({ 
                                        pk: journalValue.pk
                                    })
            })
            .then(response => response.json())
            .then(data => {
                console.log(data);
                $('#id_journal_title').val(data.journal_title);
                $('#id_short_title').val(data.short_title);
                $('#id_title_nlm').val(data.title_nlm);
                $('#id_acronym').val(data.acronym);
                $('#id_issn').val(data.issn);
                $('#id_pissn').val(data.pissn);
                $('#id_eissn').val(data.eissn);
                $('#id_pubname').val(data.pubname);
            })
            .catch(error => {
                console.error("Error:", error);
                $('#id_journal_title').val("");
                $('#id_short_title').val("");
                $('#id_title_nlm').val("");
                $('#id_acronym').val("");
                $('#id_issn').val("");
                $('#id_pissn').val("");
                $('#id_eissn').val("");
                $('#id_pubname').val("");
            });

        }else{
            $('#id_journal_title').val("");
            $('#id_short_title').val("");
            $('#id_title_nlm').val("");
            $('#id_acronym').val("");
            $('#id_issn').val("");
            $('#id_pissn').val("");
            $('#id_eissn').val("");
            $('#id_pubname').val("");
        }
    });

    observer.observe(journalWrapper, { childList: true, subtree: true });
});


function get_zip() {
    // Extraer el pk desde /edit/<id>/
    const path = window.location.pathname;
    const match = path.match(/edit\/(\d+)\//);
    const pk_register = match ? parseInt(match[1], 10) : null;
    if (!pk_register) {
      console.error("No se pudo obtener el ID del registro desde la URL.");
      return;
    }
  
    return fetch('/admin/download-zip/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFTokenFromInput(), // asegúrate de que esta func devuelva el token correcto
        'Accept': 'application/zip'             // opcional, para claridad
      },
      body: JSON.stringify({ pk: pk_register })
    })
    .then(async (response) => {
      if (!response.ok) {
        // Si el backend a veces devuelve JSON de error, intenta leerlo:
        let errorText = `Error ${response.status}`;
        try {
          const data = await response.json();
          if (data && data.error) errorText += `: ${data.error}`;
        } catch {
          // Si no era JSON, lee como texto
          try {
            errorText += `: ${await response.text()}`;
          } catch {}
        }
        throw new Error(errorText);
      }
  
      // Leer el ZIP como Blob
      const blob = await response.blob();
  
      // Intentar extraer filename del header Content-Disposition
      let filename = "archivo.zip";
      const cd = response.headers.get('Content-Disposition');
      if (cd) {
        // ej: attachment; filename="article_123.zip"
        const match = cd.match(/filename\*?=(?:UTF-8'')?"?([^\";]+)/i);
        if (match && match[1]) {
          filename = decodeURIComponent(match[1].replace(/\"/g, ''));
        }
      }
  
      // Crear un Object URL y disparar descarga
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename; // sugiere el nombre
      document.body.appendChild(a);
      a.click();
      // Limpieza
      URL.revokeObjectURL(url);
      a.remove();
    })
    .catch((error) => {
      console.error("Error al descargar el ZIP:", error);
      alert("No se pudo descargar el ZIP. " + error.message);
    });
  }

  function openPreviewHTMLFetch() {
    // Extraer el pk desde /edit/<id>/
    const path = window.location.pathname;
    const match = path.match(/edit\/(\d+)\//);
    const pk_register = match ? parseInt(match[1], 10) : null;
    if (!pk_register) {
    console.error("No se pudo obtener el ID del registro desde la URL.");
    return;
    }

    const w = window.open('', '_blank');
    fetch('/admin/preview-html/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFTokenFromInput(),
        'Accept': 'text/html'
      },
      body: JSON.stringify({ pk: pk_register })
    })
    .then(r => {
      if (!r.ok) throw new Error('Error ' + r.status);
      return r.text();
    })
    .then(html => {
      w.document.open();
      w.document.write(html);
      w.document.close();
    })
    .catch(err => {
      w.close();
      alert('No se pudo abrir la vista previa: ' + err.message);
    });
  }


  function openPrettyXML() {
    // Extraer el pk desde /edit/<id>/
    const path = window.location.pathname;
    const match = path.match(/edit\/(\d+)\//);
    const pk_register = match ? parseInt(match[1], 10) : null;
    if (!pk_register) {
    console.error("No se pudo obtener el ID del registro desde la URL.");
    return;
    }

    const w = window.open('', '_blank');
    fetch('/admin/pretty-xml/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFTokenFromInput(),
        'Accept': 'text/xml'
      },
      body: JSON.stringify({ pk: pk_register })
    })
    .then(r => {
      if (!r.ok) throw new Error('Error ' + r.status);
      return r.text();
    })
    .then(html => {
      w.document.open();
      w.document.write(html);
      w.document.close();
    })
    .catch(err => {
      w.close();
      alert('No se pudo abrir la vista previa: ' + err.message);
    });
  }


(function() {
  
    function createXrefButton(textarea) {
      // Evita duplicados
      if (textarea.dataset.xrefButtonAdded === "true") return;
  
      // Marca como procesado
      textarea.dataset.xrefButtonAdded = "true";
  
      // Contenedor estilo "toolbar" (opcional)
      const bar = document.createElement("div");
      bar.style.display = "flex";
      bar.style.gap = "8px";
      bar.style.alignItems = "center";
      bar.style.marginBottom = "6px";
  
      // Botón
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Download ZIP";
      btn.style.padding = "4px 8px";
      btn.style.cursor = "pointer";
      btn.style.marginLeft = "auto";

      btn.style.backgroundColor = "#007d7e";  // fondo azul (Bootstrap-like)
      btn.style.color = "white";
      btn.style.fontWeight = "bold";

      btn.addEventListener("mouseover", () => {
        btn.style.backgroundColor = "#006465";
      });
      btn.addEventListener("mouseout", () => {
        btn.style.backgroundColor = "#007d7e";
      });
  
      bar.appendChild(btn);


      // Botón 2
      const btn2 = document.createElement("button");
      btn2.type = "button";
      btn2.textContent = "Preview HTML";
      btn2.style.padding = "4px 8px";
      btn2.style.cursor = "pointer";
      //btn2.style.marginLeft = "auto";

      btn2.style.backgroundColor = "#007d7e";  // fondo azul (Bootstrap-like)
      btn2.style.color = "white";
      btn2.style.fontWeight = "bold";

      btn2.addEventListener("mouseover", () => {
        btn2.style.backgroundColor = "#006465";
      });
      btn2.addEventListener("mouseout", () => {
        btn2.style.backgroundColor = "#007d7e";
      });
  
      bar.appendChild(btn2);


      // Botón 3
      const btn3 = document.createElement("button");
      btn3.type = "button";
      btn3.textContent = "Pretty XML";
      btn3.style.padding = "4px 8px";
      btn3.style.cursor = "pointer";
      //btn2.style.marginLeft = "auto";

      btn3.style.backgroundColor = "#007d7e";  // fondo azul (Bootstrap-like)
      btn3.style.color = "white";
      btn3.style.fontWeight = "bold";

      btn3.addEventListener("mouseover", () => {
        btn2.style.backgroundColor = "#006465";
      });
      btn3.addEventListener("mouseout", () => {
        btn3.style.backgroundColor = "#007d7e";
      });
  
      bar.appendChild(btn3);
  
      // Inserta la barra **antes** del textarea (o sea, arriba)
      textarea.parentNode.insertBefore(bar, textarea);
  
      // Lógica de click
      btn.addEventListener("click", async function() {
  
        get_zip()
      });

      // Lógica de click
      btn2.addEventListener("click", async function() {
  
        openPreviewHTMLFetch()
      });

      // Lógica de click
      btn3.addEventListener("click", async function() {
  
        openPrettyXML()
      });
    }
  
    // Intenta inmediatamente si ya está en el DOM
    function tryAttach() {
      const ta = document.getElementById("id_text_xml");
      if (ta) createXrefButton(ta);
    }
  
    // Observa por si el textarea aparece más tarde o se re-renderiza
    const observer = new MutationObserver(() => tryAttach());
    observer.observe(document.documentElement, { childList: true, subtree: true });
  
    // También en DOMContentLoaded por si basta
    document.addEventListener("DOMContentLoaded", tryAttach);
  
    // Llama una vez por si ya está listo
    tryAttach();
  })();

