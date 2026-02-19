"""
Editor de vídeo básico para Erome Bot
Versão simplificada apenas para testes
"""

import asyncio
from pathlib import Path
from typing import Optional
import subprocess
import json
import logging
from config.custom_logger import *


class VideoEditor:
    """Editor de vídeo básico (versão para testes)"""

    def __init__(self):
        print('🎬 Inicializando VideoEditor (modo básico)')

    async def process_video(
        self, video_path: Path, title: str
    ) -> Optional[Path]:
        """
        Processa um vídeo (versão básica - apenas copia)

        Args:
            video_path: Caminho do vídeo original
            title: Título do vídeo

        Returns:
            Caminho do vídeo processado ou None
        """
        print(f'📹 Processando vídeo: {title[:50]}...')

        try:
            # Verificar se o arquivo existe
            if not video_path.exists():
                logging.error(f'❌ Arquivo não encontrado: {video_path}')
                return None

            # Criar nome do arquivo editado
            edited_path = video_path.parent / f'edited_{video_path.name}'

            # Modo básico: apenas copiar o arquivo (simulando edição)
            logging.debug(f'📋 Copiando arquivo para: {edited_path}')

            # Usar shutil para copiar (mais rápido que ffmpeg para teste)
            import shutil

            shutil.copy2(video_path, edited_path)

            # Verificar se a cópia foi bem sucedida
            if edited_path.exists():
                size_mb = edited_path.stat().st_size / (1024 * 1024)
                logging.success(
                    f'✅ Vídeo processado (cópia): {size_mb:.2f} MB'
                )
                return edited_path
            else:
                logging.error('❌ Falha ao copiar arquivo')
                return None

        except Exception as e:
            logging.error(f'❌ Erro processando vídeo: {e}')
            return None

    def get_duration(self, video_path: Path) -> int:
        """
        Obtém a duração do vídeo em segundos

        Args:
            video_path: Caminho do vídeo

        Returns:
            Duração em segundos (0 se não conseguir)
        """
        try:
            # Tentar usar ffprobe (se disponível)
            cmd = [
                'ffprobe',
                '-v',
                'quiet',
                '-print_format',
                'json',
                '-show_format',
                str(video_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                logging.debug(f'⏱️ Duração: {duration:.0f}s')
                return int(duration)
            else:
                # Fallback: retornar um valor padrão
                logging.warning(
                    '⚠️ ffprobe não disponível, usando duração padrão'
                )
                return 60  # 1 minuto padrão

        except Exception as e:
            logging.error(f'Erro ao obter duração: {e}')
            return 60  # valor padrão

    async def add_watermark(
        self, video_path: Path, text: str
    ) -> Optional[Path]:
        """
        Adiciona watermark ao vídeo (versão básica)

        Args:
            video_path: Caminho do vídeo
            text: Texto do watermark

        Returns:
            Caminho do vídeo com watermark
        """
        logging.info(f"💧 Adicionando watermark: '{text}'")

        # Versão básica: apenas retorna o mesmo arquivo
        logging.debug('Modo básico: watermark não implementado')
        return video_path

    async def create_clip(
        self, video_path: Path, start: int, duration: int
    ) -> Optional[Path]:
        """
        Cria um clipe do vídeo (versão básica)

        Args:
            video_path: Caminho do vídeo
            start: Tempo de início em segundos
            duration: Duração do clipe em segundos

        Returns:
            Caminho do clipe
        """
        logging.info(f'✂️ Criando clipe: {start}s - {start + duration}s')

        # Versão básica: retorna o vídeo original
        logging.debug('Modo básico: corte não implementado')
        return video_path

    async def generate_thumbnail(self, video_path: Path) -> Optional[Path]:
        """
        Gera thumbnail do vídeo (versão básica)

        Args:
            video_path: Caminho do vídeo

        Returns:
            Caminho da thumbnail
        """
        logging.info('🖼️ Gerando thumbnail')

        try:
            # Criar nome da thumbnail
            thumbnail_path = video_path.with_suffix('.jpg')

            # Tentar usar ffmpeg para extrair frame
            cmd = [
                'ffmpeg',
                '-i',
                str(video_path),
                '-ss',
                '00:00:05',  # Frame aos 5 segundos
                '-vframes',
                '1',
                '-q:v',
                '2',
                '-y',
                str(thumbnail_path),
            ]

            result = subprocess.run(cmd, capture_output=True)

            if result.returncode == 0 and thumbnail_path.exists():
                logging.success(f'✅ Thumbnail gerada: {thumbnail_path.name}')
                return thumbnail_path
            else:
                # Fallback: criar uma imagem simples
                logging.warning(
                    '⚠️ ffmpeg não disponível, usando imagem padrão'
                )
                return await self._create_dummy_thumbnail(thumbnail_path)

        except Exception as e:
            logging.error(f'❌ Erro gerando thumbnail: {e}')
            return None

    async def _create_dummy_thumbnail(self, path: Path) -> Path:
        """
        Cria uma thumbnail dummy (quando ffmpeg não disponível)

        Args:
            path: Caminho para salvar

        Returns:
            Caminho da thumbnail criada
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Criar imagem preta com texto
            img = Image.new('RGB', (320, 180), color='black')
            d = ImageDraw.Draw(img)

            # Adicionar texto
            text = 'Erome Bot'
            try:
                # Tentar usar fonte padrão
                font = ImageFont.load_default()
                d.text((10, 10), text, fill='white', font=font)
            except:
                d.text((10, 10), text, fill='white')

            # Salvar
            img.save(path)
            logging.debug(f'🖼️ Thumbnail dummy criada: {path.name}')
            return path

        except Exception as e:
            logging.error(f'Erro criando thumbnail dummy: {e}')
            # Criar arquivo vazio como fallback
            path.touch()
            return path


# Versão ainda mais simples para testes rápidos
class VideoEditorMinimal:
    """Versão mínima do editor (apenas para testes)"""

    async def process_video(self, video_path: Path, title: str) -> Path:
        """Apenas retorna o mesmo caminho"""
        logging.info(f'📹 [MINIMAL] Processando: {title[:30]}...')
        return video_path

    def get_duration(self, video_path: Path) -> int:
        """Retorna duração fixa"""
        return 60

    async def add_watermark(self, video_path: Path, text: str) -> Path:
        """Apenas retorna o mesmo caminho"""
        return video_path

    async def create_clip(
        self, video_path: Path, start: int, duration: int
    ) -> Path:
        """Apenas retorna o mesmo caminho"""
        return video_path

    async def generate_thumbnail(self, video_path: Path) -> Path:
        """Cria thumbnail dummy"""
        thumb_path = video_path.with_suffix('.jpg')
        thumb_path.touch()
        return thumb_path


# Para testar rapidamente:
if __name__ == '__main__':

    async def test():
        editor = VideoEditor()
        test_path = Path('test.mp4')

        # Criar arquivo de teste se não existir
        if not test_path.exists():
            test_path.touch()

        result = await editor.process_video(test_path, 'Vídeo de teste')
        duration = editor.get_duration(test_path)
        print(f'Resultado: {result}')
        print(f'Duração: {duration}s')

    asyncio.run(test())
