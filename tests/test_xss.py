import re
from datetime import date

from app import db
from app.models.actividad import ActividadCultivo
from tests.conftest import crear_cultivo, crear_usuario, iniciar_sesion

ATAQUE = '</script><script>alert(1)</script>'


def test_nota_del_calendario_no_rompe_el_script(logged_client, user):
    cultivo = crear_cultivo(user)
    hoy = date.today()
    db.session.add(ActividadCultivo(idCultivo=cultivo.idCultivo, tipo='otro', fecha=hoy, nota=ATAQUE))
    db.session.commit()

    html = logged_client.get(f'/calendario/{cultivo.idCultivo}').get_data(as_text=True)
    assert ATAQUE not in html
    assert 'const actividadesPorDia = {' in html


def test_nombre_del_cultivo_no_rompe_el_script(logged_client, user):
    cultivo = crear_cultivo(user, nombre=ATAQUE)
    html = logged_client.get(f'/calendario/{cultivo.idCultivo}').get_data(as_text=True)
    assert ATAQUE not in html


def test_nombre_de_usuario_no_entra_en_el_javascript_del_panel(client, admin):
    ataque = "x'+alert(1)+'"
    crear_usuario(ataque, correo='atacante@ejemplo.com')
    iniciar_sesion(client, admin)
    html = client.get('/usuarios').get_data(as_text=True)
    formulario = re.search(r'<form[^>]*data-nombre="x[^>]*>', html).group(0)
    assert 'this.dataset.nombre' in formulario
    assert 'alert' not in formulario.split('onsubmit=')[1]
