"""
TESTE REMATCH ANALYZER
Testa todas as funcionalidades:
1. APIs do Rematch
2. Scraping dinâmico com Playwright
3. Integração completa
4. Comparação de dados
"""

import sys
import os
import json
import time
import asyncio

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import requisitar_dados, fazer_scraping_dinamico_playwright
from scraping_playwright import scraping_dinamico_rematch, fazer_scraping_dinamico_sync

def print_separator(titulo="", char="=", length=70):
    """Imprime separador formatado"""
    if titulo:
        padding = (length - len(titulo) - 2) // 2
        print(char * padding + f" {titulo} " + char * padding)
    else:
        print(char * length)

def teste_completo_rematch():
    """
    Teste completo do sistema RematchAnalyzer
    """
    print_separator("🚀 TESTE COMPLETO REMATCH ANALYZER", "=")
    print("🎯 Testando: APIs + Scraping Dinâmico + Integração")
    print("⏰ Iniciado em:", time.strftime('%Y-%m-%d %H:%M:%S'))
    print()
    
    # Steam IDs para teste
    steam_ids = {
        "player1": "76561198274751649",  # NSG | wellio
        "player2": "76561198371863048"   # OPB | JadokaDokaDoka
    }
    
    resultados = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'tests': {
            'api_test': {},
            'scraping_test': {},
            'integration_test': {}
        },
        'summary': {}
    }
    
    # ==========================================
    # 1. TESTE DAS APIs
    # ==========================================
    print_separator("📡 TESTE 1: APIs DO REMATCH", "-")
    api_success = 0
    
    for player_name, steam_id in steam_ids.items():
        print(f"\n🔵 Testando API para {player_name} ({steam_id})")
        
        try:
            dados = requisitar_dados(steam_id)
            
            if dados and 'lifetime_stats' in dados:
                player_info = dados.get('player', {})
                stats = dados.get('lifetime_stats', {}).get('All', {})
                
                api_data = {
                    'status': 'success',
                    'player_name': player_info.get('display_name', 'N/A'),
                    'matches': stats.get('matches_played', 0),
                    'goals': stats.get('goals', 0),
                    'wins': stats.get('wins', 0),
                    'mvps': stats.get('mvps', 0),
                    'shots': stats.get('shots', 0),
                    'win_rate': round((stats.get('wins', 0) / max(stats.get('matches_played', 1), 1)) * 100, 1),
                    'shot_accuracy': round((stats.get('goals', 0) / max(stats.get('shots', 1), 1)) * 100, 1)
                }
                
                resultados['tests']['api_test'][player_name] = api_data
                api_success += 1
                
                print(f"   ✅ API funcionando!")
                print(f"   👤 Nome: {api_data['player_name']}")
                print(f"   📊 Partidas: {api_data['matches']}")
                print(f"   ⚽ Gols: {api_data['goals']}")
                print(f"   🏆 Win Rate: {api_data['win_rate']}%")
                print(f"   🎯 Shot Accuracy: {api_data['shot_accuracy']}%")
                
            else:
                resultados['tests']['api_test'][player_name] = {'status': 'failed', 'error': 'Dados não recebidos'}
                print(f"   ❌ API falhou para {player_name}")
                
        except Exception as e:
            resultados['tests']['api_test'][player_name] = {'status': 'error', 'error': str(e)}
            print(f"   ❌ Erro na API: {e}")
    
    print(f"\n📊 Resultado APIs: {api_success}/{len(steam_ids)} sucessos")
    
    # ==========================================
    # 2. TESTE DO SCRAPING DINÂMICO
    # ==========================================
    print_separator("🎭 TESTE 2: SCRAPING DINÂMICO COM PLAYWRIGHT", "-")
    scraping_success = 0
    
    for player_name, steam_id in steam_ids.items():
        print(f"\n🔵 Testando scraping dinâmico para {player_name} ({steam_id})")
        
        try:
            dados_scraping = fazer_scraping_dinamico_sync(steam_id)
            
            if dados_scraping and dados_scraping.get('status') == 'success':
                player_info = dados_scraping.get('player_info', {})
                page_stats = dados_scraping.get('page_stats', {})
                playing_style = dados_scraping.get('playing_style_analysis', {})
                
                scraping_data = {
                    'status': 'success',
                    'display_name': player_info.get('display_name'),
                    'grade': player_info.get('grade'),
                    'player_type': player_info.get('player_type'),
                    'rank': player_info.get('rank'),
                    'win_rate_page': page_stats.get('win_rate_percent'),
                    'shot_accuracy_page': page_stats.get('shot_accuracy_percent'),
                    'playing_style': playing_style
                }
                
                resultados['tests']['scraping_test'][player_name] = scraping_data
                scraping_success += 1
                
                print(f"   ✅ Scraping dinâmico funcionando!")
                print(f"   👤 Nome: {scraping_data['display_name']}")
                print(f"   📊 Grade: {scraping_data['grade']}")
                print(f"   🎯 Tipo: {scraping_data['player_type']}")
                print(f"   🏆 Rank: {scraping_data['rank']}")
                print(f"   📈 Win Rate (página): {scraping_data['win_rate_page']}%")
                print(f"   🎯 Shot Accuracy (página): {scraping_data['shot_accuracy_page']}%")
                
                # Mostrar playing style se disponível
                if any(playing_style.values()):
                    print("   📊 Playing Style:")
                    for style, value in playing_style.items():
                        if value is not None:
                            print(f"     {style.title()}: {value}/100")
                            
            else:
                error_msg = dados_scraping.get('error', 'Erro desconhecido') if dados_scraping else 'Sem dados'
                resultados['tests']['scraping_test'][player_name] = {'status': 'failed', 'error': error_msg}
                print(f"   ❌ Scraping falhou: {error_msg}")
                
        except Exception as e:
            resultados['tests']['scraping_test'][player_name] = {'status': 'error', 'error': str(e)}
            print(f"   ❌ Erro no scraping: {e}")
    
    print(f"\n📊 Resultado Scraping: {scraping_success}/{len(steam_ids)} sucessos")
    
    # ==========================================
    # 3. TESTE DE INTEGRAÇÃO
    # ==========================================
    print_separator("🔗 TESTE 3: INTEGRAÇÃO COMPLETA", "-")
    integration_success = 0
    
    for player_name in steam_ids.keys():
        api_data = resultados['tests']['api_test'].get(player_name, {})
        scraping_data = resultados['tests']['scraping_test'].get(player_name, {})
        
        if api_data.get('status') == 'success' and scraping_data.get('status') == 'success':
            print(f"\n🔵 Comparando dados para {player_name}")
            
            # Comparar Win Rate
            api_wr = api_data.get('win_rate')
            scraping_wr = scraping_data.get('win_rate_page')
            
            # Comparar Shot Accuracy
            api_sa = api_data.get('shot_accuracy')
            scraping_sa = scraping_data.get('shot_accuracy_page')
            
            integration_data = {
                'status': 'success',
                'api_vs_scraping': {
                    'win_rate_match': False,
                    'shot_accuracy_match': False,
                    'api_win_rate': api_wr,
                    'scraping_win_rate': scraping_wr,
                    'api_shot_accuracy': api_sa,
                    'scraping_shot_accuracy': scraping_sa
                },
                'unique_scraping_data': {
                    'grade': scraping_data.get('grade'),
                    'player_type': scraping_data.get('player_type'),
                    'rank': scraping_data.get('rank'),
                    'playing_style': scraping_data.get('playing_style')
                }
            }
            
            # Verificar se coincidem
            if api_wr and scraping_wr:
                diff_wr = abs(api_wr - scraping_wr)
                integration_data['api_vs_scraping']['win_rate_match'] = diff_wr < 1
                print(f"   🎯 Win Rate - API: {api_wr}% | Scraping: {scraping_wr}% | Diff: {diff_wr:.1f}%")
                if diff_wr < 1:
                    print("   ✅ Win Rates coincidem!")
                else:
                    print("   ⚠️ Win Rates diferentes")
            
            if api_sa and scraping_sa:
                diff_sa = abs(api_sa - scraping_sa)
                integration_data['api_vs_scraping']['shot_accuracy_match'] = diff_sa < 1
                print(f"   🎯 Shot Accuracy - API: {api_sa}% | Scraping: {scraping_sa}% | Diff: {diff_sa:.1f}%")
                if diff_sa < 1:
                    print("   ✅ Shot Accuracy coincidem!")
                else:
                    print("   ⚠️ Shot Accuracy diferentes")
            
            # Mostrar dados únicos do scraping
            print(f"   📊 Dados únicos do scraping:")
            print(f"     Grade: {scraping_data.get('grade', 'N/A')}")
            print(f"     Tipo: {scraping_data.get('player_type', 'N/A')}")
            print(f"     Rank: {scraping_data.get('rank', 'N/A')}")
            
            resultados['tests']['integration_test'][player_name] = integration_data
            integration_success += 1
            
        else:
            print(f"\n❌ Não foi possível integrar dados para {player_name}")
            resultados['tests']['integration_test'][player_name] = {
                'status': 'failed', 
                'reason': 'API ou Scraping falhou'
            }
    
    print(f"\n📊 Resultado Integração: {integration_success}/{len(steam_ids)} sucessos")
    
    # ==========================================
    # 4. RESUMO FINAL
    # ==========================================
    print_separator("🏆 RESUMO FINAL", "=")
    
    total_tests = len(steam_ids) * 3  # 3 tipos de teste por player
    total_success = api_success + scraping_success + integration_success
    success_rate = (total_success / total_tests) * 100
    
    resultados['summary'] = {
        'total_tests': total_tests,
        'total_success': total_success,
        'success_rate': success_rate,
        'api_success': api_success,
        'scraping_success': scraping_success,
        'integration_success': integration_success
    }
    
    print(f"📈 TAXA DE SUCESSO GERAL: {total_success}/{total_tests} ({success_rate:.0f}%)")
    print(f"📡 APIs: {api_success}/{len(steam_ids)} ({(api_success/len(steam_ids))*100:.0f}%)")
    print(f"🎭 Scraping: {scraping_success}/{len(steam_ids)} ({(scraping_success/len(steam_ids))*100:.0f}%)")
    print(f"🔗 Integração: {integration_success}/{len(steam_ids)} ({(integration_success/len(steam_ids))*100:.0f}%)")
    
    if success_rate >= 80:
        print("\n🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
        print("✨ Funcionalidades disponíveis:")
        print("   📡 APIs do Rematch para estatísticas principais")
        print("   🎭 Scraping dinâmico para dados únicos (Grade, Playing Style)")
        print("   🔗 Integração completa entre API e scraping")
        print("   📊 Dados coincidentes entre fontes")
    elif success_rate >= 60:
        print("\n⚠️ Sistema funcionando com algumas limitações")
    else:
        print("\n❌ Sistema com problemas. Verifique os logs acima.")
    
    # ==========================================
    # 5. SALVAR RESULTADOS
    # ==========================================
    arquivo_resultado = 'teste_resultado_completo.json'
    with open(arquivo_resultado, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados detalhados salvos em: {arquivo_resultado}")
    print(f"⏰ Teste concluído em: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("", "=")

def teste_rapido():
    """
    Teste rápido apenas das APIs (sem Playwright)
    """
    print_separator("⚡ TESTE RÁPIDO - APENAS APIs", "=")
    
    steam_id = "76561198274751649"
    print(f"🎯 Testando API para Steam ID: {steam_id}")
    
    try:
        dados = requisitar_dados(steam_id)
        if dados:
            player_info = dados.get('player', {})
            stats = dados.get('lifetime_stats', {}).get('All', {})
            
            print("✅ API funcionando!")
            print(f"👤 Nome: {player_info.get('display_name', 'N/A')}")
            print(f"📊 Partidas: {stats.get('matches_played', 0)}")
            print(f"⚽ Gols: {stats.get('goals', 0)}")
            print(f"🏆 Vitórias: {stats.get('wins', 0)}")
            print(f"🎖️ MVPs: {stats.get('mvps', 0)}")
        else:
            print("❌ API falhou")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print_separator("", "=")

if __name__ == "__main__":
    print("🚀 TESTE REMATCH ANALYZER")
    print("Escolha uma opção:")
    print("1. Teste completo (APIs + Scraping + Integração)")
    print("2. Teste rápido (apenas APIs)")
    print("3. Executar teste completo automaticamente")
    
    try:
        if len(sys.argv) > 1:
            opcao = sys.argv[1]
        else:
            opcao = input("\nDigite sua opção (1-3): ").strip()
        
        if opcao == "1":
            teste_completo_rematch()
        elif opcao == "2":
            teste_rapido()
        elif opcao == "3":
            teste_completo_rematch()
        else:
            print("Executando teste completo por padrão...")
            teste_completo_rematch()
            
    except KeyboardInterrupt:
        print("\n\n👋 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}") 