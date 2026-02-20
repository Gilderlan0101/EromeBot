#!/usr/bin/env python3
"""
Editor de vídeo básico para o Erome Bot
Recursos: corte, banner, marca d'água e ajuste de orientação
"""

import random
import subprocess
from pathlib import Path
from datetime import datetime
import uuid


# Importar configuração de logging PRIMEIRO
from config.custom_logger import setup_logger

# Configurar logger do projeto ANTES de outras importações
logger = setup_logger(log_dir='logs', rotation='500 MB', retention='30 days')



# Importar loggers
from config.custom_logger import video_logger


class VideoEditor:
    """Editor de vídeo básico usando ffmpeg"""

    def __init__(self):
        """Inicializa o editor"""
        video_logger.info('Inicializando VideoEditor (modo básico)')
        self.check_ffmpeg()

    def check_ffmpeg(self):
        """Verifica se o ffmpeg está instalado"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            video_logger.debug('ffmpeg encontrado')
        except (subprocess.CalledProcessError, FileNotFoundError):
            video_logger.error('ffmpeg não encontrado. Instale com: sudo apt install ffmpeg')
            raise

    def get_video_info(self, video_path: Path) -> dict:
        """
        Obtém informações do vídeo usando ffprobe

        Args:
            video_path: Caminho do vídeo

        Returns:
            Dict com informações do vídeo
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            import json
            info = json.loads(result.stdout)

            # Extrair informações relevantes
            video_info = {
                'duration': float(info['format']['duration']),
                'size': int(info['format']['size']),
                'streams': []
            }

            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    video_info.update({
                        'width': int(stream.get('width', 0)),
                        'height': int(stream.get('height', 0)),
                        'codec': stream.get('codec_name', 'unknown')
                    })
                    break

            return video_info

        except Exception as e:
            video_logger.error(f'Erro ao obter informações do vídeo: {e}')
            return {'duration': 0, 'width': 0, 'height': 0}

    def get_random_crop_time(self, duration: float) -> tuple:
            """
            Gera tempos de corte aleatórios entre 7 segundos

            Args:
                duration: Duração total do vídeo

            Returns:
                Tuple (start_time, end_time)
            """
            # Duração do corte (7 segundos fixos)
            crop_duration = 7  # Alterado de 15-20 para 7 segundos

            # Garantir que não ultrapasse a duração do vídeo
            if duration <= crop_duration:
                return (0, duration)

            # Ponto de início aleatório
            max_start = duration - crop_duration
            start_time = random.uniform(0, max_start)
            end_time = start_time + crop_duration

            return (start_time, end_time)

    async def process_video(self, input_path: Path, title: str = '') -> Path:
        """
        Processa o vídeo: corta, adiciona banner e marca d'água

        Args:
            input_path: Caminho do vídeo original
            title: Título do vídeo (opcional)

        Returns:
            Caminho do vídeo processado
        """
        from config.settings import settings

        try:
            video_logger.info(f'Processando vídeo: {input_path.name}')

            # Obter informações do vídeo
            info = self.get_video_info(input_path)
            duration = info['duration']

            if duration <= 0:
                video_logger.error('Duração inválida')
                return None

            # Gerar nome do arquivo de saída
            output_filename = f"edited_{uuid.uuid4().hex[:8]}.mp4"
            output_path = settings.EDITED_DIR / output_filename

            # 1. Primeiro: cortar o vídeo
            start_time, end_time = self.get_random_crop_time(duration)
            crop_duration = end_time - start_time

            video_logger.info(f'Cortando vídeo: {start_time:.2f}s -> {end_time:.2f}s (duração: {crop_duration:.2f}s)')

            # Arquivo temporário após corte
            temp_cut = settings.TEMP_DIR / f"temp_cut_{uuid.uuid4().hex[:8]}.mp4"

            # Comando para cortar o vídeo
            cut_cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-ss', str(start_time),
                '-t', str(crop_duration),
                '-c', 'copy',  # Copiar sem reencodar (mais rápido)
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Sobrescrever se existir
                str(temp_cut)
            ]

            video_logger.debug(f'Executando corte: {" ".join(cut_cmd)}')
            result = subprocess.run(cut_cmd, capture_output=True, text=True)

            if result.returncode != 0 or not temp_cut.exists():
                video_logger.error(f'Erro no corte: {result.stderr}')
                return None

            video_logger.info('Corte concluído')

            # 2. Agora adicionar banner e marca d'água
            video_logger.info('Adicionando banner e marca d\'água')

            # Criar filtros complexos do ffmpeg
            filters = []

            # Ajustar para formato vertical (9:16) se necessário
            if info['width'] > info['height']:
                # Vídeo está na horizontal, converter para vertical
                video_logger.info('Convertendo para formato vertical (9:16)')
                filters.append(
                    "scale=iw*min(1080/iw\,1920/ih):ih*min(1080/iw\,1920/ih),"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
                )

            # Banner no rodapé
            banner_text = "Completo no bot"
            banner_filter = (
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{banner_text}':"
                f"fontcolor=white:"
                f"fontsize=24:"
                f"box=1:"
                f"boxcolor=black@0.5:"
                f"boxborderw=10:"
                f"x=(w-text_w)/2:"
                f"y=h-text_h-20"
            )
            filters.append(banner_filter)

            # Marca d'água com @ do bot no canto superior direito
            watermark_text = "@lunaSafe_bot"
            watermark_filter = (
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{watermark_text}':"
                f"fontcolor=white:"
                f"fontsize=18:"
                f"box=1:"
                f"boxcolor=black@0.5:"
                f"boxborderw=5:"
                f"x=w-text_w-10:"
                f"y=10"
            )
            filters.append(watermark_filter)

            # Combinar todos os filtros
            filter_complex = ','.join(filters)

            # Comando final com todos os efeitos
            final_cmd = [
                'ffmpeg',
                '-i', str(temp_cut),
                '-vf', filter_complex,
                '-c:a', 'aac',  # Codec de áudio
                '-b:a', '128k',  # Bitrate de áudio
                '-preset', 'fast',  # Preset mais rápido
                '-y',  # Sobrescrever
                str(output_path)
            ]

            video_logger.debug(f'Aplicando efeitos finais')
            result = subprocess.run(final_cmd, capture_output=True, text=True)

            # Limpar arquivo temporário
            if temp_cut.exists():
                temp_cut.unlink()

            if result.returncode != 0 or not output_path.exists():
                video_logger.error(f'Erro ao aplicar efeitos: {result.stderr}')
                return None

            # Obter tamanho do arquivo final
            size_mb = output_path.stat().st_size / (1024 * 1024)
            video_logger.info(f'✅ Vídeo processado: {output_path.name} ({size_mb:.2f} MB)')

            return output_path

        except Exception as e:
            video_logger.error(f'Erro no processamento: {e}')
            return None

    def get_duration(self, video_path: Path) -> int:
        """
        Obtém a duração do vídeo em segundos

        Args:
            video_path: Caminho do vídeo

        Returns:
            Duração em segundos
        """
        info = self.get_video_info(video_path)
        return int(info.get('duration', 0))


# Teste rápido se executado diretamente
if __name__ == '__main__':
    import asyncio

    async def test():
        editor = VideoEditor()
        test_video = Path('storage/videos/7c572f8d.mp4')
        if test_video.exists():
            result = await editor.process_video(test_video)
            print(f'Resultado: {result}')
        else:
            print('Arquivo de teste não encontrado')

    asyncio.run(test())
