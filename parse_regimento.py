# -*- coding: utf-8 -*-
import re

def parse_regimento(filepath):
    """Lê um arquivo de texto do regimento e extrai os artigos."""
    articles = []
    current_article_text = []
    current_article_title = None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: # Pular linhas em branco
                    continue

                # Tenta encontrar um título de artigo (ex: "Artigo 1: ..." ou "Artigo X ...")
                match = re.match(r"^(Artigo \d+[:\s])(.*)", line, re.IGNORECASE)
                if match:
                    # Se já havia um artigo sendo processado, salva-o
                    if current_article_title and current_article_text:
                        articles.append({
                            "title": current_article_title.strip(),
                            "text": " ".join(current_article_text).strip()
                        })
                        current_article_text = []
                    
                    current_article_title = match.group(1).strip()
                    # O texto que vem depois do título na mesma linha já faz parte do corpo do artigo
                    initial_text = match.group(2).strip()
                    if initial_text:
                        current_article_text.append(initial_text)
                elif current_article_title:
                    # Se não é um novo título de artigo, mas estamos dentro de um artigo, anexa a linha
                    # Evita adicionar títulos de Capítulos como parte do texto do artigo
                    if not re.match(r"^(Capítulo \d+[:\s])", line, re.IGNORECASE):
                        current_article_text.append(line)
            
            # Salva o último artigo processado após o loop
            if current_article_title and current_article_text:
                articles.append({
                    "title": current_article_title.strip(),
                    "text": " ".join(current_article_text).strip()
                })

    except FileNotFoundError:
        print(f"Erro: Arquivo {filepath} não encontrado.")
        return []
    except Exception as e:
        print(f"Ocorreu um erro ao processar o arquivo: {e}")
        return []
        
    return articles

if __name__ == "__main__":
    parsed_articles = parse_regimento("/home/ubuntu/regimento_exemplo.txt")
    if parsed_articles:
        print("Artigos extraídos do regimento:")
        for i, article in enumerate(parsed_articles):
            print(f"\n--- Artigo {i+1} ---")
            print(f"Título: {article['title']}")
            print(f"Texto: {article['text']}")
    else:
        print("Nenhum artigo foi extraído ou houve um erro.")

