from flask_login import UserMixin
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from io import BytesIO
import base64
from PIL import Image
import os
from flask import url_for, current_app

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    idUser = db.Column(db.Integer, primary_key=True)
    nameUser = db.Column(db.String(80), unique=True, nullable=False)
    # Guarda el hash de la contraseña (nunca la contraseña en texto plano).
    # Se ensanchó de 120 a 255 caracteres porque los hashes modernos
    # (scrypt/pbkdf2) pueden ser más largos que una contraseña normal.
    passwordUser = db.Column(db.String(255), nullable=False)
    # Solo la cuenta 'admin' (sembrada al arrancar la app) queda marcada como
    # administradora por defecto. Cualquier cuenta creada desde "Crear Cuenta
    # Nueva" en el login es una cuenta normal, sin acceso a la sección de
    # Usuarios registrados.
    isAdmin = db.Column(db.Boolean, default=False, nullable=False)
    # Cuentas creadas por un usuario cualquiera desde "Crear Cuenta Nueva"
    # quedan bloqueadas (activo=False) hasta que el administrador las active
    # a mano desde la sección de Usuarios. La cuenta 'admin' y las que ya
    # existían antes de este campo quedan activas por defecto.
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # loansUser = db.relationship("Loan", back_populates="user", lazy='dynamic')
    # computerLoansUser = db.relationship('ComputerLoan', back_populates='user', lazy='dynamic')

    def get_id(self):
        return str(self.idUser)

    def set_password(self, password_en_texto_plano):
        """Guarda la contraseña ya encriptada (hash), nunca el texto plano."""
        self.passwordUser = generate_password_hash(password_en_texto_plano, method='pbkdf2:sha256')

    def check_password(self, password_en_texto_plano):
        """Compara una contraseña escrita por el usuario contra el hash guardado."""
        return check_password_hash(self.passwordUser, password_en_texto_plano)

    @staticmethod
    def es_hash_valido(valor):
        """True si 'valor' ya tiene pinta de hash generado por Werkzeug (y no
        una contraseña vieja guardada en texto plano)."""
        return isinstance(valor, str) and (valor.startswith('pbkdf2:') or valor.startswith('scrypt:'))

    def to_dict(self):
        return {
            "idUser": self.idUser,
            "nameUser": self.nameUser,
            # Ya no se incluye la contraseña (ni su hash) en el diccionario:
            # antes esto se mandaba tal cual en las rutas que devuelven JSON.
            "isAdmin": self.isAdmin,
            "activo": self.activo,
        }
    
    def save(self):
        db.add(self)
        db.commit()

    def generate_qr(self):
        # Datos del usuario para el QR
        import json
        from PIL import Image
        user_data = json.dumps({
            'ID': self.idUser,
            'Name': self.nameUser
        })
        print("Generando código QR para el usuario:", user_data)
        # Generar el código QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(user_data)
        qr.make(fit=True)
        
        # Crear una imagen del QR
        img_qr = qr.make_image(fill='black', back_color='white').convert('RGB')
        
        # Cargar la imagen que se incluirá en el QR
        logo_path = os.path.join(current_app.root_path, 'static', 'img', 'sena.png')
        logo = Image.open(logo_path)
                
        # Calcular el tamaño del logo
        logo_size = 50
        logo = logo.resize((logo_size, logo_size))
        
        # Calcular la posición para centrar el logo en el QR
        pos = ((img_qr.size[0] - logo_size) // 2, (img_qr.size[1] - logo_size) // 2)
        
        # Pegar el logo en el QR
        img_qr.paste(logo, pos)
        
        # Convertir la imagen a base64
        buffered = BytesIO()
        img_qr.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str