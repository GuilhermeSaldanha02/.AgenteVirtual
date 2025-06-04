# -*- coding: utf-8 -*-
import os
import json
import google.generativeai as genai
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartSuggestions:
    """Classe para fornecer sugestões inteligentes usando a API Gemini"""

    def __init__(self, processed_dir):
        """
        Inicializa o sistema de sugestões

        Args:
            processed_dir: Diretório onde os documentos processados estão salvos
        """
        self.processed_dir = processed_dir
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None

        if not self.api_key:
            logger.error("Chave da API Gemini (GEMINI_API_KEY) não encontrada nas variáveis de ambiente.")
        else:
            try:
                genai.configure(api_key=self.api_key)
                # Usar um modelo padrão, pode ser ajustado conforme necessidade
                self.model = genai.GenerativeModel("gemini-pro")
                logger.info("API Gemini configurada com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao configurar a API Gemini: {e}")

    def _load_processed_documents(self):
        """Carrega os artigos dos documentos processados."""
        articles_context = ""
        all_articles = {}
        for doc_type in ["regimento", "convencao"]:
            json_path = os.path.join(self.processed_dir, f"{doc_type}_processado.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        doc_data = json.load(f)
                        type_name = "Regimento Interno" if doc_type == "regimento" else "Convenção Condominial"
                        articles = doc_data.get("articles", {})
                        all_articles[doc_type] = articles
                        for num, text in articles.items():
                            articles_context += f"\n---\nFonte: {type_name}\nArtigo: {num}\nTexto: {text}\n---"
                except Exception as e:
                    logger.error(f"Erro ao carregar documento processado {json_path}: {e}")
        return articles_context, all_articles

    def get_suggestions(self, user_input):
        """
        Obtém sugestões (descrição e artigos) da API Gemini.

        Args:
            user_input: Texto fornecido pelo usuário (palavras-chave ou descrição inicial).

        Returns:
            Dicionário com sugestões ou None em caso de erro.
        """
        if not self.model:
            logger.error("Modelo Gemini não inicializado. Verifique a configuração da API Key.")
            return {
                "suggested_description": "Erro: Modelo de IA não configurado.",
                "related_articles": []
            }

        if not user_input:
            return {
                "suggested_description": None,
                "related_articles": []
            }

        articles_context, all_articles_data = self._load_processed_documents()

        if not articles_context:
            logger.warning("Nenhum documento (Regimento/Convenção) processado encontrado para fornecer contexto.")
            # Pode retornar um erro ou tentar sem contexto
            # return {
            #     "suggested_description": "Erro: Documentos do condomínio não encontrados.",
            #     "related_articles": []
            # }
            # Por enquanto, tentaremos sem contexto específico de artigos

        prompt = f"""
        Você é um assistente para administradores de condomínio. Sua tarefa é analisar a entrada do usuário sobre uma ocorrência e, com base no contexto dos artigos do Regimento Interno e Convenção Condominial fornecidos, gerar uma sugestão de descrição para a ocorrência e identificar os 3 artigos mais relevantes.

        Entrada do Usuário (pode ser palavras-chave ou uma descrição inicial):
        {user_input}

        Contexto dos Artigos (Regimento Interno e Convenção Condominial):
        {articles_context if articles_context else 'Nenhum contexto de artigos disponível.'}

        Instruções:
        1. Analise a Entrada do Usuário.
        2. Se o contexto de artigos foi fornecido, identifique até 3 artigos (com número e fonte: Regimento ou Convenção) que sejam mais relevantes para a entrada do usuário. Liste-os em ordem de relevância.
        3. Gere uma sugestão de descrição concisa e profissional para a ocorrência, incorporando a informação da entrada do usuário e fazendo referência ao artigo mais relevante identificado (se houver). A descrição deve terminar com um placeholder como '[Preencher com detalhes específicos...]'.
        4. Retorne o resultado estritamente no seguinte formato JSON, sem nenhum texto adicional antes ou depois:
        {{
          "suggested_description": "(Texto da descrição sugerida aqui)",
          "related_articles": [
            {{
              "doc_type": "(regimento ou convencao)",
              "article_num": "(Número do artigo)",
              "text": "(Texto completo do artigo)",
              "score": (Número de 0 a 100 representando a relevância estimada)
            }},
            // ... (até mais 2 artigos, se relevantes)
          ]
        }}
        Se nenhum artigo relevante for encontrado, retorne uma lista vazia para "related_articles". Se não for possível gerar uma descrição, retorne null para "suggested_description".
        """  # A f-string principal já cobre a formatação das variáveis user_input e articles_context

        try:
            logger.info(f"Enviando prompt para Gemini com entrada: {user_input[:50]}...")
            response = self.model.generate_content(prompt)

            # Tentar extrair o JSON da resposta
            response_text = response.text.strip()
            logger.debug(f"Resposta bruta da API Gemini:\n{response_text}")

            # Limpar possível formatação markdown de bloco de código
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Tentar parsear o JSON
            result_json = json.loads(response_text)
            logger.info("Sugestões recebidas e parseadas com sucesso da API Gemini.")

            # Validar e complementar dados dos artigos, se necessário
            if "related_articles" in result_json and isinstance(result_json["related_articles"], list):
                valid_articles = []
                for article_info in result_json["related_articles"]:
                    doc_type = article_info.get("doc_type")
                    article_num = article_info.get("article_num")
                    # Se o texto não veio na resposta, buscar no nosso JSON processado
                    if doc_type and article_num and not article_info.get("text"):
                        if doc_type in all_articles_data and article_num in all_articles_data[doc_type]:
                            article_info["text"] = all_articles_data[doc_type][article_num]
                    # Garantir que temos os campos essenciais
                    if doc_type and article_num and article_info.get("text"):
                        # Adicionar score padrão se não fornecido pela IA
                        if "score" not in article_info:
                            article_info["score"] = 80  # Score padrão
                        valid_articles.append(article_info)
                result_json["related_articles"] = valid_articles[:3]  # Limitar a 3 artigos
            else:
                result_json["related_articles"] = []  # Garantir que seja uma lista

            return result_json

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da resposta da API Gemini: {e}\nResposta recebida: {response.text}")
            return {
                "suggested_description": "Erro ao processar a resposta da IA.",
                "related_articles": []
            }
        except Exception as e:
            logger.error(f"Erro ao chamar a API Gemini ou processar a resposta: {e}")
            # Tentar obter mais detalhes do erro da resposta, se disponível
            try:
                logger.error(f"Detalhes da resposta (candidates): {response.candidates}")
                logger.error(f"Detalhes da resposta (prompt_feedback): {response.prompt_feedback}")
            except AttributeError:
                pass  # Ignorar se os atributos não existirem
            return {
                "suggested_description": f"Erro ao comunicar com a IA: {e}",
                "related_articles": []
            }

# --- Funções que podem ser mantidas para compatibilidade ou removidas ---
# (As funções search_articles_by_keywords, generate_description_suggestion,
# process_keywords_and_suggest da versão anterior podem ser removidas
# ou mantidas como fallback, se desejado)

# Exemplo de como a API Flask chamaria (adaptar em app.py):
# @app.route("/api/suggestions", methods=["POST"])
# @login_required
# def get_suggestions():
#     data = request.get_json()
#     user_input = data.get("keywords", "") or data.get("description", "")
#     suggestions = smart_suggestions.get_suggestions(user_input)
#     return jsonify(suggestions)