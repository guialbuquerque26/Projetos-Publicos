from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime
import time

app = Flask(__name__)

MOEDAS_DISPONIVEIS = {
    'USD': 'Dólar Americano',
    'BRL': 'Real Brasileiro',
    'EUR': 'Euro',
    'BTC': 'Bitcoin',
    'GBP': 'Libra Esterlina',
    'ARS': 'Peso Argentino',
    'JPY': 'Iene Japonês',
    'CHF': 'Franco Suíço',
    'AUD': 'Dólar Australiano',
    'CNY': 'Yuan Chinês',
    'CAD': 'Dólar Canadense',
    'ETH': 'Ethereum',
    'XRP': 'Ripple',
    'DOGE': 'Dogecoin'
}

def obter_historico_cotacoes(moeda, dias):
    # Ajustar URL baseado no período
    if dias == 1:
        # Para "Hoje" usamos a API de cotação por hora
        url = f"https://economia.awesomeapi.com.br/json/daily/{moeda}/12"  # Últimas 12 horas
    else:
        url = f"https://economia.awesomeapi.com.br/json/daily/{moeda}/{dias}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        dados = response.json()
        
        # Verificar se recebemos uma lista de cotações
        if isinstance(dados, list) and len(dados) > 0:
            print(f"Recebidos {len(dados)} registros históricos")
            return dados
        else:
            print("Erro: Dados recebidos não estão no formato esperado")
            return None
            
    except requests.RequestException as e:
        print(f"Erro ao obter cotações: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro ao processar dados: {e}")
        return None

def calcular_estatisticas(dados):
    if not dados or not isinstance(dados, list):
        return None
    
    try:
        # Ordenar dados do mais recente para o mais antigo
        dados_ordenados = sorted(dados, key=lambda x: int(x['timestamp']), reverse=True)
        
        # Extrair valores de bid (compra)
        valores = [float(item['bid']) for item in dados_ordenados]
        
        # Calcular médias móveis apenas se tivermos dados suficientes
        ma7 = sum(valores[:7]) / min(7, len(valores)) if len(valores) >= 7 else None
        ma21 = sum(valores[:21]) / min(21, len(valores)) if len(valores) >= 21 else None
        ma50 = sum(valores[:50]) / min(50, len(valores)) if len(valores) >= 50 else None
        
        # Preparar dados dos últimos dias/horas
        ultimos_dias = []
        for cotacao in dados_ordenados:
            timestamp = int(cotacao['timestamp'])
            # Ajustar formato da data baseado no período
            if len(dados) <= 12:  # Se for dados de hoje
                data = datetime.fromtimestamp(timestamp).strftime('%H:%M')
            else:
                data = datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')
            
            ultimos_dias.append({
                'data': data,
                'valor': float(cotacao['bid']),
                'variacao': float(cotacao['pctChange']),
                'maxima': float(cotacao['high']),
                'minima': float(cotacao['low'])
            })
        
        # Calcular volatilidade
        volatilidade = ((max(valores) - min(valores)) / min(valores) * 100)
        
        return {
            'média': sum(valores) / len(valores),
            'máxima': max(valores),
            'mínima': min(valores),
            'variação': float(dados_ordenados[0]['pctChange']),
            'ultimos_dias': ultimos_dias,
            'tendencia': 'alta' if valores[0] > valores[-1] else 'baixa',
            'volatilidade': volatilidade,
            'volume': abs(sum([float(item.get('varBid', 0)) for item in dados_ordenados])),
            'variacao_total': ((valores[0] - valores[-1]) / valores[-1] * 100),
            'nome': dados[0].get('name', ''),
            'cotacao_atual': valores[0],
            'timestamp_atual': dados_ordenados[0]['timestamp'],
            'ma7': ma7,
            'ma21': ma21,
            'ma50': ma50,
            'periodo': 'hoje' if len(dados) <= 12 else 'dias'  # Sintaxe correta do Python
        }
    except Exception as e:
        print(f"Erro ao calcular estatísticas: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html', 
                         ultima_atualizacao=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                         atualizacao_automatica=True)

@app.route('/moedas_disponiveis')
def obter_moedas_disponiveis():
    return jsonify(MOEDAS_DISPONIVEIS)

@app.route('/atualizar')
def atualizar():
    timestamp = int(time.time())
    moeda_base = request.args.get('base', 'USD')
    moeda_destino = request.args.get('destino', 'BRL')
    periodo = request.args.get('periodo', '7')
    
    # Validar período
    periodo = int(periodo)
    if periodo not in [1, 7, 15, 30, 60, 90]:
        return jsonify({
            'status': 'error',
            'message': 'Período inválido. Use 1, 7, 15, 30, 60 ou 90 dias.',
            'timestamp': timestamp
        })
    
    # Validar se as moedas existem
    if moeda_base not in MOEDAS_DISPONIVEIS or moeda_destino not in MOEDAS_DISPONIVEIS:
        return jsonify({
            'status': 'error',
            'message': 'Moeda não suportada',
            'timestamp': timestamp
        })
    
    # Validar se não é o mesmo par
    if moeda_base == moeda_destino:
        return jsonify({
            'status': 'error',
            'message': 'As moedas de origem e destino devem ser diferentes',
            'timestamp': timestamp
        })
    
    par_moeda = f"{moeda_base}-{moeda_destino}"
    
    try:
        dados = obter_historico_cotacoes(par_moeda, periodo)
        
        # Log para debug
        if dados:
            print(f"Número de registros recebidos: {len(dados)}")
            print(f"Primeiro registro: {dados[0]}")
            print(f"Último registro: {dados[-1]}")
            
            stats = calcular_estatisticas(dados)
            if stats:
                stats['moeda_simbolo'] = '₿' if 'BTC' in par_moeda else 'R$' if moeda_destino == 'BRL' else '$'
                stats['ultima_atualizacao'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                return jsonify({
                    'status': 'success',
                    'data': stats,
                    'timestamp': timestamp
                })
        
        return jsonify({
            'status': 'error',
            'message': 'Não foi possível obter os dados',
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"Erro na rota /atualizar: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': timestamp
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=True)