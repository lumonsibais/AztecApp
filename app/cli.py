"""Comandos de consola.

Aquí vive lo que NO debe poder hacerse por la API —conceder el rol de
administrador, dar de alta un acceso a mano— y el mantenimiento del cobro.

Podría haberse hecho con un endpoint protegido —solo un admin crea otro admin—
pero eso convierte el primer admin en un problema de arranque y, peor, deja una
ruta por la que un permiso se concede. Ya arreglamos una escalada de
privilegios en este backend (un PUT /profile con `has_full_access`); la lección
no fue parchear ese campo, fue que un permiso que se concede por la API es un
permiso que alguien va a intentar concederse. Desde la consola hace falta
acceso al servidor, que es exactamente la barrera que queremos.
"""
import click
from flask.cli import AppGroup

from app.extensions import db
from app.users.models import User

admin_cli = AppGroup("admin", help="Gestión de cuentas de administrador.")


def _buscar(email: str) -> User:
    usuario = User.query.filter_by(email=email.lower().strip()).first()
    if usuario is None:
        raise click.ClickException(f"No hay ninguna cuenta con el email {email}")
    return usuario


@admin_cli.command("grant")
@click.argument("email")
def grant(email):
    """Concede el rol de administrador a una cuenta existente.

        flask admin grant alguien@ejemplo.com
    """
    usuario = _buscar(email)

    if usuario.is_admin:
        click.echo(f"{usuario.email} ya era administrador. No he tocado nada.")
        return

    usuario.is_admin = True
    db.session.commit()
    click.secho(f"{usuario.email} ahora es administrador.", fg="green")


@admin_cli.command("revoke")
@click.argument("email")
def revoke(email):
    """Retira el rol de administrador.

        flask admin revoke alguien@ejemplo.com
    """
    usuario = _buscar(email)

    if not usuario.is_admin:
        click.echo(f"{usuario.email} no era administrador. No he tocado nada.")
        return

    usuario.is_admin = False
    db.session.commit()
    click.secho(f"{usuario.email} ya no es administrador.", fg="yellow")


@admin_cli.command("list")
def listar():
    """Quién tiene el rol ahora mismo.

    Conviene mirarlo de vez en cuando: un admin olvidado de hace seis meses es
    una cuenta con permiso de escritura que nadie vigila.
    """
    admins = User.query.filter_by(is_admin=True).order_by(User.email).all()

    if not admins:
        click.echo("No hay ningún administrador.")
        return

    click.echo(f"{len(admins)} administrador(es):")
    for u in admins:
        estado = "" if u.is_active else "  (cuenta desactivada)"
        click.echo(f"  {u.email}{estado}")


pagos_cli = AppGroup("payments", help="Mantenimiento del cobro por las tiendas.")


@pagos_cli.command("acusar-pendientes")
@click.option("--limite", default=200, show_default=True,
              help="Cuántas compras revisar como mucho.")
def acusar_pendientes(limite):
    """Reintenta el acuse de recibo de las compras de Google que se quedaron sin él.

        flask payments acusar-pendientes

    ESTO TIENE QUE CORRER PERIÓDICAMENTE. Google reembolsa automáticamente toda
    compra que no se acuse en 3 días: el comprador conserva el acceso, el dinero
    se devuelve y no llega ningún aviso de que haya pasado. El acuse normal se
    hace justo después de conceder el acceso, pero si esa llamada falla —una
    caída de red de dos segundos basta— nadie se entera, porque al usuario ya se
    le respondió que todo fue bien.

    Una vez al día con holgura; en cron, con el intérprete del proyecto.
    """
    from app.payments.services import PurchaseService

    resultado = PurchaseService.acusar_pendientes(limite)

    if not resultado["revisadas"]:
        click.echo("No hay compras pendientes de acuse.")
        return

    fallidas = resultado["revisadas"] - resultado["acusadas"]
    click.echo(
        f"{resultado['revisadas']} pendiente(s), {resultado['acusadas']} acusada(s)."
    )
    if fallidas:
        click.secho(
            f"{fallidas} siguen sin acusar. Si llevan cerca de 3 días, Google las "
            "va a reembolsar: mira el log para ver qué contesta la API.",
            fg="red",
        )


@pagos_cli.command("grant")
@click.argument("email")
@click.option("--motivo", default="cortesía", show_default=True)
def grant_access(email, motivo):
    """Concede el desbloqueo a mano, sin cobro.

        flask payments grant alguien@ejemplo.com --motivo "prueba de prensa"

    Para cortesías, pruebas y soporte. Está aquí y no en la API por lo mismo que
    el rol de administrador: un acceso que se concede por la API es un acceso
    que alguien va a intentar concederse.
    """
    import uuid

    from app.payments.models import Purchase
    from app.shared.constants import (
        CURRENCY_USD,
        FULL_ACCESS_PRICE_USD,
        FULL_ACCESS_PRODUCT,
        PROVIDER_MANUAL,
        PURCHASE_COMPLETED,
    )
    from app.shared.utils import utc_ahora

    usuario = _buscar(email)

    if usuario.has_full_access:
        click.echo(f"{usuario.email} ya tenía el acceso. No he tocado nada.")
        return

    ahora = utc_ahora()
    db.session.add(Purchase(
        id=str(uuid.uuid4()),
        user_id=usuario.id,
        product=FULL_ACCESS_PRODUCT,
        provider=PROVIDER_MANUAL,
        # La referencia se inventa aquí a propósito: la restricción única
        # (provider, external_id) exige que dos altas manuales no choquen.
        external_id=f"manual:{uuid.uuid4()}",
        amount=FULL_ACCESS_PRICE_USD,
        currency=CURRENCY_USD,
        status=PURCHASE_COMPLETED,
        purchased_at=ahora,
        refund_reason=None,
        store_environment="Manual",
    ))
    usuario.has_full_access = True
    usuario.full_access_since = ahora
    db.session.commit()

    click.secho(
        f"{usuario.email} tiene el acceso completo ({motivo}).", fg="green")


def register_cli(app):
    app.cli.add_command(admin_cli)
    app.cli.add_command(pagos_cli)
