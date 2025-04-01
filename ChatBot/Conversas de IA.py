import cohere
import google.generativeai as genai
import time
import os

# Configuração do Gemini
genai.configure(api_key='AIzaSyCcPpGKAqSkQg877obo93vLSTy6qfibhM4')

# Configuração do Cohere
co = cohere.Client('WR3YgBXki6mQHlO24JZyr5x1bGeVUwSCfeNC0HqI')

def gemini_response(prompt):
    # Adiciona delay de 10 segundos antes da requisição
    time.sleep(1)
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    return response.text

def cohere_response(prompt):
    try:
        response = co.generate(
            model='command',
            prompt=prompt,
            max_tokens=200,
            temperature=0.7
        )
        return response.generations[0].text
    except Exception as e:
        print(f"Erro ao processar resposta: {e}")
        return "Erro ao gerar resposta."

def salvar_conversa(conversa, tema):
    try:
        # Remove caracteres inválidos do nome da pasta
        caracteres_invalidos = ['?', ',', ':', ';', '!', '*', '/', '\\', '|', '"', '<', '>']
        for char in caracteres_invalidos:
            tema = tema.replace(char, '')
        
        # Cria a pasta com o nome do tema
        pasta = tema.replace(" ", "_").lower()
        os.makedirs(pasta, exist_ok=True)
        
        # Cria o prompt para o Gemini gerar um resumo elaborado
        prompt = f"""
        Com base na seguinte conversa, crie um relatório detalhado em português com:
        1. Introdução sobre o tema discutido
        2. Trechos importantes da conversa com suas análises
        3. Principais pontos destacados
        4. Conclusões e reflexões finais

        Formate o texto com títulos e subtítulos. Use markdown para destacar trechos importantes.

        Conversa:
        {conversa}
        """
        
        # Gera o resumo com o Gemini
        resumo = gemini_response(prompt)
        
        # Salva o resumo em um arquivo TXT dentro da pasta
        caminho_arquivo = os.path.join(pasta, "resumo_conversa.txt")
        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
            arquivo.write(resumo)
        
        print(f"\nRelatório detalhado da conversa salvo em '{caminho_arquivo}'")
    except Exception as e:
        print(f"Erro ao salvar a conversa: {e}")

def conversa_entre_ias(max_turns=5):
    # Solicita o tema da conversa ao usuário
    tema = input("Digite o tema da conversa: ")
    prompt = f"Vamos discutir sobre: {tema}"
    turno = 0
    conversa_completa = ""
    
    while turno < max_turns:
        print(f"\nTurno {turno + 1}:")
        
        # Gemini responde
        resposta_gemini = gemini_response(prompt)
        print(f"Gemini: {resposta_gemini}")
        conversa_completa += f"Gemini: {resposta_gemini}\n"
        
        # Adiciona um delay de 20 segundos
        time.sleep(1)
        
        # Cohere responde
        resposta_cohere = cohere_response(resposta_gemini)
        print(f"Cohere: {resposta_cohere}")
        conversa_completa += f"Cohere: {resposta_cohere}\n"
        
        # Atualiza o prompt para a próxima iteração
        prompt = resposta_cohere
        turno += 1
    
    # Salva a conversa ao final
    salvar_conversa(conversa_completa, tema)

# Inicia a conversa
conversa_entre_ias(max_turns=5)
