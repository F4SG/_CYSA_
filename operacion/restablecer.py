"""Vacía los registros del banco local S2 y conserva su esquema."""

import os
from pathlib import Path

from .almacen import Almacen
from .sqlserver import connection


def main():
    if os.environ.get('CYSA_SQL_DATABASE', 'CYSA_Control_S2') != 'CYSA_Control_S2':
        raise ValueError('El restablecimiento solo se aplica a CYSA_Control_S2.')
    Almacen().ready()
    script = Path(__file__).with_name('sql').joinpath('restablecer.sql').read_text(encoding='utf-8')
    with connection() as database:
        database.execute(script)
    print('Banco S2 vacío.')


if __name__ == '__main__':
    main()
