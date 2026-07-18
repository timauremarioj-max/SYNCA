"""
Test rápido: intenta crear la app y cargar modelos.
Si falla, imprime el error completo.
"""
import sys
import traceback
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    from app import create_app
    app = create_app('development')
    with app.app_context():
        from app.models.models import Usuario
        print("✓ App creada exitosamente")
        print("✓ Modelos importados")
        print("\nSi ves este mensaje, la aplicación está bien configurada.")
except Exception as e:
    print("✗ Error al crear la app:")
    print(traceback.format_exc())
    sys.exit(1)
