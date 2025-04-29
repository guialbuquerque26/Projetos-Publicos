import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
from itertools import combinations
from collections import defaultdict

def converter_numero_br(valor_str):
    """Converte valores no formato brasileiro para centavos (inteiro)"""
    try:
        valor_str = valor_str.strip()
        
        # Separa parte inteira e decimal
        if ',' in valor_str:
            inteiro_str, decimal_str = valor_str.split(',', 1)
        else:
            inteiro_str = valor_str
            decimal_str = '00'

        # Remove pontos de milhar e converte para inteiro
        inteiro = int(inteiro_str.replace('.', '')) if inteiro_str else 0
        
        # Completa decimal com zeros e limita a 2 dígitos
        decimal = decimal_str.ljust(2, '0')[:2]
        
        return inteiro * 100 + int(decimal)
    except:
        return None

def processar_entrada(entrada):
    """Extrai números usando regex aprimorada"""
    padrao = r'\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}'
    return [converter_numero_br(n) for n in re.findall(padrao, entrada) if converter_numero_br(n) is not None]

def encontrar_combinacao_exata(numeros, alvo):
    """Busca eficiente usando PD para encontrar combinação exata"""
    dp = defaultdict(list)
    dp[0] = []
    
    for num in numeros:
        for soma in list(dp.keys()):
            nova_soma = soma + num
            if nova_soma == alvo:
                return dp[soma] + [num]
            if nova_soma < alvo and nova_soma not in dp:
                dp[nova_soma] = dp[soma] + [num]
    
    return None

def encontrar_melhor_aproximacao(numeros, alvo):
    """Encontra a melhor combinação usando PD"""
    dp = defaultdict(list)
    dp[0] = []
    melhor_diff = float('inf')
    melhor_comb = []
    
    for num in sorted(numeros, reverse=True):
        for soma in list(dp.keys()):
            nova_soma = soma + num
            nova_diff = abs(nova_soma - alvo)
            
            if nova_soma not in dp or len(dp[soma]) + 1 < len(dp[nova_soma]):
                dp[nova_soma] = dp[soma] + [num]
                
                if nova_diff < melhor_diff:
                    melhor_diff = nova_diff
                    melhor_comb = dp[nova_soma]
                    
                if nova_diff == 0:
                    return melhor_comb
                    
    return melhor_comb

def formatar_br(centavos):
    """Formata centavos para formato brasileiro"""
    return f"R${centavos // 100:,.0f},{centavos % 100:02d}".replace(',', '@').replace('.', ',').replace('@', '.')

class SomaInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Encontrador de Combinações de Valores")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Configuração do tema
        self.root.configure(bg="#f0f0f0")
        
        # Frame principal
        main_frame = tk.Frame(root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Valor alvo
        tk.Label(main_frame, text="Valor alvo:", bg="#f0f0f0", font=("Arial", 12)).grid(row=0, column=0, sticky="w", pady=5)
        self.valor_alvo_entry = tk.Entry(main_frame, font=("Arial", 12), width=20)
        self.valor_alvo_entry.grid(row=0, column=1, sticky="w", pady=5)
        self.valor_alvo_entry.insert(0, "1.234,56")
        
        # Área de texto para valores
        tk.Label(main_frame, text="Cole/insira os valores (formato brasileiro):", bg="#f0f0f0", font=("Arial", 12)).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        
        self.valores_text = scrolledtext.ScrolledText(main_frame, width=60, height=15, font=("Arial", 11))
        self.valores_text.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5)
        
        # Botão de processar
        self.processar_btn = tk.Button(main_frame, text="Processar", command=self.iniciar_processamento, 
                                        bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), 
                                        width=15, height=2)
        self.processar_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Área de resultados
        tk.Label(main_frame, text="Resultados:", bg="#f0f0f0", font=("Arial", 12)).grid(row=4, column=0, sticky="w", pady=5)
        
        self.resultado_text = scrolledtext.ScrolledText(main_frame, width=60, height=10, font=("Arial", 11))
        self.resultado_text.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=5)
        
        # Configurar redimensionamento
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Frame de loading overlay
        self.loading_frame = tk.Frame(root, bg="white")
        self.loading_label = tk.Label(self.loading_frame, text="Processando...", font=("Arial", 16, "bold"), bg="white")
        self.loading_bar = tk.Canvas(self.loading_frame, width=300, height=20, bg="white", highlightthickness=0)
        
        # Variável para controlar a animação
        self.animacao_ativa = False
    
    def mostrar_loading(self):
        """Exibe a tela de loading"""
        self.loading_frame.place(relx=0.5, rely=0.5, anchor="center", width=400, height=200)
        self.loading_label.pack(pady=20)
        self.loading_bar.pack(pady=10)
        
        # Inicia a animação da barra de progresso
        self.animacao_ativa = True
        self.animar_loading(0)
        
    def esconder_loading(self):
        """Esconde a tela de loading"""
        self.animacao_ativa = False
        self.loading_frame.place_forget()
        
    def animar_loading(self, posicao):
        """Anima a barra de progresso"""
        if not self.animacao_ativa:
            return
            
        # Limpar canvas e desenhar retângulo
        self.loading_bar.delete("all")
        self.loading_bar.create_rectangle(posicao, 0, posicao+60, 20, fill="#4CAF50", outline="")
        
        # Mover a barra
        nova_posicao = (posicao + 5) % 300
        
        # Agendar próxima animação
        self.root.after(50, self.animar_loading, nova_posicao)
    
    def iniciar_processamento(self):
        """Inicia o processamento em uma thread separada"""
        self.mostrar_loading()
        self.processar_btn.config(state=tk.DISABLED)
        
        # Iniciar thread de processamento
        threading.Thread(target=self.processar_thread, daemon=True).start()
    
    def processar_thread(self):
        """Executa o processamento em uma thread separada"""
        try:
            # Limpar resultados anteriores
            self.resultado_text.delete(1.0, tk.END)
            
            # Obter valor alvo
            valor_alvo_str = self.valor_alvo_entry.get().strip()
            alvo = converter_numero_br(valor_alvo_str)
            
            if not alvo or alvo <= 0:
                self.finalizar_processamento("Valor alvo inválido!")
                return
            
            # Obter valores de entrada
            entrada = self.valores_text.get(1.0, tk.END)
            numeros = processar_entrada(entrada)
            
            if not numeros:
                self.finalizar_processamento("Nenhum número válido encontrado!")
                return
            
            resultado = f"{len(numeros)} números válidos processados\n\n"
            
            # Busca por combinação exata
            combinacao_exata = encontrar_combinacao_exata(numeros, alvo)
            if combinacao_exata:
                soma = sum(combinacao_exata)
                resultado += f"Combinação exata encontrada:\n{[formatar_br(n) for n in combinacao_exata]}\n\n"
                resultado += f"Soma total: {formatar_br(soma)}"
                self.finalizar_processamento(resultado)
                return
            
            # Busca por melhor aproximação
            melhor_comb = encontrar_melhor_aproximacao(numeros, alvo)
            if melhor_comb:
                soma = sum(melhor_comb)
                diff = abs(soma - alvo)
                resultado += f"Melhor combinação aproximada:\n{[formatar_br(n) for n in melhor_comb]}\n\n"
                resultado += f"Soma total: {formatar_br(soma)}\n"
                resultado += f"Diferença: {formatar_br(diff)}"
                self.finalizar_processamento(resultado)
            else:
                self.finalizar_processamento("Nenhuma combinação encontrada!")
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", str(e)))
            self.finalizar_processamento("")
    
    def finalizar_processamento(self, resultado):
        """Finaliza o processamento e exibe resultados"""
        def concluir():
            if resultado:
                self.resultado_text.insert(tk.END, resultado)
            self.esconder_loading()
            self.processar_btn.config(state=tk.NORMAL)
        
        # Programar a atualização da interface na thread principal
        self.root.after(500, concluir)  # Atraso de 500ms para melhor UX
    
    def processar(self):
        """Método mantido para compatibilidade (não utilizado)"""
        pass
            
def main():
    root = tk.Tk()
    app = SomaInterface(root)
    root.mainloop()

if __name__ == "__main__":
    main()