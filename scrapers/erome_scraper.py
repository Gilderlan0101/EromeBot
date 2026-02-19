#!/usr/bin/env python3
"""
Scraper para Erome usando requests (sem abrir navegador)
Integrado com o sistema de logs e banco de dados
"""

import asyncio
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Importar configuração do logger
from config.custom_logger import setup_logger
from config.settings import settings
from database.models import ScrapeLog, Video, init_db

# Configurar logger (isso deve ser feito ANTES de usar os loggers especializados)
logger = setup_logger()

# AGORA podemos importar os loggers especializados
from config.custom_logger import scraping_logger, video_logger


class EromeScraper:
    """Scraper para Erome usando requests (sem navegador)"""

    def __init__(self, timeout: int = 30):
        """
        Inicializa o scraper

        Args:
            timeout: Tempo máximo de espera para requisições
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.erome.com/',
            }
        )
        scraping_logger.info('Inicializando scraper Erome (modo requests)')

    def safe_get(self, url: str) -> Optional[str]:
        """
        Faz requisição GET de forma segura

        Args:
            url: URL para acessar

        Returns:
            str: Conteúdo HTML ou None se erro
        """
        try:
            scraping_logger.debug(f'Acessando: {url}')
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            scraping_logger.error(f'Timeout ao acessar {url}')
            return None
        except requests.exceptions.RequestException as e:
            scraping_logger.error(f'Erro na requisição {url}: {e}')
            return None

    def extract_album_links(
        self, html: str, max_albums: int = 20
    ) -> List[str]:
        """
        Extrai links de álbuns do HTML da página explore

        Args:
            html: Conteúdo HTML da página
            max_albums: Número máximo de álbuns para extrair

        Returns:
            Lista de URLs de álbuns
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            album_links = []

            # Buscar links de álbuns (padrão /a/xxxxxx)
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/a/' in href:
                    full_url = (
                        href
                        if href.startswith('http')
                        else f'https://www.erome.com{href}'
                    )
                    if full_url not in album_links:
                        album_links.append(full_url)

            album_links = list(dict.fromkeys(album_links))[:max_albums]
            scraping_logger.info(f'Encontrados {len(album_links)} álbuns')
            return album_links

        except Exception as e:
            scraping_logger.error(f'Erro ao extrair links de álbuns: {e}')
            return []

    def extract_video_data_from_album(self, album_url: str) -> List[Dict]:
        """
        Extrai dados dos vídeos de um álbum

        Args:
            album_url: URL do álbum

        Returns:
            Lista de dicionários com dados dos vídeos
        """
        videos_data = []
        html = self.safe_get(album_url)

        if not html:
            return videos_data

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extrair título do álbum
            album_title = 'Sem título'
            title_tag = soup.find('h1')
            if title_tag:
                album_title = title_tag.get_text().strip()

            # Extrair username
            username = 'desconhecido'
            user_tag = soup.find(class_='username')
            if user_tag:
                username = user_tag.get_text().strip()

            # Extrair URLs de vídeos (MP4)
            # Método 1: tags video
            for video in soup.find_all('video'):
                src = video.get('src')
                if src and src.endswith('.mp4'):
                    video_id = str(uuid.uuid4())[:8]
                    video_url = (
                        src if src.startswith('http') else f'https:{src}'
                    )
                    videos_data.append(
                        {
                            'id': video_id,
                            'url': video_url,
                            'album_url': album_url,
                            'album_title': album_title,
                            'username': username,
                            'title': f'{album_title} - {username}',
                            'source': 'erome',
                        }
                    )

            # Método 2: tags source
            for source in soup.find_all('source'):
                src = source.get('src')
                if src and src.endswith('.mp4'):
                    video_id = str(uuid.uuid4())[:8]
                    video_url = (
                        src if src.startswith('http') else f'https:{src}'
                    )
                    if not any(v['url'] == video_url for v in videos_data):
                        videos_data.append(
                            {
                                'id': video_id,
                                'url': video_url,
                                'album_url': album_url,
                                'album_title': album_title,
                                'username': username,
                                'title': f'{album_title} - {username}',
                                'source': 'erome',
                            }
                        )

            # Método 3: regex no HTML para encontrar URLs MP4
            if not videos_data:
                mp4_pattern = r'(https?://[^\s"\']+?\.mp4)'
                mp4_urls = re.findall(mp4_pattern, html)
                for url in mp4_urls:
                    video_id = str(uuid.uuid4())[:8]
                    if not any(v['url'] == url for v in videos_data):
                        videos_data.append(
                            {
                                'id': video_id,
                                'url': url,
                                'album_url': album_url,
                                'album_title': album_title,
                                'username': username,
                                'title': f'{album_title} - {username}',
                                'source': 'erome',
                            }
                        )

            scraping_logger.info(
                f'Encontrados {len(videos_data)} vídeos em {album_url}'
            )

        except Exception as e:
            scraping_logger.error(
                f'Erro ao extrair vídeos de {album_url}: {e}'
            )

        return videos_data

    async def scrape_daily(self, limit: int = 20) -> List[Dict]:
        """
        Versão para uso no job diário - processa múltiplos álbuns

        Args:
            limit: Número máximo de álbuns para processar

        Returns:
            Lista de dados dos vídeos encontrados
        """
        start_time = time.time()
        all_videos = []

        try:
            scraping_logger.info(
                f'Iniciando scraping diário (limite: {limit} álbuns)'
            )

            # Acessar página explore
            html = self.safe_get('https://www.erome.com/search?q=novinhas')
            if not html:
                scraping_logger.error('Falha ao carregar página explore')
                return all_videos

            # Extrair álbuns
            album_urls = self.extract_album_links(html, max_albums=limit)

            # Processar cada álbum
            for i, album_url in enumerate(album_urls, 1):
                scraping_logger.info(
                    f'Processando álbum {i}/{len(album_urls)}'
                )

                try:
                    videos = self.extract_video_data_from_album(album_url)

                    # Verificar se vídeos já existem no banco
                    session = init_db()
                    for video_data in videos:
                        existing = (
                            session.query(Video)
                            .filter_by(source_url=video_data['url'])
                            .first()
                        )
                        if not existing:
                            all_videos.append(video_data)
                    session.close()

                    # Delay entre requisições
                    time.sleep(1)

                except Exception as e:
                    scraping_logger.error(f'Erro no álbum {album_url}: {e}')
                    continue

            # Remover duplicatas
            unique_videos = []
            seen_urls = set()
            for video in all_videos:
                if video['url'] not in seen_urls:
                    seen_urls.add(video['url'])
                    unique_videos.append(video)

            # Salvar log
            session = init_db()
            scrape_log = ScrapeLog(
                source='erome',
                albums_found=len(album_urls),
                videos_found=len(all_videos),
                videos_new=len(unique_videos),
                duration=time.time() - start_time,
            )
            session.add(scrape_log)
            session.commit()
            session.close()

            scraping_logger.info(
                f'Scraping concluído! {len(unique_videos)} novos vídeos'
            )
            return unique_videos

        except Exception as e:
            scraping_logger.error(f'Erro no scraping diário: {e}')
            return []

    async def download_video(
        self, video_url: str, output_path: Path
    ) -> Optional[Path]:
        """
        Baixa um vídeo usando yt-dlp

        Args:
            video_url: URL do vídeo
            output_path: Caminho para salvar

        Returns:
            Caminho do arquivo baixado ou None
        """
        import subprocess

        try:
            video_logger.info(f'Baixando vídeo: {video_url}')

            # Criar diretório se não existir
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Comando yt-dlp com headers
            cmd = [
                'yt-dlp',
                '--add-header',
                'Referer:https://www.erome.com/',
                '--add-header',
                'User-Agent:Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                '-o',
                str(output_path),
                video_url,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode == 0 and output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                video_logger.info(f'Download concluído: {size_mb:.2f} MB')
                return output_path
            else:
                video_logger.error(f'Erro no download: {result.stderr[:200]}')
                return None

        except subprocess.TimeoutExpired:
            video_logger.error('Timeout no download (5 minutos)')
            return None
        except Exception as e:
            video_logger.error(f'Erro ao baixar vídeo: {e}')
            return None

    def close(self):
        """Fecha a sessão"""
        if self.session:
            self.session.close()
            scraping_logger.info('Sessão HTTP fechada')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
