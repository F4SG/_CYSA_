"""Factory Method sobre el detector de Sprint 1, para pruebas locales."""
from abc import ABC, abstractmethod
from contextlib import closing

from cysa_detector.run import CameraSource


class FuenteCamara(CameraSource):
    def __init__(self, config):
        if not isinstance(config.get('source', 0), int):
            raise ValueError('La cámara local requiere un índice')
        super().__init__(config)


class FuenteVideo(CameraSource):
    def __init__(self, config, inicio_video=None):
        if not isinstance(config.get('source'), str):
            raise ValueError('La fuente secuencial requiere una ruta o URL')
        super().__init__(config, inicio_video)


class CreadorDetector(ABC):
    @abstractmethod
    def crear_fuente(self) -> CameraSource:
        ...

    def ejecutar(self, publicar):
        fuente = self.crear_fuente()
        # CameraSource.eventos es un generador con cierre de recursos en finally.
        with closing(fuente.eventos()) as eventos:
            for evento in eventos:
                publicar(evento)
        return fuente.edit_requested


class CreadorCamara(CreadorDetector):
    def __init__(self, config):
        self.config = config

    def crear_fuente(self):
        return FuenteCamara(self.config)


class CreadorVideo(CreadorDetector):
    def __init__(self, config, inicio_video=None):
        self.config = config
        self.inicio_video = inicio_video

    def crear_fuente(self):
        return FuenteVideo(self.config, self.inicio_video)
