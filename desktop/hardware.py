"""Prueba CPU/CUDA en el equipo actual, sin acceder a la cámara ni a datos reales."""
import gc
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time


def nvidia_info():
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10, errors='replace')
        if result.returncode != 0:
            return False, None
        version = re.search(r'CUDA(?: UMD)? Version:\s*(\d+)\.(\d+)', result.stdout)
        return True, tuple(map(int, version.groups())) if version else None
    except (OSError, subprocess.TimeoutExpired):
        return False, None


def cuda_packages(version):
    # Pares oficiales para Windows/Python 3.12. No instalar drivers ni CUDA Toolkit.
    # https://pytorch.org/get-started/previous-versions/
    if version and version >= (13, 0):
        return '2.14.1', '0.29.1', 'cu130'
    if version and version >= (12, 6):
        return '2.14.1', '0.29.1', 'cu126'
    if version and version >= (11, 8):
        return '2.7.1', '0.22.1', 'cu118'
    return None


def prepare_gpu():
    detected, version = nvidia_info()
    packages = cuda_packages(version)
    if not detected or not packages:
        raise RuntimeError('No se encontró un controlador NVIDIA compatible. Actualiza el controlador o usa CPU. AMD/Intel no están habilitadas como GPU en este detector Windows.')
    torch, vision, index = packages
    print('Preparando GPU con los paquetes oficiales PyTorch/CUDA. La descarga puede ocupar varios GB.', flush=True)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--upgrade',
                    f'torch=={torch}', f'torchvision=={vision}', '--index-url', f'https://download.pytorch.org/whl/{index}'], check=True)


def choose(cpu_ms, candidates):
    """Exigir una mejora del 10 % para no recomendar GPU por ruido de medición."""
    valid = [gpu for gpu in candidates if gpu.get('Ms') is not None]
    fastest = min(valid, key=lambda gpu: gpu['Ms']) if valid else None
    return (fastest['Device'] if fastest and fastest['Ms'] < cpu_ms * .9 else 'cpu'), fastest


def benchmark(weights, device):
    import numpy as np
    import torch
    from ultralytics import YOLO
    from ultralytics.utils import NUM_THREADS
    torch.set_num_threads(NUM_THREADS)
    selected = torch.device('cpu' if device == 'cpu' else f'cuda:{device}')
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    model = YOLO(str(weights))
    try:
        with torch.inference_mode():
            for _ in range(2):
                model.predict(frame, imgsz=640, device=selected, half=False, verbose=False)
            if model.predictor.device != selected:
                raise RuntimeError('El modelo no utilizó el dispositivo solicitado')
            samples = []
            for _ in range(5):
                if device != 'cpu':
                    torch.cuda.synchronize(int(device))
                start = time.perf_counter()
                model.predict(frame, imgsz=640, device=selected, half=False, verbose=False)
                if device != 'cpu':
                    torch.cuda.synchronize(int(device))
                samples.append((time.perf_counter() - start) * 1000)
        return round(statistics.median(samples), 2)
    finally:
        del model
        gc.collect()
        if device != 'cpu':
            torch.cuda.empty_cache()


def detect(root):
    import torch
    detected, _ = nvidia_info()
    devices = [(str(i), torch.cuda.get_device_name(i)) for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else []
    weights = root / 'deteccion/modelos/yolo26s.pt'
    weights.parent.mkdir(parents=True, exist_ok=True)
    print('Midiendo YOLO a 640 px: calentamiento y mediana de 5 imágenes sintéticas por dispositivo.', flush=True)
    cpu_ms = benchmark(weights, 'cpu')
    print(f'CPU: {cpu_ms:.2f} ms/imagen', flush=True)
    candidates = []
    errors = []
    for index, name in devices:
        try:
            latency = benchmark(weights, index)
            candidates.append(dict(Device=index, Name=name, Ms=latency))
            print(f'GPU {index} ({name}): {latency:.2f} ms/imagen', flush=True)
        except Exception:
            errors.append(name)
            print(f'GPU {index} no superó la prueba de inferencia; se mantiene CPU disponible.', flush=True)
    recommended, fastest = choose(cpu_ms, candidates)
    if fastest:
        reason = ('GPU más rápida en la prueba de este equipo.' if recommended != 'cpu'
                  else 'CPU es más rápida o la mejora de GPU es menor del 10 %.')
    elif errors:
        reason = 'La GPU falló en la prueba. Usa CPU; revisa el controlador y el soporte CUDA.'
    elif detected:
        reason = 'NVIDIA detectada, pero CUDA no está disponible en este entorno. Pulsa Preparar GPU para habilitarla y comparar.'
    else:
        reason = 'CPU disponible. No se detectó GPU NVIDIA/CUDA compatible; AMD/Intel usan CPU en esta versión Windows.'
    return dict(Recommended=recommended, GpuReady=bool(fastest), GpuDevice=fastest['Device'] if fastest else '0',
                GpuName=fastest['Name'] if fastest else '', CpuMs=cpu_ms, GpuMs=fastest['Ms'] if fastest else None,
                NvidiaDetected=detected, Reason=reason, Candidates=candidates)


def validate_device(device):
    if device == 'cpu':
        return device
    if not str(device).isdigit():
        raise ValueError('Modo del detector inválido')
    import torch
    index = int(device)
    if not torch.cuda.is_available() or index >= torch.cuda.device_count():
        raise RuntimeError('La GPU elegida ya no está disponible. Vuelve a detectar el equipo o selecciona CPU.')
    # No basta con detectar el controlador: ejecutar un kernel antes de abrir el editor.
    torch.zeros(1, device=f'cuda:{index}').add_(1)
    torch.cuda.synchronize(index)
    return index
