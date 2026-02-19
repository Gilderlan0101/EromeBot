#!/usr/bin/env python3
"""
Scraper para Erome usando Firefox com suporte a JavaScript
Integrado com o sistema de logs e banco de dados
"""

import time
import asyncio
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
import re
import uuid

# Importar loggers do projeto
from loguru.logger import *
from config.settings import settings
from database.models import init_db
from database.models import Video, ScrapeLog


class EromeScraper:
    """Scraper para Erome usando Firefox com suporte a JavaScript"""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Inicializa o scraper com Firefox

        Args:
            headless: Se True, executa o Firefox em modo headless
            timeout: Tempo máximo de espera para carregamento
        """
        self.timeout = timeout
        self.headless = headless
        self.driver = None
        scraping_logger.info('🕷️ Inicializando scraper Erome')
        self.setup_driver()

    def setup_driver(self):
        """Configura o driver do Firefox com opções seguras"""
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.service import Service
            from selenium.webdriver.firefox.options import Options
            from webdriver_manager.firefox import GeckoDriverManager

            firefox_options = Options()

            if self.headless:
                firefox_options.add_argument('--headless')
                scraping_logger.debug('Modo headless ativado')

            # Configurações para evitar detecção
            firefox_options.set_preference('dom.webdriver.enabled', False)
            firefox_options.set_preference('useAutomationExtension', False)

            # User agent realista
            user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
            firefox_options.set_preference(
                'general.useragent.override', user_agent
            )

            # Performance
            firefox_options.set_preference(
                'permissions.default.image', 2
            )  # Desabilitar imagens
            firefox_options.set_preference('dom.disable_beforeunload', True)
            firefox_options.set_preference('dom.max_script_run_time', 10)

            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(
                service=service, options=firefox_options
            )
            self.driver.set_page_load_timeout(self.timeout)

            scraping_logger.success('✅ Driver Firefox configurado com sucesso')

        except Exception as e:
            scraping_logger.error(f'❌ Erro ao configurar driver: {e}')
            raise

    def safe_get(
        self, url: str, wait_for_selector: Optional[str] = None
    ) -> bool:
        """
        Navega para URL de forma segura

        Args:
            url: URL para navegar
            wait_for_selector: Seletor CSS para esperar

        Returns:
            bool: True se sucesso
        """
        from selenium.common.exceptions import (
            TimeoutException,
            WebDriverException,
        )
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By

        try:
            scraping_logger.debug(f'Navegando para: {url}')
            self.driver.get(url)
            time.sleep(2)

            if wait_for_selector:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, wait_for_selector)
                        )
                    )
                except TimeoutException:
                    scraping_logger.debug(
                        f'Timeout esperando por: {wait_for_selector}'
                    )

            self.fast_scroll()
            return True

        except TimeoutException:
            scraping_logger.error(f'Timeout ao carregar {url}')
            return False
        except WebDriverException as e:
            scraping_logger.error(f'Erro WebDriver: {e}')
            return False
        except Exception as e:
            scraping_logger.error(f'Erro inesperado: {e}')
            return False

    def fast_scroll(self):
        """Scroll rápido para carregar conteúdo lazy-loaded"""
        try:
            self.driver.execute_script(
                'window.scrollTo(0, document.body.scrollHeight);'
            )
            time.sleep(1)
        except Exception as e:
            scraping_logger.warning(f'Erro durante scroll: {e}')

    def extract_album_links(self, max_albums: int = 20) -> List[str]:
        """
        Extrai links de álbuns da página atual

        Args:
            max_albums: Número máximo de álbuns para extrair

        Returns:
            Lista de URLs de álbuns
        """
        from selenium.webdriver.common.by import By

        try:
            album_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'a.album-link'
            )

            album_urls = []
            for element in album_elements[:max_albums]:
                href = element.get_attribute('href')
                if href and '/a/' in href and href not in album_urls:
                    album_urls.append(href)

            scraping_logger.info(f'📁 Encontrados {len(album_urls)} álbuns')
            return album_urls[:max_albums]

        except Exception as e:
            scraping_logger.error(f'Erro ao extrair links de álbuns: {e}')
            return []

    def extract_video_data_from_album(self, album_url: str) -> List[Dict]:
        """
        Extrai dados completos dos vídeos de um álbum

        Args:
            album_url: URL do álbum

        Returns:
            Lista de dicionários com dados dos vídeos
        """
        from selenium.webdriver.common.by import By

        videos_data = []

        if not self.safe_get(album_url):
            return videos_data

        try:
            # Extrair título do álbum
            album_title = 'Sem título'
            try:
                title_elem = self.driver.find_element(
                    By.CSS_SELECTOR, 'h1.album-title'
                )
                album_title = title_elem.text.strip()
            except:
                pass

            # Extrair username
            username = 'desconhecido'
            try:
                user_elem = self.driver.find_element(
                    By.CSS_SELECTOR, '.album-user'
                )
                username = user_elem.text.strip()
            except:
                pass

            # Método 1: Vídeos diretos
            video_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'video'
            )
            for video in video_elements:
                src = video.get_attribute('src')
                if src and src.endswith('.mp4'):
                    video_id = str(uuid.uuid4())[:8]
                    videos_data.append(
                        {
                            'id': video_id,
                            'url': src,
                            'album_url': album_url,
                            'album_title': album_title,
                            'username': username,
                            'title': f'{album_title} - {username}',
                            'source': 'erome',
                        }
                    )

            # Método 2: Sources
            source_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "source[src*='.mp4']"
            )
            for source in source_elements:
                src = source.get_attribute('src')
                if src:
                    video_id = str(uuid.uuid4())[:8]
                    # Verificar se já não existe
                    if not any(v['url'] == src for v in videos_data):
                        videos_data.append(
                            {
                                'id': video_id,
                                'url': src,
                                'album_url': album_url,
                                'album_title': album_title,
                                'username': username,
                                'title': f'{album_title} - {username}',
                                'source': 'erome',
                            }
                        )

            # Método 3: Regex no page source
            if not videos_data:
                page_source = self.driver.page_source
                mp4_pattern = (
                    r'(https?://[^"\']+?\.erome\.com[^"\']+\.mp4[^"\']*)'
                )
                mp4_urls = re.findall(mp4_pattern, page_source)
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
                f'🎥 Encontrados {len(videos_data)} vídeos em {album_url}'
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
        scrape_log = ScrapeLog(source='erome')

        try:
            scraping_logger.info(
                f'🚀 Iniciando scraping diário (limite: {limit} álbuns)'
            )

            # Navegar para explore
            if not self.safe_get(
                'https://www.erome.com/explore', wait_for_selector='.album'
            ):
                scraping_logger.error('Falha ao carregar página explore')
                return all_videos

            # Extrair álbuns
            album_urls = self.extract_album_links(max_albums=limit)
            scrape_log.albums_found = len(album_urls)

            # Processar cada álbum
            for i, album_url in enumerate(album_urls, 1):
                scraping_logger.info(
                    f'Processando álbum {i}/{len(album_urls)}'
                )

                try:
                    videos = self.extract_video_data_from_album(album_url)

                    # Filtrar apenas vídeos novos
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

                    scrape_log.videos_found += len(videos)
                    time.sleep(2)  # Delay entre álbuns

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

            scrape_log.videos_new = len(unique_videos)
            scrape_log.duration = time.time() - start_time

            scraping_logger.success(
                f'✅ Scraping concluído! {len(unique_videos)} novos vídeos'
            )

            # Salvar log
            session = init_db()
            session.add(scrape_log)
            session.commit()
            session.close()

            return unique_videos

        except Exception as e:
            scraping_logger.error(f'❌ Erro no scraping diário: {e}')
            scrape_log.errors = str(e)

            session = init_db()
            session.add(scrape_log)
            session.commit()
            session.close()

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
            video_logger.info(f'⬇️ Baixando vídeo: {video_url}')

            # Comando yt-dlp com headers
            cmd = [
                'yt-dlp',
                '--add-header',
                'Referer:https://www.erome.com/',
                '--add-header',
                f'User-Agent:{settings.USER_AGENT}',
                '-o',
                str(output_path),
                video_url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                video_logger.success(f'✅ Download concluído: {size_mb:.2f} MB')
                return output_path
            else:
                video_logger.error(f'❌ Erro no download: {result.stderr}')
                return None

        except Exception as e:
            video_logger.error(f'Erro ao baixar vídeo: {e}')
            return None

    def close(self):
        """Fecha o driver"""
        if self.driver:
            try:
                self.driver.quit()
                scraping_logger.info('Driver Firefox fechado')
            except Exception as e:
                scraping_logger.error(f'Erro ao fechar driver: {e}')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
