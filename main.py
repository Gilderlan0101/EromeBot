#!/usr/bin/env python3
"""
Erome Bot - Ponto de entrada principal
"""

import sys
from pathlib import Path

# Adicionar diretório atual ao path
sys.path.append(str(Path(__file__).parent))

from bot.main import main

if __name__ == '__main__':
    main()
