from bd.basedatos import BaseDatos
from modulos.sincronizador import Sincronizador
from modulos.formulario_principal import FormularioPrincipal
from modulos.dialogos_ui import (
    configurar_enfoque_automatico,
    instalar_dialogos_globales,
)


def main():

    # Todos los messagebox quedan ligados al formulario visible.
    instalar_dialogos_globales()

    bd = BaseDatos()

    try:
        bd.crear_tablas()

        # Al abrir: Tiendas_Web y las tablas del Access maestro.
        # Nunca cierra la aplicacion: si la red falla se usa la copia local.
        sincronizador = Sincronizador()
        try:
            resultado_tiendas_web = sincronizador.sincronizar_tiendas_web()
            resultado_access = sincronizador.sincronizar_access()
        finally:
            sincronizador.cerrar()

        formulario = FormularioPrincipal(
            resultado_tiendas_web=resultado_tiendas_web,
            resultado_access=resultado_access,
        )
        configurar_enfoque_automatico(formulario.ventana)
        formulario.ejecutar()

    finally:
        bd.cerrar()


if __name__ == "__main__":
    main()
