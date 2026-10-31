<p align="center">
  <img src="docs/banner.svg" alt="AgroLulo System" width="100%">
</p>

<p align="center">
  <strong>Las cuentas claras de tu cultivo de lulo, desde el celular o el computador.</strong>
</p>

<p align="center">
  <a href="https://agrolulo.proyecto.lol/"><b>🌐 Ver la aplicación en línea</b></a>
  &nbsp;·&nbsp;
  <a href="#-instálala-en-tu-celular">📱 Instalar en el celular</a>
  &nbsp;·&nbsp;
  <a href="#-correr-el-proyecto">💻 Correr el proyecto</a>
</p>

---

## 🍊 ¿Qué es AgroLulo System?

**AgroLulo System** es una aplicación web pensada para los productores de **lulo** que quieren
saber, con números claros, cuánto les cuesta su cultivo y cuánto les está dejando.

Muchas veces las cuentas del cultivo se llevan en un cuaderno o de memoria: lo que se gastó en
abono, lo que se pagó a los trabajadores, cuántas canastillas salieron en cada cosecha y cuánto
falta por cobrar. AgroLulo reúne todo eso en un solo lugar y lo convierte en información fácil de
entender, para tomar mejores decisiones sobre el cultivo.

## 🎯 Objetivo

Ayudar al campesino y al pequeño productor de lulo a llevar una contabilidad sencilla y ordenada
de su cultivo, sin necesidad de saber de contabilidad, para que sepa en todo momento si su cultivo
está siendo rentable.

## ✨ ¿Qué puedes hacer?

### Para el cultivador

- 🌱 **Registrar tus cultivos**: cada lote con sus hectáreas, cantidad de matas y fecha de siembra.
- 💸 **Llevar el control de los gastos**: insumos y fertilizantes, jornales, transporte y todo lo que inviertes.
- 🧺 **Anotar cada cosecha**: canastillas, kilos y precio según la calidad del lulo (grueso, parejo o riche).
- 💰 **Seguir los pagos**: cuánto te han pagado de cada cosecha y cuánto te falta por cobrar.
- 📅 **Organizar el calendario**: siembra, riego, fumigaciones, abonadas, cosechas y demás labores del cultivo.
- 📊 **Ver tus ganancias reales**: un panel con gráficos de ingresos, gastos y utilidad por cultivo.
- 🧑‍🌾 **Aprender con Don Pancho**: un guía que explica la página a las personas nuevas y pregunta por los trabajos pendientes.
- 🔑 **Recuperar tu cuenta**: un código de 6 dígitos llega a tu correo si olvidas la contraseña.

### Para el administrador

- 👥 **Administrar las cuentas**: crear, bloquear, activar y eliminar usuarios.
- 📈 **Ver el uso de la plataforma**: un panel con porcentajes generales, sin mostrar el dinero de nadie.

## 📱 Instálala en tu celular

AgroLulo se instala como una app desde la misma página, sin descargar un APK.

| Celular | Cómo instalarla |
|---|---|
| **Android (Chrome)** | Abre la página y toca **Instalar app** |
| **iPhone (Safari)** | Toca **Compartir** y luego **Agregar a inicio** |

Queda con su propio icono y se abre a pantalla completa. Necesita internet para mostrar tus datos,
y estos nunca se guardan en el celular.

## 🔒 Seguridad

- 🔐 Las contraseñas se guardan cifradas con hash, nunca como texto.
- 👤 Cada cuenta ve únicamente la información de sus propios cultivos.
- 🛡️ Hay protección contra CSRF y XSS, y cabeceras de seguridad en todas las respuestas.
- 🚫 Los intentos fallidos de inicio de sesión, los registros y las recuperaciones tienen límites.
- 🚪 Al cambiar la contraseña se cierran las sesiones abiertas en otros dispositivos.
- 🔑 Las claves y datos privados van en variables de entorno, nunca en el código.

## 🛠️ Herramientas utilizadas

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Jinja-B41717?style=for-the-badge&logo=jinja&logoColor=white" alt="Jinja">
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Bootstrap-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white" alt="Chart.js">
  <img src="https://img.shields.io/badge/PWA-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white" alt="PWA">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white" alt="Gunicorn">
  <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git">
  <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
</p>

| Herramienta | Para qué se usó |
|---|---|
| **Python** | Lenguaje principal del proyecto |
| **Flask** | Framework web que mueve toda la aplicación |
| **Flask-Login y Flask-WTF** | Inicio de sesión, cuentas de usuario y protección CSRF |
| **SQLAlchemy** | Manejo de los datos (cultivos, gastos, cosechas, pagos) |
| **SQLite** | Base de datos donde se guarda la información |
| **Jinja** | Plantillas de las páginas |
| **HTML, CSS y JavaScript** | Diseño e interacción de la interfaz |
| **Bootstrap y Bootstrap Icons** | Estilos, diseño adaptable a celular e íconos |
| **Chart.js** | Gráficos de ingresos, gastos y ganancias |
| **PWA** | Instalación de la página como app en el celular |
| **Docker y Gunicorn** | Empaquetado y publicación de la aplicación en el servidor |
| **pytest y GitHub Actions** | Pruebas automáticas del código |
| **Git y GitHub** | Control de versiones del código |
| **Inteligencia artificial** | Apoyo en el diseño, la programación y las pruebas |

## 💻 Correr el proyecto

Necesitas **Python 3.11 o superior**. Estos comandos son para Linux o macOS.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python run.py
```

La página abre en <http://127.0.0.1:5000>. Antes de arrancarla, pon una `SECRET_KEY` propia en el
archivo `.env`.

La cuenta `admin` nace con una contraseña aleatoria. Para ponerle la tuya:

```bash
flask --app run crear-admin
```

### Con Docker

Arranca aunque falten variables, pero conviene crear primero el archivo `.env`: sin `SECRET_KEY`
las sesiones se cierran en cada reinicio, y sin los datos de correo no se puede recuperar la contraseña.

```bash
docker compose up --build
```

Por seguridad, el puerto 5000 solo queda disponible en el mismo equipo. En un servidor, la carpeta
`instance` debe pertenecer al usuario 1000, y el acceso desde internet debe pasar por un proxy con HTTPS.

### Variables de entorno

Van en el archivo `.env`, que nunca se sube a GitHub. Hay un ejemplo en [.env.example](.env.example).

| Variable | Para qué sirve | ¿Obligatoria? |
|---|---|---|
| `SECRET_KEY` | Clave que protege las sesiones | En producción |
| `MAIL_USERNAME` | Cuenta de Gmail que envía los correos | Para enviar correos |
| `MAIL_PASSWORD` | Contraseña de aplicación de Gmail | Para enviar correos |
| `MAIL_SERVER` | Servidor de correo | No: `smtp.gmail.com` |
| `MAIL_PORT` | Puerto del servidor de correo | No: `587` |
| `MAIL_SENDER` | Remitente que aparece en los correos | No: usa `MAIL_USERNAME` |
| `APP_URL` | Dirección pública de la página | En producción |
| `DETRAS_DE_HTTPS` | Ponla en `1` solo detrás de un proxy con HTTPS | En producción |

> [!IMPORTANT]
> Para `MAIL_PASSWORD`, activa la verificación en dos pasos en Gmail y crea una
> [contraseña de aplicación](https://myaccount.google.com/apppasswords). No uses la contraseña
> normal de tu correo. Con `DETRAS_DE_HTTPS=1` y sin HTTPS, nadie podrá iniciar sesión.

### Comandos útiles

| Comando | Qué hace |
|---|---|
| `pytest` | Corre las pruebas automáticas |
| `flask --app run crear-admin` | Crea la cuenta administradora o le cambia la contraseña |
| `flask --app run datos-demo` | Crea usuarios imaginarios para probar (no usar en producción) |
| `flask --app run datos-demo --borrar` | Borra esos usuarios imaginarios |
| `flask --app run recordatorios-muestra CORREO` | Envía los 7 correos de ejemplo de los recordatorios |

## 📁 Estructura del proyecto

```text
.
├── app/
│   ├── ml/          # Conteo de matas en fotos (módulo sin activar)
│   ├── models/      # Modelos de la base de datos
│   ├── routes/      # Rutas de cada sección
│   ├── static/      # CSS, JavaScript, imágenes y archivos de la app
│   ├── templates/   # Páginas HTML y correos
│   └── utils/       # Seguridad, correo, cálculos y otras ayudas
├── docs/            # Imágenes de esta documentación
├── tests/           # Pruebas automáticas
├── config.py        # Configuración de la aplicación
├── run.py           # Arranque local
├── Dockerfile
└── docker-compose.yml
```

## 🤖 Desarrollado con apoyo de la inteligencia artificial

Este proyecto se construyó con el **apoyo de herramientas de inteligencia artificial**, que
ayudaron en el diseño, la programación, las pruebas y la mejora continua de la aplicación.

## 📄 Licencia

Este proyecto es **software propietario**: todos los derechos están reservados. No está
permitido copiar, replicar, modificar ni distribuir el código sin la autorización del autor.
Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

<p align="center">Hecho con 💚 para los cultivadores de lulo</p>
