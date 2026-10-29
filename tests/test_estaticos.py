import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / 'app'


def test_css_tiene_las_llaves_balanceadas():
    """Una llave sin cerrar (p. ej. tras unir ramas) hace que el navegador
    ignore todos los estilos que vienen después."""
    css = (RAIZ / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
    sin_comentarios = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    profundidad = 0
    for caracter in sin_comentarios:
        if caracter == '{':
            profundidad += 1
        elif caracter == '}':
            profundidad -= 1
            assert profundidad >= 0, 'Hay una llave } de más en style.css'
    assert profundidad == 0, f'Quedan {profundidad} llaves sin cerrar en style.css'


def test_plantillas_sin_marcas_de_conflicto():
    for archivo in list((RAIZ / 'templates').rglob('*.html')) + list((RAIZ / 'static').rglob('*.css')) + list((RAIZ / 'static' / 'js').glob('*.js')):
        texto = archivo.read_text(encoding='utf-8')
        assert '<<<<<<<' not in texto and '>>>>>>>' not in texto, archivo.name
