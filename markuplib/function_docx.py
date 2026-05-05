import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.ns import qn
from lxml import etree, objectify
from django.core.files.base import ContentFile
import re, zipfile
import os


class functionsDocx:

    def openDocx(filename):
        doc = docx.Document(filename)
        return doc

    # Función: solo reemplaza mfenced que NO tengan atributos open/close y que usen |
    def replace_mfenced_pipe_only(self, mathml_root):
        mml_ns = "http://www.w3.org/1998/Math/MathML"
        for mfenced in mathml_root.xpath(".//mml:mfenced", namespaces={"mml": mml_ns}):
            has_open = mfenced.get("open")
            has_close = mfenced.get("close")
            separators = mfenced.get("separators", "")

            # Solo reemplazar si: no tiene open/close y usa barra
            if not has_open and not has_close and separators == "|":
                mrow = etree.Element(f"{{{mml_ns}}}mrow")

                mo_open = etree.Element(f"{{{mml_ns}}}mo")
                mo_open.text = "("
                mo_close = etree.Element(f"{{{mml_ns}}}mo")
                mo_close.text = ")"

                mrow.append(mo_open)
                for child in list(mfenced):
                    mrow.append(child)
                mrow.append(mo_close)

                parent = mfenced.getparent()
                if parent is not None:
                    parent.replace(mfenced, mrow)
        return mathml_root


    def extract_numbering_info(self, docx_path):
        # Diccionario para mapear numId a su tipo (numerada o viñeta)
        numbering_map = {}
        namespaces = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

        # Abrir el archivo DOCX como un archivo ZIP
        with zipfile.ZipFile(docx_path, 'r') as docx:
            # Verificar si existe el archivo numbering.xml
            if 'word/numbering.xml' in docx.namelist():
                # Extraer el archivo numbering.xml
                numbering_xml = docx.read('word/numbering.xml')
                # Parsear el XML
                numbering_tree = etree.fromstring(numbering_xml)

                # Buscar todas las definiciones abstractas de numeración
                for abstract_num in numbering_tree.findall('.//w:abstractNum', namespaces=numbering_tree.nsmap):
                    abstract_num_id = abstract_num.get(namespaces+'abstractNumId')
                    # Revisar los niveles dentro de la definición abstracta
                    for lvl in abstract_num.findall('.//w:lvl', namespaces=abstract_num.nsmap):
                        num_fmt = lvl.find('.//w:numFmt', lvl.nsmap).get(namespaces+'val')
                        ilvl = lvl.get(namespaces+'ilvl')

                        # Asignar el tipo según el valor de numFmt
                        if abstract_num_id not in numbering_map:
                            numbering_map[abstract_num_id] = {}

                        numbering_map[abstract_num_id][ilvl] = num_fmt

                # Relacionar numId con su abstractNumId
                for num in numbering_tree.findall('.//w:num', namespaces=numbering_tree.nsmap):
                    num_id = num.get(namespaces+'numId')
                    abstract_num_id = num.find('.//w:abstractNumId', namespaces=num.nsmap).get(namespaces+'val')
                    if abstract_num_id in numbering_map:
                        numbering_map[abstract_num_id]['numId'] = num_id
            else:
                numbering_map = None

        return numbering_map


    def extract_hiperlinks_info(self, docx_path):
        hiperlinks = []
        with zipfile.ZipFile(docx_path, 'r') as docx:
            # Leer relaciones del documento
            rels_path = 'word/_rels/document.xml.rels'
            if rels_path in docx.namelist():
                rels_data = docx.read(rels_path)
                rels_root = etree.fromstring(rels_data)

                # Buscar hipervínculos
                for rel in rels_root.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                    r_id = rel.attrib['Id']
                    target = rel.attrib['Target']
                    if rel.attrib['Type'].endswith('/hyperlink'):
                        hiperlinks.append((r_id, target))

        return dict(hiperlinks)


    def extract_hiperlink(self, element, rels_map, namespaces):
        links = []

        # 1. Buscar hipervínculos de texto (recursivo con .//)
        for hyperlink in element.findall('.//w:hyperlink', namespaces=namespaces):
            r_id = hyperlink.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if r_id and r_id in rels_map:
                links.append(rels_map[r_id])

        # 2. Buscar hipervínculos en imágenes (recursivo con .//)
        for hlink in element.findall('.//a:hlinkClick', namespaces=namespaces):
            r_id = hlink.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if r_id and r_id in rels_map:
                links.append(rels_map[r_id])

        return ' '.join(links) if links else None


    def extractContent(self, doc, doc_path):

        list_types = self.extract_numbering_info(doc_path) or {}

        hiperlinks_info = self.extract_hiperlinks_info(doc_path)

        found_hiperlinks = True

        # Obtener el directorio actual del archivo .py
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        # Construir la ruta completa al archivo XSLT
        xslt_path = os.path.join(BASE_DIR, "omml2mml.xsl")

        # Cargar XSLT y prepararlo
        xslt = etree.parse(xslt_path)
        transform = etree.XSLT(xslt)

        def match_paragraph(text):
            keywords = r'(?im)^\s*(?:<italic>)?\s*(palabra(?:s)?\s*clave|palavras?\s*-?\s*chave|keywords?)\s*(?:</italic>)?\s*(?::|<italic>\s*:\s*</italic>)\s*(.+)$'
            #history = r'\d{2}/\d{2}/\d{4}'
            #corresp = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            abstract = r'(?i)^resumen|^resumo|^abstract'
            accepted = r'(?i)aceptado|accepted|aceited|aprovado'
            received = r'(?i)recibido|received|recebido'

            if re.search(keywords, text):
                return '<kwd-group>'
            #if re.search(history, text):
                #return '<history>'
            #if re.search(corresp, text):
                #return '<corresp>'
            if re.search(abstract, text):
                return '<abstract>'
            if re.search(accepted, text):
                return '<date-accepted>'
            if re.search(received, text):
                return '<date-received>'
            return False

        def matches_section(a, b):
            try:
                return (
                    a.get('size') == b.get('size') and
                    a.get('bold') == b.get('bold') and
                    a.get('isupper') == b.get('isupper')
                )
            except Exception as e:
                print(f"Error comparando secciones: {e}")
                return False

        def section_priority(sections):
            return (-sections['size'], not sections['bold'], not sections['isupper'])

        def identify_section(sections, size, bold, text):
            if size == 0:
                return sections

            isupper = text.isupper()
            s_id = {'size': size, 'bold': bold, 'isupper': isupper, 'count': 0}
            
            if len(sections) == 0:
                sections.append(s_id)
                return sections

            for section in sections:
                if matches_section(s_id, section):
                    section['count'] += 1
                    return sections
            
            sections.append(s_id)
            return sections

        def clean_labels(text):
            # Eliminar etiquetas cuadradas tipo [ ... ] con espacios opcionales
            extract_label = re.sub(r'\[\s*/?\s*[\w-]+(?:\s+[^\]]+)?\s*\]', '', text)

            # Reemplazar múltiples espacios por uno solo
            clean_text = re.sub(r'\s+', ' ', extract_label)

            # Eliminar espacio antes de signos de puntuación
            clean_text = re.sub(r'\s+([;:,.])', r'\1', clean_text)

            return clean_text.strip()

        content = []
        sections = []
        found_fb = False
        review_fb = True
        #Palabras a buscar como indicador del primer bloque
        start_text = ['introducción', 'introduction', 'introdução']

        current_list = []
        current_num_id = None
        numId = None
        namespaces_p = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

        for element in doc.element.body:        
            if isinstance(element, CT_P):
                obj = {}

                namespaces = {
                    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
                }

                hiperlinks = self.extract_hiperlink(element, hiperlinks_info, namespaces) if found_hiperlinks else None

                paragraph = element
                text_paragraph = []

                # Determina si es parte de una lista
                is_numPr = paragraph.find('.//w:numPr', namespaces=paragraph.nsmap) is not None

                # obtiene id y nivel
                if is_numPr:
                    numPr = paragraph.find('.//w:numPr', namespaces=paragraph.nsmap)
                    numId = numPr.find('.//w:numId', namespaces=paragraph.nsmap).get(namespaces_p + 'val')
                    type_matches = [
                        (key, objt)
                        for key, objt in list_types.items()
                        if objt.get('numId') == numId
                    ]

                    #Es una lista diferente
                    if numId != current_num_id:
                        current_num_id = numId
                        if len(current_list) > 0:
                            current_list.append('[/list]')
                            objl = {}
                            objl['type'] = 'list'
                            objl['list'] = '\n'.join(current_list)
                            current_list = []
                            content.append(objl)
                        list_type = 'bullet'
                        if type_matches and type_matches[0][1].get(str(0)) == 'decimal':
                            list_type = 'order'

                        current_list.append(f'[list list-type="{list_type}"]')
                else:
                    #Se terminaron de agregar elementos a la lista
                    if len(current_list) > 0:
                        current_list.append('[/list]')
                        objl = {}
                        objl['type'] = 'list'
                        objl['list'] = '\n'.join(current_list)
                        current_list = []
                        content.append(objl)

                for child in paragraph:
                    if child.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hyperlink':
                        for r in child.findall('w:r', namespaces=child.nsmap):
                            t_elem = r.find('w:t', namespaces=child.nsmap)
                            if t_elem is not None and t_elem.text:
                                text_paragraph.append(t_elem.text)

                    elif child.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r':
                        namespaces = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                        sz_element = child.find('.//w:sz', namespaces=child.nsmap)
                        obj['font_size'] = 0

                        if sz_element is None:
                            p_pr = paragraph.find('.//w:rPr/w:sz', namespaces=child.nsmap)
                            if p_pr is not None:
                                sz_element = p_pr.find('.//w:pPr', namespaces=child.nsmap)

                        if sz_element is not None:
                            xml_string = etree.tostring(sz_element, pretty_print=True, encoding='unicode')
                            size_element = objectify.fromstring(xml_string)
                            font_size_value = size_element.get(namespaces+'val')
                            obj['font_size'] = int(font_size_value)/2

                        color_element = child.find('.//w:color', namespaces=child.nsmap)

                        if color_element is None:
                            p_pr = paragraph.find('.//w:pPr', namespaces=child.nsmap)
                            if p_pr is not None:
                                color_element = p_pr.find('.//w:rPr/w:color', namespaces=child.nsmap)

                        if color_element is not None:
                            xml_string_color = etree.tostring(color_element, pretty_print=True, encoding='unicode')
                            object_element = objectify.fromstring(xml_string_color)
                            color_value = object_element.get(namespaces + 'val')
                            obj['color'] = color_value

                        b_tag = child.find('.//w:b', namespaces=child.nsmap)

                        if b_tag is None:
                            p_pr = paragraph.find('.//w:rPr/w:b', namespaces=child.nsmap)
                            if p_pr is not None:
                                b_tag = p_pr.find('.//w:pPr', namespaces=child.nsmap)

                        if b_tag is not None:
                            val = b_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                            obj['bold'] = (val is None or val in ['1', 'true', 'True'])
                        else:
                            obj['bold'] = False

                        i_tag = child.find('.//w:i', namespaces=child.nsmap)

                        if i_tag is None:
                            p_pr = paragraph.find('.//w:rPr/w:i', namespaces=child.nsmap)
                            if p_pr is not None:
                                i_tag = p_pr.find('.//w:pPr', namespaces=child.nsmap)

                        if i_tag is not None:
                            val = i_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                            obj['italic'] = (val is None or val in ['1', 'true', 'True'])
                        else:
                            obj['italic'] = False
                        
                        s_tag = child.find('.//w:spacing', namespaces=child.nsmap)
                        
                        if s_tag is None:
                            p_pr = paragraph.find('.//w:rPr/w:spacing', namespaces=child.nsmap)
                            if p_pr is not None:
                                s_tag = p_pr.find('.//w:pPr', namespaces=child.nsmap)

                        if s_tag is not None:
                            val = s_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}before')
                            obj['spacing'] = not (val is None)
                        else:
                            obj['spacing'] = False

                        clean_text = clean_labels(child.text)

                        #identifica sección
                        sections = identify_section(sections, obj['font_size'], obj['bold'] , clean_text)

                        if obj['italic']:
                            text_paragraph.append('<italic>' + clean_text + '</italic>' + (f" {hiperlinks}" if hiperlinks else ""))
                        else:
                            text_paragraph.append(clean_text + (f" {hiperlinks}" if hiperlinks else ""))

                        paraph = match_paragraph(clean_text)
                        if paraph:
                            obj['paraph'] = paraph
                            obj['type'] = paraph

                        if review_fb:
                            found_fb = any(word in clean_text.lower() for word in start_text)
                        
                        #Si se encontró alguna palabra, incluye todo lo anterior en un sólo bloque
                        if found_fb:
                            found_fb = False
                            review_fb = False
                            found_hiperlinks = False
                            sections = [sections[-1]]
                            first_block = ''
                            tmp_content = []
                            abstract_mode = False 

                            for c in content:
                                if abstract_mode:
                                    if c['text'] == '' or c['spacing'] is True:
                                        abstract_mode = False
                                    else:
                                        tmp_content.append(c)
                                        continue

                                if 'paraph' in c:
                                    tmp_content.append(c)
                                    abstract_mode = False
                                    if c['paraph'] == '<abstract>':
                                        abstract_mode = True
                                        continue                                        
                                else:
                                    if 'text' in c:
                                        first_block = first_block + "\n" + c["text"]
                                    if 'table' in c:
                                        first_block = first_block + "\n" + c["table"]

                            obj_b = {}
                            obj_b['type'] = 'first_block'
                            obj_b['text'] = first_block
                            tmp_content.append(obj_b)
                            content = tmp_content
                            start_text = []

                if 'text' not in obj:
                    obj['text'] = (' '.join(text_paragraph)).strip()
                    clean_text = clean_labels(obj['text'])
                    obj['text'] = clean_text

                    paraph = match_paragraph(obj['text'])
                    if paraph:
                        obj['paraph'] = paraph
                        obj['type'] = paraph

                    if is_numPr:
                        if 'font_size' in obj:
                            del obj['font_size']
                        current_list.append(f'[list-item]{obj["text"]}[/list-item]')
                if isinstance(obj['text'], list) and len(text_paragraph) > 0:
                    obj2 = {}
                    obj2['type'] = 'text'
                    obj2['value'] = ' '.join(text_paragraph)
                    obj['text'].append(obj2)
                    text_paragraph = []
                if not is_numPr:
                    content.append(obj)
        sections.sort(key=section_priority)
        return sections, content
