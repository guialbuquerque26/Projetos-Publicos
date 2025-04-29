import os
import sys
import subprocess
import shutil
from pathlib import Path

def criar_executavel():
    """
    Script para criar o executável do Encontrador de Combinações
    usando PyInstaller.
    """
    print("Iniciando o processo de build...")
    
    # Verificar se PyInstaller está instalado
    try:
        import PyInstaller
        print("PyInstaller encontrado!")
    except ImportError:
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Limpar diretórios de build anteriores
    diretorios = ['build', 'dist']
    for diretorio in diretorios:
        if os.path.exists(diretorio):
            print(f"Removendo diretório: {diretorio}")
            shutil.rmtree(diretorio)
    
    # Opções do PyInstaller
    opcoes = [
        '--name=EncontradorDeCombinacoes',
        '--onefile',           # Criar um único arquivo executável
        '--windowed',          # Executar sem console (modo GUI)
        '--clean',             # Limpar cache antes de construir
        '--noupx',             # Não usar UPX para reduzir tamanho
        '--noconfirm',         # Substituir arquivos sem pedir confirmação
    ]
    
    # Criar o executável
    print("Criando o executável...")
    comando = [sys.executable, "-m", "PyInstaller"] + opcoes + ["Combinações.py"]
    
    try:
        subprocess.check_call(comando)
        
        # Verificar se foi criado com sucesso
        exe_path = Path("dist/EncontradorDeCombinacoes.exe")
        if exe_path.exists():
            tamanho = exe_path.stat().st_size / (1024 * 1024)  # Tamanho em MB
            print(f"\nExecutável criado com sucesso!")
            print(f"Localização: {exe_path.absolute()}")
            print(f"Tamanho: {tamanho:.2f} MB")
            print("\nVocê pode distribuir este arquivo .exe para outros usuários.")
        else:
            print("Falha ao criar o executável.")
    
    except subprocess.CalledProcessError as e:
        print(f"Erro ao criar o executável: {e}")
        return False
    
    return True

if __name__ == "__main__":
    criar_executavel() 