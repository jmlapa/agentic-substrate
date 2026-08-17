import json
from typing import Any

import httpx

from src.modules.knowledge.domain.interfaces.i_llm_synthesis_service import (
    ILlmSynthesisService,
)
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


class GeminiRagSynthesizer(ILlmSynthesisService):
    """
    Adaptador de síntese RAG baseado no Google Gemini Flash-Lite.
    Consolida chunks textuais e subgrafos ontológicos recuperados e gera
    uma resposta fundamentada e precisa.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        temperature: float = 0.2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_name = (
            model_name.replace("models/", "") if model_name.startswith("models/") else model_name
        )
        self._temperature = temperature
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=30.0)

    def _build_context(self, search_results: list[HybridSearchResult]) -> str:
        sections: list[str] = []
        for i, res in enumerate(search_results, 1):
            source_info = f"Chunk: {res.parent_chunk_id} | Seção: {res.header_path or 'Geral'}"
            meta = f"Score: {res.relevance_score:.4f}"
            content = res.parent_content.strip() if res.parent_content else "N/A"
            graph_entities = ""
            if res.related_entities:
                encoded = json.dumps(res.related_entities, ensure_ascii=False)
                graph_entities = f"Entidades/Grafo: {encoded}"

            block = (
                f"[Evidência {i}] ({source_info} | {meta})\nConteúdo:\n{content}\n{graph_entities}"
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
            "Você é um assistente especialista de conhecimento integrado ao Agentic Substrate. "
            "Responda à pergunta do usuário de forma clara, factual e estruturada em Markdown, "
            "baseando-se EXCLUSIVAMENTE nas evidências e grafos de conhecimento fornecidos. "
            "Se a resposta não puder ser respondida com base no contexto, informe claramente."
        )

        user_prompt = (
            f"Pergunta do Usuário:\n{query}\n\n"
            f"Contexto Recuperado da Knowledge Base:\n{context_str}\n\n"
            f"Sua Resposta Sintetizada:"
        )

        url = f"{self.BASE_URL}/models/{self._model_name}:generateContent?key={self._api_key}"
        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self._temperature,
            },
        }

        client = await self._get_client()
        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return str(parts[0].get("text", "")).strip()

            return "Não foi possível gerar a síntese a partir do modelo."
        except Exception as ex:
            # Fallback gracioso com resumo das evidências
            count = len(search_results)
            return (
                f"Erro na comunicação com o LLM ({str(ex)}). "
                f"Evidências encontradas ({count} resultados disponíveis no inspetor)."
            )
