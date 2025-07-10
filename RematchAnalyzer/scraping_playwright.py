"""
Scraping dinâmico usando Playwright para capturar dados do RematchTracker
Captura informações que só aparecem após JavaScript carregar (A+, Playing Style, etc.)
"""

import asyncio
import json
import re
import time
from playwright.async_api import async_playwright

async def scraping_dinamico_rematch(steam_id):
    """
    Faz scraping dinâmico da página do RematchTracker
    Captura: Grade (A+), Playing Style Analysis, tipo de jogador, etc.
    """
    url = f"https://www.rematchtracker.com/player/steam/{steam_id}"
    
    async with async_playwright() as p:
        browser = None
        try:
            print(f"🎭 Iniciando Playwright para Steam ID: {steam_id}")
            
            # Configurar navegador
            browser = await p.chromium.launch(
                headless=True,  # True = não mostra janela
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Criar nova página com configurações
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            print(f"📡 Acessando: {url}")
            
            # Navegar para a página
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            print("⏳ Aguardando elementos dinâmicos carregarem...")
            
            # Aguardar carregamento genérico da página
            print("⏳ Aguardando página carregar completamente...")
            await page.wait_for_timeout(8000)  # Aguardar 8 segundos para carregamento
            
            print("📊 Capturando dados dinâmicos...")
            
            # Estrutura de dados para capturar
            dados_dinamicos = {
                'steam_id': steam_id,
                'url': url,
                'captured_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'method': 'playwright_dynamic',
                'status': 'success',
                
                # Informações do jogador
                'player_info': {
                    'display_name': None,
                    'grade': None,        # A+, B+, etc.
                    'player_type': None,  # Impact Player, etc.
                    'rank': None          # Elite, Expert, etc.
                },
                
                # Análise de estilo de jogo (/100)
                'playing_style_analysis': {
                    'attack': None,
                    'playmaking': None,
                    'finishing': None,
                    'defense': None,
                    'goalkeeper': None,
                    'impact': None
                },
                
                # Estatísticas extras da página
                'page_stats': {
                    'win_rate_percent': None,
                    'shot_accuracy_percent': None,
                    'mvp_rate_percent': None,
                    'steals_total': None,
                    'tackles_total': None
                },
                
                # Elementos raw encontrados (debug)
                'raw_elements': {},
                'full_page_text': None
            }
            
            # Capturar todo o conteúdo da página
            page_content = await page.content()
            page_text = await page.text_content('body')
            dados_dinamicos['full_page_text'] = page_text[:2000]  # Primeiros 2000 chars
            
            print("=" * 60)
            print("🔍 DEBUG - CONTEÚDO DA PÁGINA CAPTURADO:")
            print("=" * 60)
            print(f"📄 Primeiros 500 caracteres da página:")
            print(f"{page_text[:500]}")
            print("=" * 60)
            
            # 1. CAPTURAR NOME DO JOGADOR (GENÉRICO)
            try:
                # Capturar qualquer nome que apareça na página
                display_name = None
                
                # Procurar por padrões de nome comum
                name_patterns = [
                    r'([A-Z0-9]{2,6}\s*\|\s*[^\n\r\|]{3,25})',  # Team | Player
                    r'([A-Za-z0-9_\s]{3,30})\s*Steam',          # Nome antes de "Steam"
                    r'([A-Za-z0-9_\s]{3,30})\s*View on',        # Nome antes de "View on"
                    r'([A-Za-z0-9_\s]{3,30})\s*Current Rank',   # Nome antes de "Current Rank"
                ]
                
                for pattern in name_patterns:
                    match = re.search(pattern, page_text[:1000])  # Primeiros 1000 chars
                    if match:
                        candidate = match.group(1).strip()
                        # Filtrar candidatos válidos
                        if (len(candidate) >= 3 and len(candidate) <= 30 and 
                            not candidate.isdigit() and 
                            'REMATCH' not in candidate.upper() and
                            'TRACKER' not in candidate.upper()):
                            display_name = candidate
                            break
                
                # Fallback: pegar primeiro texto "limpo" da página
                if not display_name:
                    lines = page_text[:2000].split('\n')
                    for line in lines:
                        line = line.strip()
                        if (3 <= len(line) <= 30 and 
                            not line.isdigit() and 
                            not line.startswith('http') and
                            'REMATCH' not in line.upper()):
                            display_name = line
                            break
                
                if display_name:
                    dados_dinamicos['player_info']['display_name'] = display_name
                    print(f"👤 NOME ENCONTRADO: {display_name}")
                else:
                    print("⚠️ Nome do jogador não identificado")
                    
                print(f"🔍 DEBUG NOME - Primeiros 1000 chars analisados:")
                print(f"   {page_text[:1000][:200]}...")  # Mostra 200 chars para debug
                    
            except Exception as e:
                print(f"⚠️ Erro ao capturar nome: {e}")
            
            # 2. CAPTURAR GRADE/NOTA (qualquer padrão que apareça)
            try:
                # Buscar qualquer padrão de grade/nota no texto com melhor regex
                grade_patterns = [
                    r'\b([S][+\-]?)\b',     # S, S+, S-
                    r'\b([A-F][+\-]?)\b',   # A+, A, A-, B+, B, B-, etc.
                    r'\b([A-F][+\-])\b',    # Explicitamente A+, A-, B+, B-, etc.
                    r'([S][+\-])',          # S+, S- sem word boundaries
                    r'([A-F][+\-])',        # A+, A-, B+, B-, etc. sem word boundaries
                    r'Grade:\s*([S][+\-]?)',     # Grade: S+
                    r'Grade:\s*([A-F][+\-]?)',   # Grade: A+
                    r'Nota:\s*([S][+\-]?)',      # Nota: S+
                    r'Nota:\s*([A-F][+\-]?)',    # Nota: A+
                ]
                
                grade_found = None
                all_matches = []
                
                for pattern in grade_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    all_matches.extend(matches)
                    print(f"   Padrão '{pattern}': {matches[:5]}")  # Debug
                    
                    for match in matches:
                        # Validar se parece uma grade válida
                        if match and 1 <= len(match) <= 3:
                            # Priorizar grades com modificadores
                            if '+' in match or '-' in match:
                                grade_found = match.upper()
                                print(f"📊 Grade com modificador encontrada: {grade_found}")
                                break
                            elif not grade_found:  # Se não achou ainda, usar sem modificador
                                grade_found = match.upper()
                                print(f"📊 Grade base encontrada: {grade_found}")
                    
                    if grade_found and ('+' in grade_found or '-' in grade_found):
                        break  # Se encontrou com modificador, para de procurar
                
                # Se não encontrou nada, tentar buscar padrões mais específicos
                if not grade_found and all_matches:
                    # Procurar especificamente por padrões S+, A+, etc no texto
                    specific_patterns = [
                        r'(S\+)', r'(S\-)', r'(A\+)', r'(A\-)', 
                        r'(B\+)', r'(B\-)', r'(C\+)', r'(C\-)',
                        r'(D\+)', r'(D\-)', r'(F\+)', r'(F\-)'
                    ]
                    
                    for pattern in specific_patterns:
                        match = re.search(pattern, page_text)
                        if match:
                            grade_found = match.group(1)
                            print(f"📊 Grade específica encontrada: {grade_found}")
                            break
                
                if grade_found:
                    dados_dinamicos['player_info']['grade'] = grade_found
                    print(f"📊 GRADE FINAL ENCONTRADA: {grade_found}")
                else:
                    print("⚠️ Grade não identificada")
                    print(f"🔍 Todos os matches encontrados: {all_matches[:10]}")
                    # Mostrar uma amostra do texto para debug
                    sample_text = page_text[:1000].replace('\n', ' ')
                    print(f"🔍 Amostra do texto: {sample_text[:200]}...")
                    
            except Exception as e:
                print(f"⚠️ Erro ao capturar grade: {e}")
            
            # 3. CAPTURAR TIPO DE JOGADOR (qualquer palavra + Player)
            try:
                # Buscar qualquer padrão "XXX Player"
                player_type_match = re.search(r'([A-Za-z]+\s+Player)', page_text)
                all_player_matches = re.findall(r'([A-Za-z]+\s+Player)', page_text)
                print(f"🔍 DEBUG TIPO - Padrões 'XXX Player' encontrados: {all_player_matches}")
                
                if player_type_match:
                    dados_dinamicos['player_info']['player_type'] = player_type_match.group(1)
                    print(f"🎯 TIPO ENCONTRADO: {player_type_match.group(1)}")
                else:
                    print("⚠️ Tipo de jogador não identificado")
            except Exception as e:
                print(f"⚠️ Erro ao capturar tipo: {e}")
            
            # 4. CAPTURAR RANK (qualquer palavra que pareça um rank)
            try:
                # Buscar padrões comuns de rank
                rank_patterns = [
                    r'Current Rank[:\s]*([A-Za-z]+)',
                    r'Rank[:\s]*([A-Za-z]+)',
                    r'\b(Elite|Mestre|Master|Diamante|Diamond|Platina|Platinum|Ouro|Gold|Prata|Silver|Bronze)\b'
                ]
                
                rank_found = None
                print(f"🔍 DEBUG RANK - Padrões buscados:")
                for pattern in rank_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    print(f"   Padrão '{pattern}': {matches}")
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        rank_found = match.group(1)
                        print(f"🏆 RANK ENCONTRADO: {rank_found}")
                        break
                
                if rank_found:
                    dados_dinamicos['player_info']['rank'] = rank_found
                else:
                    print("⚠️ Rank não identificado")
                    
            except Exception as e:
                print(f"⚠️ Erro ao capturar rank: {e}")
            
            # 5. CAPTURAR VALORES NUMÉRICOS (playing style, stats, etc.)
            try:
                # Capturar qualquer valor X/100 que apareça
                valores_100 = re.findall(r'(\d+)/100', page_text)
                print(f"🔍 DEBUG VALORES /100 - Encontrados: {valores_100}")
                
                if valores_100:
                    # Atribuir aos primeiros 6 valores como playing style
                    categories = ['attack', 'playmaking', 'finishing', 'defense', 'goalkeeper', 'impact']
                    for i, value in enumerate(valores_100[:6]):
                        if i < len(categories):
                            dados_dinamicos['playing_style_analysis'][categories[i]] = int(value)
                            print(f"🎮 {categories[i].title()}: {value}/100")
                        else:
                            # Valores extras vão para stats extras
                            dados_dinamicos['page_stats'][f'extra_stat_{i-5}'] = int(value)
                            print(f"📊 Extra Stat {i-5}: {value}/100")
                
                # Capturar valores percentuais adicionais
                percentuais = re.findall(r'(\d+(?:\.\d+)?)%', page_text)
                print(f"🔍 DEBUG PERCENTUAIS - Encontrados: {percentuais[:10]}")  # Primeiros 10
                
                if percentuais:
                    for i, perc in enumerate(percentuais[:5]):  # Primeiros 5 percentuais
                        dados_dinamicos['page_stats'][f'percent_{i+1}'] = float(perc)
                        print(f"📊 Percent {i+1}: {perc}%")
                
                # Capturar números grandes (com k, mil, etc.)
                numeros_grandes = re.findall(r'(\d+\.?\d*k|\d{4,})', page_text)
                print(f"🔍 DEBUG NÚMEROS GRANDES - Encontrados: {numeros_grandes[:10]}")  # Primeiros 10
                
                if numeros_grandes:
                    for i, num in enumerate(numeros_grandes[:5]):  # Primeiros 5 números grandes
                        dados_dinamicos['page_stats'][f'big_number_{i+1}'] = num
                        print(f"🔢 Número {i+1}: {num}")
                            
            except Exception as e:
                print(f"⚠️ Erro ao capturar valores: {e}")
            
            # 6. CAPTURAR ELEMENTOS DE TEXTO ADICIONAIS
            try:
                # Capturar todo texto útil em elementos pequenos
                elements_text = []
                
                # Procurar por elementos pequenos que podem conter informações úteis
                body_text_lines = page_text.split('\n')
                for line in body_text_lines:
                    line = line.strip()
                    # Capturar linhas pequenas e úteis (pode ser stats, nomes, etc.)
                    if (2 <= len(line) <= 50 and 
                        not line.startswith('http') and 
                        not line.isdigit() and
                        'javascript' not in line.lower()):
                        elements_text.append(line)
                
                # Salvar alguns elementos de texto para debug
                dados_dinamicos['raw_elements']['text_elements'] = elements_text[:20]  # Primeiros 20
                print(f"📝 ELEMENTOS DE TEXTO CAPTURADOS ({len(elements_text[:20])}):")
                for i, elemento in enumerate(elements_text[:10]):  # Mostrar primeiros 10
                    print(f"   {i+1}. {elemento}")
                if len(elements_text) > 10:
                    print(f"   ... e mais {len(elements_text) - 10} elementos")
                    
            except Exception as e:
                print(f"⚠️ Erro ao capturar elementos extras: {e}")
            
            await context.close()
            await browser.close()
            
            # LOG FINAL - RESUMO DE TUDO QUE FOI CAPTURADO
            print("=" * 60)
            print("📋 RESUMO FINAL DO SCRAPING:")
            print("=" * 60)
            print(f"🎯 Steam ID: {steam_id}")
            print(f"👤 Nome: {dados_dinamicos['player_info']['display_name']}")
            print(f"📊 Grade: {dados_dinamicos['player_info']['grade']}")
            print(f"🎯 Tipo: {dados_dinamicos['player_info']['player_type']}")
            print(f"🏆 Rank: {dados_dinamicos['player_info']['rank']}")
            print(f"🎮 Playing Style: {dados_dinamicos['playing_style_analysis']}")
            print(f"📊 Stats: {dados_dinamicos['page_stats']}")
            print(f"📝 Elementos: {len(dados_dinamicos['raw_elements']['text_elements'])} capturados")
            print("=" * 60)
            print("✅ Scraping dinâmico concluído com sucesso!")
            
            return dados_dinamicos
            
        except Exception as e:
            if 'context' in locals():
                await context.close()
            if browser:
                await browser.close()
            print(f"❌ Erro no scraping dinâmico: {e}")
            print("🔍 DEBUG ERRO - Tentando capturar conteúdo antes do erro...")
            try:
                if 'page_text' in locals() and page_text:
                    print(f"📄 Conteúdo parcial capturado: {page_text[:300]}...")
            except:
                print("⚠️ Não foi possível mostrar conteúdo parcial")
            
            return {
                'steam_id': steam_id,
                'url': url,
                'error': str(e),
                'method': 'playwright_dynamic',
                'status': 'error',
                'captured_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }

def fazer_scraping_dinamico_sync(steam_id):
    """
    Versão síncrona para integrar com o Flask
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resultado = loop.run_until_complete(scraping_dinamico_rematch(steam_id))
        loop.close()
        return resultado
    except Exception as e:
        return {
            'steam_id': steam_id,
            'error': f'Erro no loop assíncrono: {e}',
            'method': 'playwright_dynamic',
            'status': 'error'
        } 