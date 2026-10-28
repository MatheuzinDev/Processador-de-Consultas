from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from core.catalogo import CATALOGO, Catalogo
from core.otimizacao import NoAlgebra, formatar_colunas, formatar_condicoes

HEURISTICA_JUNCAO = "Heurística de junção"
HEURISTICA_TUPLAS = "Heurística de redução de tuplas"
HEURISTICA_ATRIBUTOS = "Heurística de redução de atributos"
HEURISTICA_RESTRITIVAS = "Heurística de seleções e junções mais restritivas"

_OPERACOES = {
    "Tabela": "Leitura de tabela",
    "Filtro": "Seleção (σ)",
    "Projecao": "Projeção (π)",
    "Juncao": "Junção (⨝)",
}


@dataclass(frozen=True, slots=True)
class PassoExecucao:
    numero: int
    resultado: str
    tipo: str
    operacao: str
    expressao: str
    entradas: tuple[str, ...]
    heuristicas: tuple[str, ...]
    justificativa: str


@dataclass(frozen=True, slots=True)
class PlanoExecucao:
    passos: tuple[PassoExecucao, ...]

    @property
    def resultado_final(self) -> str:
        return self.passos[-1].resultado


class _GeradorPlano:
    def __init__(self, arvore: NoAlgebra, catalogo: Catalogo) -> None:
        self._arvore = arvore
        self._catalogo = catalogo
        self._passos: list[PassoExecucao] = []
        self._folhas_lidas = 0
        self._total_folhas = sum(
            1 for no in _percorrer(arvore) if no.tipo == "Tabela"
        )
        self._tabelas_filtradas = frozenset(
            no.filhos[0].tabela
            for no in _percorrer(arvore)
            if no.tipo == "Filtro" and no.filhos[0].tipo == "Tabela"
        )

    def gerar(self) -> PlanoExecucao:
        self._validar_operadores(self._arvore)
        self._executar(self._arvore)
        return PlanoExecucao(tuple(self._passos))

    def _validar_operadores(self, no: NoAlgebra) -> None:
        tipos_suportados = {"Tabela", "Filtro", "Projecao", "Juncao"}

        if no.tipo not in tipos_suportados:
            raise ValueError(
                f"Tipo de operador não suportado na HU5: {no.tipo}"
            )

        for filho in no.filhos:
            self._validar_operadores(filho)

    def _executar(self, no: NoAlgebra) -> str:
        entradas = tuple(self._executar(filho) for filho in no.filhos)
        numero = len(self._passos) + 1
        resultado = f"R{numero}"
        expressao, heuristicas, justificativa = self._descrever(no, entradas)
        self._passos.append(
            PassoExecucao(
                numero=numero,
                resultado=resultado,
                tipo=no.tipo,
                operacao=self._nome_operacao(no),
                expressao=expressao,
                entradas=entradas,
                heuristicas=heuristicas,
                justificativa=justificativa,
            )
        )
        return resultado

    def _nome_operacao(self, no: NoAlgebra) -> str:
        if no.tipo == "Projecao" and no is self._arvore:
            return "Projeção final (π)"
        return _OPERACOES[no.tipo]

    def _descrever(
        self,
        no: NoAlgebra,
        entradas: tuple[str, ...],
        ) -> tuple[str, tuple[str, ...], str]:
            if no.tipo == "Tabela":
                return self._descrever_tabela(no)

            if no.tipo == "Filtro":
                return self._descrever_filtro(no, entradas)

            if no.tipo == "Projecao":
                return self._descrever_projecao(no, entradas)

            if no.tipo == "Juncao":
                return self._descrever_juncao(no, entradas)

            raise ValueError(
                f"Tipo de operador não suportado na HU5: {no.tipo}"
            )

    def _descrever_tabela(
        self,
        no: NoAlgebra,
    ) -> tuple[str, tuple[str, ...], str]:
        self._folhas_lidas += 1
        if self._total_folhas == 1:
            return no.tabela, (), "Única tabela da consulta."

        selecao = (
            "com seleção antecipada"
            if no.tabela in self._tabelas_filtradas
            else "sem seleção"
        )
        justificativa = (
            f"Folha {self._folhas_lidas} de {self._total_folhas} na ordem de "
            f"junção definida pelo grafo otimizado ({selecao})."
        )
        return no.tabela, (HEURISTICA_RESTRITIVAS,), justificativa

    def _descrever_filtro(
        self,
        no: NoAlgebra,
        entradas: tuple[str, ...],
    ) -> tuple[str, tuple[str, ...], str]:
        tabela = _tabela_do_ramo(no)
        expressao = f"σ_{{{formatar_condicoes(no.condicoes)}}}({entradas[0]})"
        justificativa = (
            f"Seleção aplicada logo acima de {tabela}, antes das junções: "
            "elimina tuplas cedo e reduz os resultados intermediários."
        )
        return expressao, (HEURISTICA_TUPLAS,), justificativa

    def _descrever_projecao(
        self,
        no: NoAlgebra,
        entradas: tuple[str, ...],
    ) -> tuple[str, tuple[str, ...], str]:
        expressao = f"π_{{{formatar_colunas(no.colunas)}}}({entradas[0]})"
        if no is self._arvore:
            justificativa = (
                "Projeção final: mantém apenas as colunas pedidas no SELECT "
                "e produz o resultado da consulta."
            )
            return expressao, (HEURISTICA_ATRIBUTOS,), justificativa

        tabela = _tabela_do_ramo(no)
        total = len(self._catalogo.buscar_tabela(tabela).colunas)
        justificativa = (
            f"Mantém {len(no.colunas)} de {total} atributos de {tabela}: "
            "só as colunas do SELECT e das condições de junção."
        )
        return expressao, (HEURISTICA_ATRIBUTOS,), justificativa

    def _descrever_juncao(
        self,
        no: NoAlgebra,
        entradas: tuple[str, ...],
    ) -> tuple[str, tuple[str, ...], str]:
        condicoes = formatar_condicoes(no.condicoes)
        expressao = f"{entradas[0]} ⨝_{{{condicoes}}} {entradas[1]}"
        tabela = _tabela_do_ramo(no.filhos[1])
        justificativa = (
            f"Une {entradas[0]} e {entradas[1]} pela condição de junção, "
            f"evitando produto cartesiano; {tabela} entra nesta posição por "
            "ser a próxima tabela restritiva ligada às anteriores."
        )
        return (
            expressao,
            (HEURISTICA_JUNCAO, HEURISTICA_RESTRITIVAS),
            justificativa,
        )

def _percorrer(no: NoAlgebra) -> Iterator[NoAlgebra]:
    yield no
    for filho in no.filhos:
        yield from _percorrer(filho)


def _tabela_do_ramo(no: NoAlgebra) -> str:
    atual = no
    while atual.tipo != "Tabela":
        atual = atual.filhos[0]
    return atual.tabela


def gerar_plano_execucao(
    arvore: NoAlgebra,
    catalogo: Catalogo = CATALOGO,
) -> PlanoExecucao:
    return _GeradorPlano(arvore, catalogo).gerar()


def plano_para_texto(plano: PlanoExecucao) -> str:
    linhas = []
    for passo in plano.passos:
        linhas.append(
            f"{passo.numero}. {passo.resultado} ← {passo.expressao}"
            f"  [{passo.operacao}]"
        )
        heuristicas = ", ".join(passo.heuristicas) or "nenhuma"
        linhas.append(f"   Heurísticas: {heuristicas}")
        linhas.append(f"   {passo.justificativa}")
    return "\n".join(linhas)