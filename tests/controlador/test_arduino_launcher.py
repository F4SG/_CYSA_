from cysa_controlador import probar_placa as prueba


def test_reset_manual_sin_interaccion_cierra_puerto(monkeypatch, capsys):
    closed = []

    class FakeBoard:
        def __init__(self, port, count, preguntar):
            self.preguntar = preguntar

        def cerrar(self):
            closed.append(True)

    class Crossing:
        grupos = ('NS', 'EO')

    monkeypatch.setattr(prueba, 'cargar_config', lambda _: (None, Crossing(), None, None))
    monkeypatch.setattr(prueba, 'Placa', FakeBoard)
    monkeypatch.setattr(prueba, 'probar', lambda board, _: board.preguntar('RESET'))
    assert prueba.main(['--config', 'fake', '--puerto', 'COM9', '--no-interactivo']) == 1
    assert closed == [True]
    assert 'RESET manual' in capsys.readouterr().out
