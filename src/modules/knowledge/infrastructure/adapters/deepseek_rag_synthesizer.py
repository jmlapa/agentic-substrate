import json
from typing import Any

import httpx

from src.modules.knowledge.domain.interfaces.i_llm_synthesis_service import (
    ILlmSynthesisService,
)
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


class DeepSeekRagSynthesizer(ILlmSynthesisService):
    """
    Adaptador de síntese RAG factual baseado no DeepSeek-V4-Flash via OpenRouter.
    Gera respostas em Markdown densas, concisas e com referências explícitas
    de proveniência a chunks e entidades do grafo.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "google/gemma-4-26b-a4b-it",
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.1,
        max_tokens: int = 800,
        http_client: httpx.AsyncClient | None = None,
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = http_client
        self._app_title = app_title
        self._app_referer = app_referer

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=45.0)

    def _build_context(self, search_results: list[HybridSearchResult]) -> str:
        sections: list[str] = []
        for i, res in enumerate(search_results, 1):
            source_info = f"Chunk ID: {res.parent_chunk_id} | Seção: {res.header_path or 'Geral'}"
            meta = f"Score: {res.relevance_score:.4f}"
            content = res.parent_content.strip() if res.parent_content else "N/A"
            graph_entities = ""
            if res.related_entities:
                encoded = json.dumps(res.related_entities, ensure_ascii=False)
                graph_entities = f"\nSubgrafo/Entidades: {encoded}"

            block = (
                f"[Evidência {i}] ({source_info} | {meta})\nConteúdo:\n{content}{graph_entities}"
            ).strip()
            sections.append(block)

        return "\n\n---\n\n".join(sections)

    async def synthesize_answer(
        self,
        query: str,
        search_results: list[HybridSearchResult],
    ) -> str:
        if not search_results:
            return (
                "Nenhum documento ou contexto relevante foi encontrado na Knowledge Base "
                "para responder a essa pergunta."
            )

        context_str = self._build_context(search_results)

        system_instruction = (
            "Você é o sintetizador de conhecimento factual do Agentic Substrate.\n"
            "Sua missão é responder à pergunta do usuário de forma estritamente factual, "
            "densa e concisa em Markdown (Fact-Dense Markdown).\n\n"
            "REGRAS INEGOCIÁVEIS:\n"
            "1. Sem enrolação ou introduções/conclusões conversacionais "
            "(ex: 'Com base no contexto...', 'Espero ter ajudado'). Vá direto aos fatos.\n"
            "2. Use tópicos estruturados (bullet points) e tabelas quando aplicável "
            "para máxima densidade de informação.\n"
            "3. CITAÇÃO E PROVENIÊNCIA OBRIGATÓRIA: Toda afirmação factual DEVE conter a "
            "referência explícita ao Chunk ID ou Entidade correspondente no formato "
            "[^chunk:<parent_chunk_id>] ou [^entidade:<nome>].\n"
            "4. Se o contexto não contiver dados suficientes, aponte exatamente a lacuna "
            "sem inventar fatos."
        )

        user_prompt = (
            f"Pergunta:\n{query}\n\n"
            f"Evidências e Subgrafos Recuperados:\n{context_str}\n\n"
            f"Resposta Sintetizada:"
        )

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": self._app_referer,
            "X-Title": self._app_title,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model_name,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        }

        client = await self._get_client()
        try:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if content:
                    return str(content).strip()

            return "Não foi possível gerar a síntese a partir do modelo."
        except Exception as ex:
            count = len(search_results)
            return (
                f"Erro na comunicação com o LLM via OpenRouter ({str(ex)}). "
                f"Evidências encontradas ({count} resultados disponíveis no inspetor)."
            )
