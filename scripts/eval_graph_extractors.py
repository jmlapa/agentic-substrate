"""
Script de Avaliação (Eval & Benchmark) para Extratores Ontológicos de Grafos.
Compara modelos (7B, 8B, 14B, 26B+) em três níveis de complexidade: Baixa, Média e Alta.
Mede latência, integridade referencial, aderência ao schema ontológico e custo estimado.
"""

import argparse
import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from src.modules.knowledge.domain.ontology.node_type_definition import (
    NodeTypeDefinition,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.property_definition import (
    PropertyDefinition,
)
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)
from src.modules.knowledge.domain.value_objects.extracted_graph import (
    ExtractedGraph,
)
from src.modules.knowledge.infrastructure.extractors.direct_openrouter_graph_extractor import (
    DirectOpenRouterGraphExtractor,
)


def build_benchmark_ontology() -> OntologySchema:
    return OntologySchema(
        name="OntologiaJuridicaBenchmark",
        description="Ontologia de referência para benchmark de extração de Knowledge Graph.",
        node_types=[
            NodeTypeDefinition(
                name="AtoNormativo",
                description="Leis, Decretos, CF e Súmulas",
                properties=[
                    PropertyDefinition(name="tipo", type=PropertyType.STRING, required=True),
                    PropertyDefinition(name="sigla", type=PropertyType.STRING, required=False),
                    PropertyDefinition(name="numero", type=PropertyType.STRING, required=False),
                ],
            ),
            NodeTypeDefinition(
                name="Dispositivo",
                description="Artigos, Parágrafos ou Incisos",
                properties=[
                    PropertyDefinition(name="rotulo", type=PropertyType.STRING, required=True),
                    PropertyDefinition(name="tema", type=PropertyType.STRING, required=False),
                ],
            ),
            NodeTypeDefinition(
                name="SujeitoDireito",
                description="Órgãos, Tribunais, Autoridades ou Cidadãos",
                properties=[
                    PropertyDefinition(name="categoria", type=PropertyType.STRING, required=True),
                    PropertyDefinition(name="sigla", type=PropertyType.STRING, required=False),
                ],
            ),
            NodeTypeDefinition(
                name="CompetenciaDever",
                description="Competências institucionais ou deveres funcionais",
                properties=[
                    PropertyDefinition(name="tipo", type=PropertyType.STRING, required=True),
                    PropertyDefinition(name="descricao", type=PropertyType.STRING, required=False),
                ],
            ),
            NodeTypeDefinition(
                name="AcaoJudicial",
                description="Instrumentos e Ações processuais (ADI, REsp, MS)",
                properties=[
                    PropertyDefinition(name="sigla", type=PropertyType.STRING, required=True),
                    PropertyDefinition(name="natureza", type=PropertyType.STRING, required=False),
                ],
            ),
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="CONTEM",
                source_node_type="AtoNormativo",
                target_node_type="Dispositivo",
                description="O ato normativo contém o dispositivo",
            ),
            RelationshipTypeDefinition(
                name="ATRIBUI_COMPETENCIA",
                source_node_type="Dispositivo",
                target_node_type="CompetenciaDever",
                description="O dispositivo legal atribui uma competência",
            ),
            RelationshipTypeDefinition(
                name="TITULAR_DE",
                source_node_type="SujeitoDireito",
                target_node_type="CompetenciaDever",
                description="O sujeito é titular da competência",
            ),
            RelationshipTypeDefinition(
                name="JULGA_ACAO",
                source_node_type="SujeitoDireito",
                target_node_type="AcaoJudicial",
                description="O tribunal julga a ação judicial",
            ),
            RelationshipTypeDefinition(
                name="PROPOE_ACAO",
                source_node_type="SujeitoDireito",
                target_node_type="AcaoJudicial",
                description="O legitimado propõe a ação judicial",
            ),
        ],
    )


BENCHMARK_CASES: dict[str, dict[str, Any]] = {
    "Baixa": {
        "description": "Texto curto com 2 entidades explícitas e 1 relação direta.",
        "text": (
            "O Supremo Tribunal Federal (STF) possui competência para processar e julgar a "
            "Ação Direta de Inconstitucionalidade (ADI)."
        ),
        "expected_min_nodes": 2,
        "expected_min_edges": 1,
    },
    "Média": {
        "description": "Texto com 4-6 entidades, artigos e atribuição de competência.",
        "text": (
            "A Constituição Federal de 1988 (CF/88), em seu Artigo 102, estabelece a competência "
            "precípua do Supremo Tribunal Federal (STF) para a guarda da Constituição. O "
            "Procurador-Geral da República (PGR) detém legitimidade para propor a Ação Direta de "
            "Inconstitucionalidade perante o STF."
        ),
        "expected_min_nodes": 4,
        "expected_min_edges": 3,
    },
    "Alta": {
        "description": "Texto denso multi-institucional com múltiplos tribunais e competências.",
        "text": (
            "A Constituição Federal de 1988 (CF/88) estrutura o Poder Judiciário brasileiro. "
            "O Artigo 102 da CF/88 atribui ao Supremo Tribunal Federal (STF) a competência "
            "para julgar a Ação Direta de Inconstitucionalidade (ADI), proposta pelo PGR. "
            "Por sua vez, o Artigo 105 da CF/88 outorga ao Superior Tribunal de Justiça (STJ) a "
            "competência para julgar o Recurso Especial (REsp) contra decisões ilegais."
        ),
        "expected_min_nodes": 6,
        "expected_min_edges": 4,
    },
}


@dataclass
class EvalResult:
    complexity: str
    model_name: str
    latency_ms: float
    nodes_count: int
    edges_count: int
    referential_integrity_pct: float
    schema_adherence_pct: float
    success: bool
    error_message: str | None = None


async def evaluate_single_case(
    extractor: DirectOpenRouterGraphExtractor,
    ontology: OntologySchema,
    complexity: str,
    case_data: dict[str, Any],
) -> EvalResult:
    text = case_data["text"]
    allowed_nodes = {nt.name for nt in ontology.node_types}
    allowed_rels = {rt.name for rt in ontology.relationship_types}

    start_time = time.perf_counter()
    try:
        graph: ExtractedGraph = await extractor.extract_graph(
            markdown_text=text,
            ontology=ontology,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        nodes = graph.nodes
        edges = graph.edges
        node_ids = {n.id for n in nodes}

        # 1. Integridade Referencial (Source e Target existem em Node IDs)
        if not edges:
            ref_integrity = 100.0
        else:
            valid_edges = sum(
                1 for e in edges if e.source_id in node_ids and e.target_id in node_ids
            )
            ref_integrity = (valid_edges / len(edges)) * 100.0

        # 2. Aderência ao Schema da Ontologia
        total_elements = len(nodes) + len(edges)
        if total_elements == 0:
            adherence = 0.0
        else:
            valid_nodes = sum(1 for n in nodes if n.node_type in allowed_nodes)
            valid_rels = sum(1 for e in edges if e.relationship_type in allowed_rels)
            adherence = ((valid_nodes + valid_rels) / total_elements) * 100.0

        return EvalResult(
            complexity=complexity,
            model_name=extractor._model_name,
            latency_ms=elapsed_ms,
            nodes_count=len(nodes),
            edges_count=len(edges),
            referential_integrity_pct=ref_integrity,
            schema_adherence_pct=adherence,
            success=True,
        )

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return EvalResult(
            complexity=complexity,
            model_name=extractor._model_name,
            latency_ms=elapsed_ms,
            nodes_count=0,
            edges_count=0,
            referential_integrity_pct=0.0,
            schema_adherence_pct=0.0,
            success=False,
            error_message=str(e),
        )


async def run_benchmark(
    models: list[str],
    api_key: str | None,
    dry_run: bool = False,
) -> list[EvalResult]:
    ontology = build_benchmark_ontology()
    results: list[EvalResult] = []
    mode_str = "DRY-RUN (Mock Local)" if dry_run or not api_key else "OPENROUTER API LIVE"

    print("\n" + "=" * 80)
    print("🚀 INICIANDO BENCHMARK DE EXTRAÇÃO ONTOLÓGICA DIRETA (OPENROUTER)")
    print(f"Modelos: {', '.join(models)}")
    print(f"Modo: {mode_str}")
    print("=" * 80 + "\n")

    for model in models:
        extractor = DirectOpenRouterGraphExtractor(
            model_name=model,
            api_key=None if dry_run else api_key,
        )
        print(f"🤖 Avaliando modelo: [{model}]...")

        for complexity, case_data in BENCHMARK_CASES.items():
            print(f"   ⏳ Cenário {complexity.upper()}...", end=" ", flush=True)
            res = await evaluate_single_case(extractor, ontology, complexity, case_data)
            results.append(res)
            status = "✅ OK" if res.success else f"❌ ERRO: {res.error_message}"
            print(
                f"{status} ({res.latency_ms:.1f}ms | "
                f"{res.nodes_count} nós | {res.edges_count} arestas)"
            )

    return results


def print_summary_table(results: list[EvalResult]) -> None:
    print("\n" + "=" * 90)
    print("📊 RESULTADOS CONSOLIDADOS DO EVAL DE MODELOS")
    print("=" * 90)
    header = (
        f"{'Modelo':<35} | {'Nível':<7} | {'Latência (ms)':<13} | "
        f"{'Nós':<4} | {'Arestas':<7} | {'Integridade %':<13} | {'Aderência %':<11}"
    )
    print(header)
    print("-" * 90)

    for r in results:
        mod_short = r.model_name.split("/")[-1] if "/" in r.model_name else r.model_name
        print(
            f"{mod_short:<35} | {r.complexity:<7} | {r.latency_ms:>11.1f}ms | "
            f"{r.nodes_count:>4} | {r.edges_count:>7} | "
            f"{r.referential_integrity_pct:>12.1f}% | {r.schema_adherence_pct:>10.1f}%"
        )
    print("=" * 90 + "\n")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Eval suite para modelos de extração ontológica.")
    parser.add_argument(
        "--models",
        type=str,
        default="meta-llama/llama-3.1-8b-instruct,qwen/qwen-2.5-7b-instruct,google/gemma-4-26b-a4b-it",
        help="Modelos separados por vírgula para avaliar",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("OPENROUTER_API_KEY"),
        help="OpenRouter API Key (ou usa OPENROUTER_API_KEY do ambiente)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa em modo local sem chamadas remotas de API",
    )

    args = parser.parse_args()
    model_list = [m.strip() for m in args.models.split(",") if m.strip()]

    results = asyncio.run(run_benchmark(model_list, args.api_key, args.dry_run))
    print_summary_table(results)


if __name__ == "__main__":
    main()
