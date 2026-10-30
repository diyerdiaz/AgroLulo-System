"""
Comandos de consola de AgroLulo (se corren con `flask --app run <comando>`).
"""
import click


def registrar(app):

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
