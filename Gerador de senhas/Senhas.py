import random
import string

def gerar_senha_forte(palavra_base):
    # Substitui espaços por caracteres especiais aleatórios
    caracteres_especiais = '!@#$%&*_-+='
    palavra_processada = ''
    for char in palavra_base:
        if char == ' ':
            palavra_processada += random.choice(caracteres_especiais)
        else:
            palavra_processada += char
    
    # Converte a palavra processada para uma lista de caracteres
    senha = list(palavra_processada)
    
    # Adiciona números aleatórios
    numeros = ''.join(random.choices(string.digits, k=2))
    senha.extend(numeros)
    
    # Adiciona caracteres especiais adicionais
    especiais = ''.join(random.choices(caracteres_especiais, k=2))
    senha.extend(especiais)
    
    # Alterna aleatoriamente entre maiúsculas e minúsculas
    for i in range(len(senha)):
        if senha[i].isalpha() and random.choice([True, False]):
            senha[i] = senha[i].upper()
    
    # Embaralha a senha final
    random.shuffle(senha)
    
    return ''.join(senha)

# Recebe a palavra ou frase do usuário
palavra = input("Digite uma palavra ou frase para base da senha: ")

# Gera e mostra a senha
senha_forte = gerar_senha_forte(palavra)
print(f"\nSua senha forte é: {senha_forte}")
