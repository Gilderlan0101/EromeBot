#!/usr/bin/env python3
"""
Erome Bot - Ponto de entrada principal
"""

import sys
import os
from pathlib import Path
from process_existing_videos import process_existing_videos
# Adicionar diretório atual ao path
sys.path.append(str(Path(__file__).parent))

from bot.main import main
try:
    process_existing_videos()
except Exception as e:
    print(f"Erro ao processar vídeos existentes: {e}")

if __name__ == '__main__':
    os.system('clear' if os.name == 'posix' else 'cls')
    main()
