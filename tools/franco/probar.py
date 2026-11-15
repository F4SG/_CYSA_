import sys
from pathlib import Path

def main():
    import pytest
    root=Path(__file__).resolve().parents[2]
    for path in ['','shared','backend','inventario','deteccion','tools/cristhian','tools/franco','simulacion','controlador']:sys.path.insert(0,str(root/path))
    raise SystemExit(pytest.main([str(root/'tests'),'-q','--import-mode=importlib',*sys.argv[1:]]))
if __name__=='__main__':main()
