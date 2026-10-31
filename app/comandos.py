"""
Comandos de consola de AgroLulo (se corren con `flask --app run <comando>`).
"""
import click


def registrar(app):

    @app.cli.command('crear-admin')
    @click.option('--usuario', default='admin', show_default=True, help='Nombre de la cuenta administradora.')
    def crear_admin(usuario):
        """Crea la cuenta administradora, o le pone una contraseña nueva si
        ya existe. La contraseña se escribe a mano (no se ve en pantalla) y
        tiene que cumplir las mismas reglas de seguridad de la página."""
        from app import db
        from app.models.users import User
        from app.utils.seguridad import errores_contrasena, mensaje_contrasena_invalida

        for _ in range(3):
            clave = click.prompt('Contraseña nueva', hide_input=True, confirmation_prompt='Repítela')
            errores = errores_contrasena(clave, usuario)
            if not errores:
                break
            click.echo(mensaje_contrasena_invalida(errores))
        else:
            raise click.ClickException('Tres intentos sin una contraseña válida. No se cambió nada.')

        cuenta = User.query.filter_by(nameUser=usuario).first()
        nueva = cuenta is None
        if nueva:
            cuenta = User(nameUser=usuario)
            db.session.add(cuenta)
        cuenta.isAdmin = True
        cuenta.activo = True
        cuenta.debe_cambiar_password = False
        cuenta.tutorial_visto = True
        cuenta.set_password(clave)
        db.session.commit()
        click.echo(f"Listo: cuenta administradora '{usuario}' {'creada' if nueva else 'actualizada'}.")

    @app.cli.command('datos-demo')
    @click.option('--borrar', is_flag=True, help='Borra los usuarios imaginarios (y solo esos).')
    def datos_demo(borrar):
        """Llena la base de datos con cultivadores imaginarios y sus lotes
        (gastos, cosechas, pagos y calendario) para probar la página. La
        contraseña de todos se muestra una sola vez en pantalla."""
        import secrets
        from app.utils.datos_demo import borrar_datos_demo, crear_datos_demo

        if borrar:
            n = borrar_datos_demo()
            click.echo(f'Listo: se borraron {n} usuarios imaginarios con todos sus datos.')
            return

        # La contraseña solo se muestra aquí, una vez: no se guarda en ningún
        # archivo (en la base de datos queda encriptada, como todas).
        clave = f'LuloDemo-{secrets.randbelow(9000) + 1000}'
        usuarios, lotes = crear_datos_demo(clave)
        if usuarios:
            click.echo(f'Contraseña de los usuarios imaginarios (anótala, no se guarda): {clave}')
        click.echo(f'Listo: {usuarios} usuarios imaginarios y {lotes} lotes creados.')

    @app.cli.command('recordatorios-muestra')
    @click.argument('destino')
    def recordatorios_muestra(destino):
        """Manda a DESTINO los 7 correos de ejemplo de los recordatorios del
        calendario (uno por plantilla), para ver cómo se ven."""
        from app.utils.recordatorios import ejemplos, enviar_recordatorio

        for i, (hoy, atrasadas) in enumerate(ejemplos(), 1):
            enviar_recordatorio(destino, 'Diyer', hoy, atrasadas)
            click.echo(f'  {i}/7 enviado')
        click.echo(f'Listo: 7 correos de ejemplo enviados a {destino}.')

    @app.cli.command('desbloquear-ip')
    @click.argument('ip')
    def desbloquear_ip(ip):
        """Quita el bloqueo de una IP (por ejemplo, una persona real que
        quedó bloqueada por compartir conexión con un bot)."""
        from app.utils.seguridad import limpiar_intentos

        limpiar_intentos(ip, 'bloqueo_ip')
        limpiar_intentos(ip, 'sondeo')
        click.echo(f'Listo: la IP {ip} ya no está bloqueada.')
