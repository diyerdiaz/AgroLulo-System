from datetime import date

from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

bp = Blueprint('landing', __name__)


@bp.route('/')
def index():
    """Página de presentación de AgroLulo (pública). Si la persona ya inició
    sesión, se va directo a su Dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return render_template('landing/index.html', anio=date.today().year)
