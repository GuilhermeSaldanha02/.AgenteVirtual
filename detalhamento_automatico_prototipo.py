# -*- coding: utf-8 -*-
import re
from parse_regimento import parse_regimento # Importa a função do script anterior

# Carrega os artigos do regimento uma vez
ARTIGOS_REGIMENTO = parse_regimento("/home/ubuntu/regimento_exemplo.txt")

def encontrar_artigo_relevante(palavras_chave_str):
    """Encontra artigos relevantes com base em palavras-chave."""
    if not ARTIGOS_REGIMENTO:
        return None, "Regimento não carregado ou vazio."

    palavras_chave = [palavra.strip().lower() for palavra in palavras_chave_str.split(",")]
    if not palavras_chave:
        return None, "Nenhuma palavra-chave fornecida."

    artigos_encontrados = []

    for i, artigo in enumerate(ARTIGOS_REGIMENTO):
        texto_artigo_lower = artigo["text"].lower()
        titulo_artigo_lower = artigo["title"].lower()
        score = 0
        termos_encontrados_no_artigo = []

        for palavra_chave in palavras_chave:
            if palavra_chave in texto_artigo_lower:
                score += texto_artigo_lower.count(palavra_chave)
                termos_encontrados_no_artigo.append(palavra_chave)
            if palavra_chave in titulo_artigo_lower:
                score += titulo_artigo_lower.count(palavra_chave) * 2 # Peso maior para título
                termos_encontrados_no_artigo.append(palavra_chave)
        
        if score > 0:
            artigos_encontrados.append({
                "index": i,
                "titulo_original": artigo["title"],
                "texto_original": artigo["text"],
                "score": score,
                "termos_encontrados": list(set(termos_encontrados_no_artigo))
            })
    
    if not artigos_encontrados:
        return None, "Nenhum artigo relevante encontrado para as palavras-chave."

    # Ordena os artigos encontrados pelo score (maior primeiro)
    artigos_encontrados.sort(key=lambda x: x["score"], reverse=True)
    return artigos_encontrados[0], None # Retorna o mais relevante

def gerar_detalhamento_ocorrencia(palavras_chave_str, unidade="Ainda não especificada"):
    """Tenta detalhar uma ocorrência com base em palavras-chave e no regimento."""
    
    artigo_relevante, erro = encontrar_artigo_relevante(palavras_chave_str)

    if erro:
        return {"sugestao_titulo": f"Ocorrência referente a: {palavras_chave_str}",
                "sugestao_descricao": f"Detalhes da ocorrência relacionada a \"{palavras_chave_str}\" na unidade {unidade}. {erro}",
                "artigo_regimento_sugerido": "N/A",
                "texto_artigo_sugerido": "N/A"}

    sugestao_titulo = f"Possível infração ao {artigo_relevante['titulo_original']}: {palavras_chave_str}"
    
    descricao_base = f"Foi reportada uma situação na unidade {unidade} que parece estar relacionada com as palavras-chave: {', '.join(artigo_relevante['termos_encontrados'])}. "
    descricao_base += f"Isso pode constituir uma infração ao {artigo_relevante['titulo_original']} do regimento interno, que estabelece: \"{artigo_relevante['texto_original']}\". "
    descricao_base += "Solicitamos verificação e providências."

    # Tentar extrair uma infração específica do texto do artigo (exemplo simples)
    classificacao_infracao = "Não classificada"
    if "silêncio" in " ".join(artigo_relevante['termos_encontrados']):
        classificacao_infracao = "Perturbação do silêncio"
    elif "lixo" in " ".join(artigo_relevante['termos_encontrados']):
        classificacao_infracao = "Descarte irregular de lixo"

    sugestao_descricao_completa = f"**Classificação Preliminar da Infração:** {classificacao_infracao}\n\n"
    sugestao_descricao_completa += f"**Unidade Envolvida:** {unidade}\n\n"
    sugestao_descricao_completa += f"**Palavras-chave da Ocorrência:** {palavras_chave_str}\n\n"
    sugestao_descricao_completa += f"**Descrição Sugerida:**\n{descricao_base}\n\n"
    sugestao_descricao_completa += f"**Artigo do Regimento Interno Potencialmente Infringido:** {artigo_relevante['titulo_original']}\n"
    sugestao_descricao_completa += f"**Texto do Artigo:** {artigo_relevante['texto_original']}"

    return {"sugestao_titulo": sugestao_titulo,
            "sugestao_descricao": sugestao_descricao_completa, # Usar a descrição mais completa
            "classificacao_infracao_sugerida": classificacao_infracao,
            "artigo_regimento_sugerido": artigo_relevante['titulo_original'],
            "texto_artigo_sugerido": artigo_relevante['texto_original']}

if __name__ == "__main__":
    # Testes
    palavras_teste_1 = "barulho, festa, 22h"
    detalhamento_1 = gerar_detalhamento_ocorrencia(palavras_teste_1, unidade="Apto 101")
    print(f"--- Teste 1: Palavras-chave: {palavras_teste_1} ---")
    print(f"Título Sugerido: {detalhamento_1['sugestao_titulo']}")
    print(f"Descrição Sugerida:\n{detalhamento_1['sugestao_descricao']}")
    print(f"Artigo Sugerido: {detalhamento_1['artigo_regimento_sugerido']}")
    print("--- Fim Teste 1 ---\n")

    palavras_teste_2 = "lixo, área comum"
    detalhamento_2 = gerar_detalhamento_ocorrencia(palavras_teste_2, unidade="Bloco B")
    print(f"--- Teste 2: Palavras-chave: {palavras_teste_2} ---")
    print(f"Título Sugerido: {detalhamento_2['sugestao_titulo']}")
    print(f"Descrição Sugerida:\n{detalhamento_2['sugestao_descricao']}")
    print(f"Artigo Sugerido: {detalhamento_2['artigo_regimento_sugerido']}")
    print("--- Fim Teste 2 ---\n")

    palavras_teste_3 = "cachorro solto"
    detalhamento_3 = gerar_detalhamento_ocorrencia(palavras_teste_3, unidade="Playground")
    print(f"--- Teste 3: Palavras-chave: {palavras_teste_3} ---")
    print(f"Título Sugerido: {detalhamento_3['sugestao_titulo']}")
    print(f"Descrição Sugerida:\n{detalhamento_3['sugestao_descricao']}")
    print(f"Artigo Sugerido: {detalhamento_3['artigo_regimento_sugerido']}")
    print("--- Fim Teste 3 ---")

