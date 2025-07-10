from flask import Flask, render_template, request, redirect, url_for, flash
import requests
import json
import os
import google.generativeai as genai
from io import StringIO
import sys
import webbrowser
import threading
import time
import re
from bs4 import BeautifulSoup
import asyncio

app = Flask(__name__)
app.secret_key = 'rematch_analyzer_secret_key_2025_unique_string_for_sessions'


# Configuração da API Rematch
url_api_resolve = 'https://api.rematchtracker.com/scrap/resolve'
url_api_profile = 'https://api.rematchtracker.com/scrap/profile'
headers = {
    'accept': '*/*',
    'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json',
    'origin': 'https://www.rematchtracker.com',
    'priority': 'u=1, i',
    'referer': 'https://www.rematchtracker.com/',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
}

# Variáveis globais para armazenar dados de scraping
scrappinplayer1 = {}
scrappinplayer2 = {}

def fazer_scraping_dinamico_playwright(steam_id):
    """
    Versão síncrona do scraping dinâmico com Playwright para Flask
    """
    try:
        from scraping_playwright import fazer_scraping_dinamico_sync
        print(f"🎭 Iniciando scraping dinâmico para {steam_id}")
        resultado = fazer_scraping_dinamico_sync(steam_id)
        print(f"✅ Scraping dinâmico concluído: {resultado.get('status', 'N/A')}")
        return resultado
    except ImportError:
        print("⚠️ Playwright não disponível, usando scraping estático")
        return fazer_scraping_player_estatico(steam_id)
    except Exception as e:
        print(f"❌ Erro no scraping dinâmico: {e}")
        return fazer_scraping_player_estatico(steam_id)

def fazer_scraping_player_estatico(steam_id):
    """
    Versão estática do scraping (fallback)
    """
    return fazer_scraping_player(steam_id)

def fazer_scraping_player(steam_id):
    """
    Faz scraping da página do jogador para obter informações dinâmicas
    Tenta capturar dados que só aparecem após JavaScript carregar
    """
    url = f"https://www.rematchtracker.com/player/steam/{steam_id}"
    
    try:
        print(f"🕷️ Fazendo scraping avançado: {url}")
        
        # Headers simples primeiro
        headers_scraping = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'identity',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers_scraping, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            dados_scraping = {
                'steam_id': steam_id,
                'url': url,
                'page_title': soup.title.string if soup.title else None,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'method': 'static_enhanced',
                'status': 'success',
                
                # Informações básicas
                'player_info': {
                    'grade': None,  # A+, B+, etc.
                    'player_type': None,  # Impact Player, etc.
                    'rank': None,  # Elite, etc.
                    'display_name': None
                },
                
                # Análise de estilo de jogo
                'playing_style': {
                    'attack': None,
                    'playmaking': None, 
                    'finishing': None,
                    'defense': None,
                    'goalkeeper': None,
                    'impact': None
                },
                
                # Estatísticas extras
                'additional_stats': {
                    'win_rate_percent': None,
                    'shot_accuracy_percent': None,
                    'steals': None,
                    'tackles': None,
                    'mvp_rate_percent': None
                },
                
                # Elementos encontrados (para debug)
                'elements_found': {},
                'meta_info': {}
            }
            
            # Extrair meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    dados_scraping['meta_info'][name] = content
            
            # Tentar encontrar dados específicos através de padrões
            page_text = soup.get_text()
            
            # Procurar por padrões de grade com melhor captura de modificadores
            grade_patterns = [
                r'([S][+\-])',          # S+, S- explícito
                r'([A-F][+\-])',        # A+, A-, B+, B-, etc. explícito
                r'Grade:\s*([S][+\-]?)',     # Grade: S+
                r'Grade:\s*([A-F][+\-]?)',   # Grade: A+
                r'([S][+\-]?)',         # S, S+, S- geral
                r'([A-F][+\-]?)',       # A, A+, A-, etc. geral
            ]
            
            grade_found = None
            for pattern in grade_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    candidate = match.group(1).upper()
                    # Priorizar grades com modificadores
                    if '+' in candidate or '-' in candidate:
                        grade_found = candidate
                        break
                    elif not grade_found:
                        grade_found = candidate
            
            if grade_found:
                dados_scraping['player_info']['grade'] = grade_found
            
            # Procurar por percentuais
            percentages = re.findall(r'(\d+\.?\d*)%', page_text)
            if percentages:
                # Tentar identificar win rate e shot accuracy
                for perc in percentages:
                    if float(perc) > 50 and float(perc) < 100:  # Provável win rate
                        dados_scraping['additional_stats']['win_rate_percent'] = float(perc)
                        break
            
            # Procurar por números grandes (steals, tackles, etc.)
            large_numbers = re.findall(r'(\d+\.?\d*k)', page_text)
            if large_numbers:
                dados_scraping['additional_stats']['large_numbers_found'] = large_numbers
            
            # Procurar por tipos de jogador
            player_types = ['Impact Player', 'Defensive Player', 'Offensive Player', 'Balanced Player']
            for player_type in player_types:
                if player_type.lower() in page_text.lower():
                    dados_scraping['player_info']['player_type'] = player_type
                    break
            
            # Procurar por ranks
            ranks = ['Elite', 'Expert', 'Advanced', 'Intermediate', 'Beginner']
            for rank in ranks:
                if rank.lower() in page_text.lower():
                    dados_scraping['player_info']['rank'] = rank
                    break
            
            # Capturar elementos específicos por classes conhecidas
            svelte_elements = soup.find_all(attrs={'class': lambda x: x and 'svelte' in ' '.join(x)})
            for i, element in enumerate(svelte_elements[:20]):  # Limitar a 20
                text = element.get_text().strip()
                if text and len(text) < 100:
                    dados_scraping['elements_found'][f'svelte_element_{i}'] = {
                        'text': text,
                        'classes': element.get('class', []),
                        'tag': element.name
                    }
            
            # Verificar se ainda está em loading
            dados_scraping['is_loading'] = 'loading' in page_text.lower()
            dados_scraping['has_dynamic_content'] = 'svelte' in str(soup).lower()
            
            print(f"✅ Scraping avançado concluído para {steam_id}")
            print(f"   Grade encontrada: {dados_scraping['player_info']['grade']}")
            print(f"   Tipo de jogador: {dados_scraping['player_info']['player_type']}")
            print(f"   Rank: {dados_scraping['player_info']['rank']}")
            
            return dados_scraping
            
        else:
            print(f"❌ Erro no scraping: Status {response.status_code}")
            return {
                'error': f'Status {response.status_code}', 
                'steam_id': steam_id, 
                'url': url,
                'status': 'error',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
    except Exception as e:
        print(f"❌ Erro no scraping: {e}")
        return {
            'error': str(e), 
            'steam_id': steam_id, 
            'url': url,
            'status': 'error',
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
}

def calcular_metricas(stats):
    partidas = stats.get('matches_played', 0)
    vitorias = stats.get('wins', 0)
    gols = stats.get('goals', 0)
    chutes = stats.get('shots', 0)
    assistencias = stats.get('assists', 0)
    saves = stats.get('saves', 0)
    interceptacoes = stats.get('intercepted_passes', 0)
    desarmes = stats.get('tackles', 0)
    mvps = stats.get('mvps', 0)

    taxa_vitoria = (vitorias / partidas) * 100 if partidas else 0
    acuracidade = (gols / chutes) * 100 if chutes else 0
    participacao_gols = (gols + assistencias) / partidas if partidas else 0
    mvps_por_partida = mvps / partidas if partidas else 0
    desempenho_defensivo = (saves + interceptacoes + desarmes) / partidas if partidas else 0
    desempenho_ofensivo = (gols + assistencias + chutes) / partidas if partidas else 0

    return {
        'taxa_vitoria': taxa_vitoria,
        'acuracidade': acuracidade,
        'participacao_gols': participacao_gols,
        'mvps_por_partida': mvps_por_partida,
        'desempenho_defensivo': desempenho_defensivo,
        'desempenho_ofensivo': desempenho_ofensivo,
        'partidas': partidas,
        'vitorias': vitorias,
        'gols': gols,
        'chutes': chutes,
        'assistencias': assistencias,
        'saves': saves,
        'interceptacoes': interceptacoes,
        'desarmes': desarmes,
        'mvps': mvps
    }

def processar_dados(dados):
    cardplayer = {}
    stats = dados.get('lifetime_stats', {})
    for modo, valores in stats.items():
        metricas = calcular_metricas(valores)
        cardplayer[modo] = metricas
    return cardplayer

def calcular_resumo_frios(dados):
    stats = dados.get('lifetime_stats', {})
    total_gols = 0
    total_assist = 0
    total_participacoes = 0
    total_partidas = 0
    total_mvps = 0
    total_chutes = 0
    total_saves = 0
    total_intercept = 0
    total_desarmes = 0
    total_vitorias = 0
    
    for modo, valores in stats.items():
        if modo == 'All':
            continue
        total_gols += valores.get('goals', 0)
        total_assist += valores.get('assists', 0)
        total_participacoes += valores.get('goals', 0) + valores.get('assists', 0)
        total_partidas += valores.get('matches_played', 0)
        total_mvps += valores.get('mvps', 0)
        total_chutes += valores.get('shots', 0)
        total_saves += valores.get('saves', 0)
        total_intercept += valores.get('intercepted_passes', 0)
        total_desarmes += valores.get('tackles', 0)
        total_vitorias += valores.get('wins', 0)
    
    acuracia_geral = (total_gols / total_chutes) * 100 if total_chutes else 0
    taxa_vitoria_geral = (total_vitorias / total_partidas) * 100 if total_partidas else 0
    
    return {
        'total_gols': total_gols,
        'total_assist': total_assist,
        'total_participacoes': total_participacoes,
        'total_partidas': total_partidas,
        'total_mvps': total_mvps,
        'total_chutes': total_chutes,
        'acuracia_geral': acuracia_geral,
        'total_acoes_defensivas': total_saves + total_intercept + total_desarmes,
        'total_vitorias': total_vitorias,
        'taxa_vitoria_geral': taxa_vitoria_geral
    }

def extrair_identifier(input_text):
    """
    Extrai o identifier (Steam ID) do link do perfil ou retorna o texto se já for um ID
    """
    # Remove espaços em branco
    input_text = input_text.strip()
    
    # Se já é um número (Steam ID), retorna direto
    if input_text.isdigit():
        return input_text
    
    # Patterns para diferentes formatos de URL do Steam
    patterns = [
        r'steamcommunity\.com/profiles/(\d+)',  # URL direta do perfil
        r'steamcommunity\.com/id/([^/]+)',      # URL com custom ID
        r'rematchtracker\.com.*?/(\d+)',        # URL do Rematch Tracker
        r'(\d{17})',                            # Steam ID de 17 dígitos
    ]
    
    for pattern in patterns:
        match = re.search(pattern, input_text)
        if match:
            return match.group(1)
    
    # Se não encontrou nenhum pattern, retorna o input original
    return input_text

def requisitar_dados(identifier):
    """
    Faz requisições para a nova API do Rematch
    Primeiro resolve o perfil, depois busca os dados
    """
    # Extrai o identifier correto do link ou texto fornecido
    identifier = extrair_identifier(identifier)
    
    # Dados para a primeira requisição (resolve)
    data_resolve = {
        'platform': 'steam',
        'identifier': identifier
    }
    
    # Dados para a segunda requisição (profile) - usa platformId
    data_profile = {
        'platform': 'steam',
        'platformId': identifier
    }
    
    try:
        # Primeira requisição: resolve
        print(f"🔍 Resolvendo perfil para identifier: {identifier}")
        response_resolve = requests.post(url_api_resolve, headers=headers, json=data_resolve, timeout=30)
        
        print(f"Status resolve: {response_resolve.status_code}")
        if response_resolve.status_code != 200:
            print(f"❌ Erro na requisição resolve: {response_resolve.status_code}")
            try:
                error_text = response_resolve.text
                print(f"Resposta de erro: {error_text}")
            except:
                pass
            return None
        
        resolve_data = response_resolve.json()
        print(f"✅ Perfil resolvido com sucesso: {resolve_data}")
        
        # Segunda requisição: buscar dados do perfil
        print(f"📊 Buscando dados do perfil...")
        response_profile = requests.post(url_api_profile, headers=headers, json=data_profile, timeout=30)
        
        print(f"Status profile: {response_profile.status_code}")
        if response_profile.status_code == 200:
            profile_data = response_profile.json()
            print(f"✅ Dados do perfil obtidos com sucesso")
            return profile_data
        else:
            print(f"❌ Erro na requisição profile: {response_profile.status_code}")
            try:
                error_text = response_profile.text
                print(f"Resposta de erro: {error_text}")
            except:
                pass
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout nas requisições")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro nas requisições: {e}")
    return None

def comparar_com_gemini(resumo1, resumo2, atuacao1="", atuacao2="", scraping_data1=None, scraping_data2=None):
    """
    Comparação melhorada entre jogadores usando dados do scraping dinâmico
    """
    try:
        genai.configure(api_key="AIzaSyA_EQv9Fa5-UFge7gu2_Qq_eIBZAei7aWQ")
    except Exception as e:
        return f"Erro ao configurar a API Gemini: {e}"
    
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # Contextos de atuação
    contexto_atuacao1 = ""
    contexto_atuacao2 = ""
    
    if atuacao1.lower() == "geral":
        contexto_atuacao1 = "O Jogador 1 será analisado de forma GERAL, considerando tanto aspectos ofensivos quanto defensivos de forma equilibrada."
    elif atuacao1.lower() == "ofensiva":
        contexto_atuacao1 = "O Jogador 1 atua principalmente na ÁREA OFENSIVA. Dê mais peso para: gols, assistências, participações em gols, chutes e acuracidade."
    elif atuacao1.lower() == "defensiva":
        contexto_atuacao1 = "O Jogador 1 atua principalmente na ÁREA DEFENSIVA. Dê mais peso para: saves, interceptações, desarmes e ações defensivas totais."
    
    if atuacao2.lower() == "geral":
        contexto_atuacao2 = "O Jogador 2 será analisado de forma GERAL, considerando tanto aspectos ofensivos quanto defensivos de forma equilibrada."
    elif atuacao2.lower() == "ofensiva":
        contexto_atuacao2 = "O Jogador 2 atua principalmente na ÁREA OFENSIVA. Dê mais peso para: gols, assistências, participações em gols, chutes e acuracidade."
    elif atuacao2.lower() == "defensiva":
        contexto_atuacao2 = "O Jogador 2 atua principalmente na ÁREA DEFENSIVA. Dê mais peso para: saves, interceptações, desarmes e ações defensivas totais."
    
    # Extrair dados avançados do Jogador 1
    dados_jogador1 = ""
    if scraping_data1 and scraping_data1.get('status') == 'success':
        player_info1 = scraping_data1.get('player_info', {})
        playing_style1 = scraping_data1.get('playing_style_analysis', {})
        
        rank1 = player_info1.get('rank')
        rank_info1 = interpretar_rank_jogador(rank1) if rank1 else None
        
        grade1 = player_info1.get('grade')
        grade_info1 = interpretar_grade_jogador(grade1) if grade1 else None
        
        style_analysis1 = analisar_playing_style(playing_style1)
        
        dados_jogador1 = f"""
JOGADOR 1 - DADOS AVANÇADOS:
Rank: {rank1 or 'N/A'} {f"({rank_info1['descricao']})" if rank_info1 else ""}
Nota: {grade1 or 'N/A'} {f"({grade_info1['classificacao']})" if grade_info1 else ""}
Tipo: {player_info1.get('player_type', 'N/A')}
{style_analysis1}
"""
    
    # Extrair dados avançados do Jogador 2
    dados_jogador2 = ""
    if scraping_data2 and scraping_data2.get('status') == 'success':
        player_info2 = scraping_data2.get('player_info', {})
        playing_style2 = scraping_data2.get('playing_style_analysis', {})
        
        rank2 = player_info2.get('rank')
        rank_info2 = interpretar_rank_jogador(rank2) if rank2 else None
        
        grade2 = player_info2.get('grade')
        grade_info2 = interpretar_grade_jogador(grade2) if grade2 else None
        
        style_analysis2 = analisar_playing_style(playing_style2)
        
        dados_jogador2 = f"""
JOGADOR 2 - DADOS AVANÇADOS:
Rank: {rank2 or 'N/A'} {f"({rank_info2['descricao']})" if rank_info2 else ""}
Nota: {grade2 or 'N/A'} {f"({grade_info2['classificacao']})" if grade_info2 else ""}
Tipo: {player_info2.get('player_type', 'N/A')}
{style_analysis2}
"""
    
    # Comparação de ranks se ambos disponíveis
    comparacao_ranks = ""
    if (scraping_data1 and scraping_data1.get('status') == 'success' and 
        scraping_data2 and scraping_data2.get('status') == 'success'):
        
        rank1 = scraping_data1.get('player_info', {}).get('rank')
        rank2 = scraping_data2.get('player_info', {}).get('rank')
        
        if rank1 and rank2:
            rank_info1 = interpretar_rank_jogador(rank1)
            rank_info2 = interpretar_rank_jogador(rank2)
            
            if rank_info1['nivel'] > rank_info2['nivel']:
                comparacao_ranks = f"🏆 VANTAGEM RANK: Jogador 1 ({rank1}) tem rank superior ao Jogador 2 ({rank2})"
            elif rank_info2['nivel'] > rank_info1['nivel']:
                comparacao_ranks = f"🏆 VANTAGEM RANK: Jogador 2 ({rank2}) tem rank superior ao Jogador 1 ({rank1})"
            else:
                comparacao_ranks = f"⚖️ RANKS EQUIVALENTES: Ambos jogadores estão no mesmo rank ({rank1})"
    
    prompt = f"""CONTEXTO: Análise comparativa detalhada de jogadores do REMATCH (jogo de futebol online).

ÁREAS DE ATUAÇÃO:
{contexto_atuacao1}
{contexto_atuacao2}

{dados_jogador1}

{dados_jogador2}

{comparacao_ranks}

INSTRUÇÕES ESPECÍFICAS:
- Compare os RANKS para determinar experiência e habilidade geral
- Compare as NOTAS DE CLASSIFICAÇÃO para avaliar desempenho atual
- Compare os PLAYING STYLES para identificar diferenças táticas
- Use os TIPOS DE JOGADOR para entender seus roles preferidos

ANÁLISE COMPARATIVA:

**JOGADOR 1 - PONTOS FORTES:**
[Liste 3-4 pontos principais baseados em rank, nota de classificação e playing style]

**JOGADOR 1 - PONTOS FRACOS:**
[Liste 2-3 pontos baseados nos dados avançados]

**JOGADOR 2 - PONTOS FORTES:**
[Liste 3-4 pontos principais baseados em rank, nota de classificação e playing style]

**JOGADOR 2 - PONTOS FRACOS:**
[Liste 2-3 pontos baseados nos dados avançados]

**COMPARAÇÃO TÉCNICA:**
[Compare ranks, notas de classificação, playing styles e desempenho estatístico]

**COMPARAÇÃO DE PLAYING STYLE:**
[Compare pontos fortes e fracos de cada playing style]

**CONCLUSÃO:**
[Quem é melhor considerando rank, nota de classificação, playing style e estatísticas]

DADOS ESTATÍSTICOS BÁSICOS:
Jogador 1: {resumo1}
Jogador 2: {resumo2}

Responda APENAS com a análise estruturada, sem comentários introdutórios."""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao gerar conteúdo com Gemini: {e}"

def interpretar_rank_jogador(rank):
    """
    Interpreta o rank do jogador e retorna informações contextuais
    """
    ranks_hierarchy = {
        'Elite': {'nivel': 7, 'descricao': 'Elite'},
        'Mestre': {'nivel': 6, 'descricao': 'Mestre'},
        'Diamante': {'nivel': 5, 'descricao': 'Diamante'},
        'Platina': {'nivel': 4, 'descricao': 'Platina'},
        'Ouro': {'nivel': 3, 'descricao': 'Ouro'},
        'Prata': {'nivel': 2, 'descricao': 'Prata'},
        'Bronze': {'nivel': 1, 'descricao': 'Bronze'}
    }
    
    return ranks_hierarchy.get(rank, {'nivel': 0, 'descricao': 'Rank não identificado'})

def interpretar_grade_jogador(grade):
    """
    Interpreta a grade do jogador (S+, S, A+, A, etc.) - Sistema de classificação por notas
    """
    grades_info = {
        'S+': {'nivel': 10, 'classificacao': 'Excepcional S+'},
        'S': {'nivel': 9, 'classificacao': 'Excepcional S'},
        'A+': {'nivel': 8, 'classificacao': 'Excelente A+'},
        'A': {'nivel': 7, 'classificacao': 'Excelente A'},
        'A-': {'nivel': 6, 'classificacao': 'Muito Bom A-'},
        'B+': {'nivel': 5, 'classificacao': 'Bom B+'},
        'B': {'nivel': 4, 'classificacao': 'Bom B'},
        'B-': {'nivel': 3, 'classificacao': 'Regular B-'},
        'C+': {'nivel': 2, 'classificacao': 'Abaixo da Média C+'},
        'C': {'nivel': 1, 'classificacao': 'Abaixo da Média C'},
        'D': {'nivel': 0, 'classificacao': 'Precisa Melhorar D'}
    }
    
    return grades_info.get(grade, {'nivel': 0, 'classificacao': 'Não identificada'})

def analisar_playing_style(playing_style):
    """
    Analisa o playing style e retorna insights
    """
    if not playing_style or not any(playing_style.values()):
        return "Playing style não disponível"
    
    # Encontrar os pontos mais fortes e fracos
    valores_validos = {k: v for k, v in playing_style.items() if v is not None}
    
    if not valores_validos:
        return "Dados de playing style não disponíveis"
    
    ponto_forte = max(valores_validos.items(), key=lambda x: x[1])
    ponto_fraco = min(valores_validos.items(), key=lambda x: x[1])
    
    # Categorizar os valores
    analise = []
    
    for categoria, valor in valores_validos.items():
        if valor >= 70:
            analise.append(f"{categoria.title()}: {valor}/100 (Excelente)")
        elif valor >= 50:
            analise.append(f"{categoria.title()}: {valor}/100 (Bom)")
        elif valor >= 30:
            analise.append(f"{categoria.title()}: {valor}/100 (Regular)")
        else:
            analise.append(f"{categoria.title()}: {valor}/100 (Precisa melhorar)")
    
    return f"""
ANÁLISE DO PLAYING STYLE:
{chr(10).join(analise)}

PONTO MAIS FORTE: {ponto_forte[0].title()} ({ponto_forte[1]}/100)
PONTO MAIS FRACO: {ponto_fraco[0].title()} ({ponto_fraco[1]}/100)
"""

def analisar_jogador_individual_com_ia(resumo, atuacao="", scraping_data=None):
    """
    Análise individual melhorada com dados do scraping dinâmico
    """
    try:
        genai.configure(api_key="AIzaSyA_EQv9Fa5-UFge7gu2_Qq_eIBZAei7aWQ")
    except Exception as e:
        return f"Erro ao configurar a API Gemini: {e}"
    
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    # Contexto de atuação
    contexto_atuacao = ""
    if atuacao.lower() == "geral":
        contexto_atuacao = "Este jogador será analisado de forma GERAL, considerando tanto aspectos ofensivos quanto defensivos de forma equilibrada no futebol."
    elif atuacao.lower() == "ofensiva":
        contexto_atuacao = "Este jogador atua principalmente na ÁREA OFENSIVA no futebol (atacante/meio-campista ofensivo). Foque mais em: gols, assistências, participações em gols, chutes e acuracidade. Ações defensivas são secundárias para esta posição."
    elif atuacao.lower() == "defensiva":
        contexto_atuacao = "Este jogador atua principalmente na ÁREA DEFENSIVA no futebol (zagueiro/volante/goleiro). Foque mais em: saves (defesas), interceptações, desarmes e ações defensivas totais. Gols e assistências são menos esperados para esta posição."
    else:
        contexto_atuacao = "Analise o jogador de forma geral, considerando tanto aspectos ofensivos quanto defensivos no futebol."
    
    # Extrair dados do scraping dinâmico
    dados_dinamicos = ""
    if scraping_data and scraping_data.get('status') == 'success':
        player_info = scraping_data.get('player_info', {})
        playing_style = scraping_data.get('playing_style_analysis', {})
        
        # Interpretar rank
        rank = player_info.get('rank')
        rank_info = interpretar_rank_jogador(rank) if rank else None
        
        # Interpretar grade
        grade = player_info.get('grade')
        grade_info = interpretar_grade_jogador(grade) if grade else None
        
        # Analisar playing style
        style_analysis = analisar_playing_style(playing_style)
        
        dados_dinamicos = f"""
DADOS AVANÇADOS CAPTURADOS:

RANK COMPETITIVO: {rank or 'N/A'}
{f"• {rank_info['descricao']}" if rank_info else ""}

NOTA DE CLASSIFICAÇÃO: {grade or 'N/A'}
{f"• {grade_info['classificacao']}" if grade_info else ""}

TIPO DE JOGADOR: {player_info.get('player_type', 'N/A')}

{style_analysis}
"""
    
    prompt = f"""CONTEXTO: Análise detalhada de jogador do REMATCH (jogo de futebol online).

ÁREA DE ATUAÇÃO:
{contexto_atuacao}

{dados_dinamicos}

INSTRUÇÕES ESPECÍFICAS:
- Use o RANK para contextualizar o nível do jogador
- Use a NOTA DE CLASSIFICAÇÃO para avaliar o desempenho geral
- Use o PLAYING STYLE para identificar pontos fortes e fracos específicos
- Use o TIPO DE JOGADOR para entender seu papel preferido

**RESUMO DO PERFIL:**
[Descrição considerando rank, nota de classificação e playing style]

**PONTOS FORTES:**
[Liste 3-4 pontos principais baseados nos dados avançados]

**PONTOS A MELHORAR:**
[Liste 3-4 áreas baseadas no playing style e nota de classificação]

**RECOMENDAÇÕES:**
[Sugestões específicas baseadas no rank e playing style]

**POTENCIAL DE CRESCIMENTO:**
[Baseado no rank atual e áreas de melhoria]

DADOS ESTATÍSTICOS BÁSICOS:
{resumo}

Responda APENAS com a análise estruturada, sem comentários introdutórios."""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao gerar conteúdo com Gemini: {e}"

def formatar_analise_ia(texto):
    """Formatar texto da análise da IA para melhor exibição"""
    if not texto:
        return ""
    
    # Substituir títulos em negrito
    texto = texto.replace('**RESUMO DO PERFIL:**', '<div class="secao-titulo">📊 RESUMO DO PERFIL</div>')
    texto = texto.replace('**PONTOS FORTES:**', '<div class="secao-titulo">💪 PONTOS FORTES</div>')
    texto = texto.replace('**PONTOS A MELHORAR:**', '<div class="secao-titulo">🔧 PONTOS A MELHORAR</div>')
    texto = texto.replace('**RECOMENDAÇÕES:**', '<div class="secao-titulo">💡 RECOMENDAÇÕES</div>')
    texto = texto.replace('**JOGADOR 1 - PONTOS FORTES:**', '<div class="secao-titulo">🔵 JOGADOR 1 - PONTOS FORTES</div>')
    texto = texto.replace('**JOGADOR 1 - PONTOS FRACOS:**', '<div class="secao-titulo">🔴 JOGADOR 1 - PONTOS FRACOS</div>')
    texto = texto.replace('**JOGADOR 2 - PONTOS FORTES:**', '<div class="secao-titulo">🟢 JOGADOR 2 - PONTOS FORTES</div>')
    texto = texto.replace('**JOGADOR 2 - PONTOS FRACOS:**', '<div class="secao-titulo">🟠 JOGADOR 2 - PONTOS FRACOS</div>')
    texto = texto.replace('**COMPARAÇÃO TÉCNICA:**', '<div class="secao-titulo">⚖️ COMPARAÇÃO TÉCNICA</div>')
    texto = texto.replace('**CONCLUSÃO:**', '<div class="secao-titulo">🏆 CONCLUSÃO</div>')
    
    # Remover outros asteriscos
    texto = texto.replace('**', '')
    
    # Converter quebras de linha
    texto = texto.replace('\n\n', '</p><p>')
    texto = texto.replace('\n', '<br>')
    
    # Envolver em parágrafos
    if not texto.startswith('<div'):
        texto = f'<p>{texto}</p>'
    
    return texto

app.jinja_env.filters['formatar_analise'] = formatar_analise_ia

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jogador_unico')
def jogador_unico():
    return render_template('jogador_unico.html')

@app.route('/duelo')
def duelo():
    return render_template('duelo.html')

@app.route('/analisar_jogador', methods=['POST'])
def analisar_jogador():
    global scrappinplayer1
    
    identifier = request.form['identifier']
    atuacao = request.form.get('atuacao', '')  # Campo opcional para área de atuação
    
    # Extrair Steam ID para scraping
    steam_id = extrair_identifier(identifier)
    
    dados = requisitar_dados(identifier)
    if not dados:
        flash('Erro ao buscar dados do jogador. Verifique o link do perfil.', 'error')
        return redirect(url_for('jogador_unico'))
    
    # Fazer scraping dinâmico da página do jogador
    scrappinplayer1 = fazer_scraping_dinamico_playwright(steam_id)
    
    player_info = dados.get('player', {})
    metricas = processar_dados(dados)
    resumo = calcular_resumo_frios(dados)
    
    # Montar string do resumo para a IA
    resumo_str = f"""Total de gols: {resumo['total_gols']}
Total de assistências: {resumo['total_assist']}
Total de participações em gols: {resumo['total_participacoes']}
Total de partidas: {resumo['total_partidas']}
Total de MVPs: {resumo['total_mvps']}
Total de chutes: {resumo['total_chutes']}
Acuracidade geral: {resumo['acuracia_geral']:.2f}%
Total de ações defensivas: {resumo['total_acoes_defensivas']}
Total de vitórias: {resumo['total_vitorias']}
Taxa de vitória geral: {resumo['taxa_vitoria_geral']:.2f}%"""
    
    # Análise da IA com dados do scraping dinâmico
    analise_ia = analisar_jogador_individual_com_ia(resumo_str, atuacao, scrappinplayer1)
    
    return render_template('resultado_jogador.html', 
                         player_info=player_info, 
                         metricas=metricas, 
                         resumo=resumo,
                         analise_ia=analise_ia,
                         atuacao=atuacao,
                         scraping_data=scrappinplayer1)

@app.route('/analisar_duelo', methods=['POST'])
def analisar_duelo():
    global scrappinplayer1, scrappinplayer2
    
    identifier1 = request.form['identifier1']
    identifier2 = request.form['identifier2']
    atuacao1 = request.form['atuacao1']
    atuacao2 = request.form['atuacao2']
    
    # Extrair Steam IDs para scraping
    steam_id1 = extrair_identifier(identifier1)
    steam_id2 = extrair_identifier(identifier2)
    
    dados1 = requisitar_dados(identifier1)
    dados2 = requisitar_dados(identifier2)
    
    if not dados1 or not dados2:
        flash('Erro ao buscar dados de um ou ambos os jogadores. Verifique os links dos perfis.', 'error')
        return redirect(url_for('duelo'))
    
    # Fazer scraping dinâmico das páginas dos jogadores
    scrappinplayer1 = fazer_scraping_dinamico_playwright(steam_id1)
    scrappinplayer2 = fazer_scraping_dinamico_playwright(steam_id2)
    
    player1_info = dados1.get('player', {})
    player2_info = dados2.get('player', {})
    
    metricas1 = processar_dados(dados1)
    metricas2 = processar_dados(dados2)
    
    resumo1 = calcular_resumo_frios(dados1)
    resumo2 = calcular_resumo_frios(dados2)
    
    # Montar string dos resumos para a IA
    resumo1_str = f"""Total de gols: {resumo1['total_gols']}
Total de assistências: {resumo1['total_assist']}
Total de participações em gols: {resumo1['total_participacoes']}
Total de partidas: {resumo1['total_partidas']}
Total de MVPs: {resumo1['total_mvps']}
Total de chutes: {resumo1['total_chutes']}
Acuracidade geral: {resumo1['acuracia_geral']:.2f}%
Total de ações defensivas: {resumo1['total_acoes_defensivas']}
Total de vitórias: {resumo1['total_vitorias']}
Taxa de vitória geral: {resumo1['taxa_vitoria_geral']:.2f}%"""
    
    resumo2_str = f"""Total de gols: {resumo2['total_gols']}
Total de assistências: {resumo2['total_assist']}
Total de participações em gols: {resumo2['total_participacoes']}
Total de partidas: {resumo2['total_partidas']}
Total de MVPs: {resumo2['total_mvps']}
Total de chutes: {resumo2['total_chutes']}
Acuracidade geral: {resumo2['acuracia_geral']:.2f}%
Total de ações defensivas: {resumo2['total_acoes_defensivas']}
Total de vitórias: {resumo2['total_vitorias']}
Taxa de vitória geral: {resumo2['taxa_vitoria_geral']:.2f}%"""
    
    # Análise comparativa da IA com dados do scraping dinâmico
    analise_ia = comparar_com_gemini(resumo1_str, resumo2_str, atuacao1, atuacao2, scrappinplayer1, scrappinplayer2)
    
    return render_template('resultado_duelo.html',
                         player1_info=player1_info,
                         player2_info=player2_info,
                         metricas1=metricas1,
                         metricas2=metricas2,
                         resumo1=resumo1,
                         resumo2=resumo2,
                         atuacao1=atuacao1,
                         atuacao2=atuacao2,
                         analise_ia=analise_ia,
                         scraping_data1=scrappinplayer1,
                         scraping_data2=scrappinplayer2)

@app.route('/debug/scraping')
def debug_scraping():
    """Rota para visualizar dados de scraping dinâmico coletados"""
    global scrappinplayer1, scrappinplayer2
    
    debug_data = {
        'scrappinplayer1': scrappinplayer1,
        'scrappinplayer2': scrappinplayer2,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Resumo dos dados dinâmicos
    resumo1 = ""
    if scrappinplayer1 and 'player_info' in scrappinplayer1:
        resumo1 = f"""
        <h3>📊 Resumo Player 1:</h3>
        <ul>
            <li><strong>Nome:</strong> {scrappinplayer1.get('player_info', {}).get('display_name', 'N/A')}</li>
            <li><strong>Grade:</strong> {scrappinplayer1.get('player_info', {}).get('grade', 'N/A')}</li>
            <li><strong>Tipo:</strong> {scrappinplayer1.get('player_info', {}).get('player_type', 'N/A')}</li>
            <li><strong>Rank:</strong> {scrappinplayer1.get('player_info', {}).get('rank', 'N/A')}</li>
            <li><strong>Win Rate:</strong> {scrappinplayer1.get('page_stats', {}).get('win_rate_percent', 'N/A')}%</li>
            <li><strong>Shot Accuracy:</strong> {scrappinplayer1.get('page_stats', {}).get('shot_accuracy_percent', 'N/A')}%</li>
        </ul>
        """
    
    resumo2 = ""
    if scrappinplayer2 and 'player_info' in scrappinplayer2:
        resumo2 = f"""
        <h3>📊 Resumo Player 2:</h3>
        <ul>
            <li><strong>Nome:</strong> {scrappinplayer2.get('player_info', {}).get('display_name', 'N/A')}</li>
            <li><strong>Grade:</strong> {scrappinplayer2.get('player_info', {}).get('grade', 'N/A')}</li>
            <li><strong>Tipo:</strong> {scrappinplayer2.get('player_info', {}).get('player_type', 'N/A')}</li>
            <li><strong>Rank:</strong> {scrappinplayer2.get('player_info', {}).get('rank', 'N/A')}</li>
            <li><strong>Win Rate:</strong> {scrappinplayer2.get('page_stats', {}).get('win_rate_percent', 'N/A')}%</li>
            <li><strong>Shot Accuracy:</strong> {scrappinplayer2.get('page_stats', {}).get('shot_accuracy_percent', 'N/A')}%</li>
        </ul>
        """
    
    return f"""
    <html>
    <head>
        <title>Debug - Scraping Dinâmico</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .summary {{ background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>🎭 Dados de Scraping Dinâmico com Playwright</h1>
        <p><strong>Timestamp:</strong> {debug_data['timestamp']}</p>
        
        <div class="summary">
            {resumo1}
            {resumo2}
        </div>
        
        <h2>🔵 Player 1 (scrappinplayer1) - Dados Completos:</h2>
        <pre>{json.dumps(scrappinplayer1, indent=2, ensure_ascii=False)}</pre>
        
        <h2>🟢 Player 2 (scrappinplayer2) - Dados Completos:</h2>
        <pre>{json.dumps(scrappinplayer2, indent=2, ensure_ascii=False)}</pre>
        
        <p><a href="/">← Voltar para o início</a></p>
    </body>
    </html>
    """

@app.route('/fechar')
def fechar_aplicacao():
    """Rota para fechar a aplicação quando executada como EXE"""
    if getattr(sys, 'frozen', False):
        # Está rodando como executável
        def shutdown():
            time.sleep(1)
            os._exit(0)
        
        # Executa o shutdown em uma thread separada
        threading.Thread(target=shutdown).start()
        return "Aplicação fechada. Você pode fechar esta aba."
    else:
        return "Aplicação rodando em modo desenvolvimento. Use Ctrl+C no terminal para fechar."

def abrir_navegador():
    """Abre o navegador após um pequeno delay para garantir que o servidor esteja rodando"""
    # Delay diferente dependendo do modo
    if getattr(sys, 'frozen', False):
        time.sleep(1.5)  # Modo executável
    else:
        time.sleep(2.5)  # Modo desenvolvimento (Flask debug demora mais)
    
    url = "http://127.0.0.1:5000"
    
    try:
        import platform
        sistema = platform.system().lower()
        
        # Tenta abrir no Chrome primeiro
        chrome_path = None
        
        if sistema == "windows":
            # Caminhos comuns do Chrome no Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]
        elif sistema == "darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        else:  # Linux
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break
        
        if chrome_path:
            # Abre no Chrome
            if sistema == "darwin":
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(f'open -a "{chrome_path}"'))
            else:
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
            webbrowser.get('chrome').open(url)
            print(f"🌐 Aplicação aberta no Chrome: {url}")
        else:
            # Se Chrome não encontrado, usa navegador padrão
            webbrowser.open(url)
            print(f"🌐 Aplicação aberta no navegador padrão: {url}")
            
    except Exception as e:
        print(f"⚠️  Não foi possível abrir o navegador automaticamente: {e}")
        print(f"💡 Abra manualmente: {url}")

def iniciar_aplicacao():
    """Inicia a aplicação Flask"""
    print("=" * 60)
    print("🚀 REMATCH ANALYZER - Sistema de Análise de Jogadores")
    print("=" * 60)
    print("📊 Versão: 1.0.0")
    print("🌐 Interface Web: http://127.0.0.1:5000")
    print("🤖 IA: Google Gemini 2.5 Pro")
    print("=" * 60)
    
    # Verifica se está rodando como executável
    if getattr(sys, 'frozen', False):
        # Está rodando como executável
        print("💻 Modo: Aplicação Standalone (EXE)")
        print("🔧 Status: Iniciando servidor web...")
        
        # Inicia thread para abrir navegador
        browser_thread = threading.Thread(target=abrir_navegador)
        browser_thread.daemon = True
        browser_thread.start()
        
        print("⚡ Servidor iniciado! Abrindo navegador...")
        print("💡 Para fechar: use o botão 'Fechar App' na interface web")
        print("⚠️  NÃO FECHE esta janela enquanto usar a aplicação!")
        print("=" * 60)
        
        # Inicia Flask sem debug e sem reloader
        try:
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        except KeyboardInterrupt:
            print("\n👋 Aplicação fechada pelo usuário")
        except Exception as e:
            print(f"\n❌ Erro ao iniciar servidor: {e}")
            input("Pressione Enter para fechar...")
    else:
        # Está rodando como script Python
        print("🐍 Modo: Script Python (Desenvolvimento)")
        print("🔧 Debug: Ativado")
        print("=" * 60)
        
        # Só abre navegador se não for o processo de reload do Flask
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            print("⚡ Servidor iniciado! Abrindo navegador...")
            # Inicia thread para abrir navegador também no modo desenvolvimento
            browser_thread = threading.Thread(target=abrir_navegador)
            browser_thread.daemon = True
            browser_thread.start()
        
        app.run(debug=True)

if __name__ == '__main__':
    iniciar_aplicacao() 