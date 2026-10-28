from __future__ import annotations

from dataclasses import dataclass
from html import escape

from core.catalogo import CATALOGO, Catalogo
from core.conversao import AlgebraRelacional
from core.erros import ErroSemantico
from core.modelos import (
    Comparacao,
    Condicao,
    Conjuncao,
    ConsultaSQL,
    Literal,
    ReferenciaColuna,
)


# Restritividade de uma seleção: quanto menor, mais restritiva.
_PESO_IGUALDADE_CHAVE = 0  # Igualdade em chave primária: devolve no máximo 1 linha
_PESO_IGUALDADE = 1  # Igualdade em coluna que não é chave
_PESO_INTERVALO = 2  # Peso para comparações de intervalo (<, >, <=, >=): devolvem uma faixa de linhas
_PESO_DIFERENCA = 3  # Peso para diferença (<>): elimina poucas linhas, por isso é pouco restritiva
_PESO_ENTRE_COLUNAS = 4  # Peso para comparação entre duas colunas da mesma tabela: não dá para estimar
_PESO_SEM_SELECAO = 5  # Peso para tabela sem filtro nenhum: entra com todas as linhas

_OPERADORES_INTERVALO = frozenset(("<", ">", "<=", ">="))


@dataclass(frozen=True, slots=True)
class NoAlgebra:
    """Nó da árvore de consulta usada pelo otimizador."""

    tipo: str
    filhos: tuple[NoAlgebra, ...] = ()
    tabela: str | None = None
    condicoes: tuple[Comparacao, ...] = ()
    colunas: tuple[ReferenciaColuna, ...] = ()


@dataclass(frozen=True, slots=True)
class PassoOtimizacao:
    heuristica: str
    descricao: str
    expressao: str
    arvore: NoAlgebra


@dataclass(frozen=True, slots=True)
class ResultadoOtimizacao:
    arvore: NoAlgebra
    passos: tuple[PassoOtimizacao, ...]


class _Otimizador:
    def __init__(self, consulta: ConsultaSQL, catalogo: Catalogo) -> None:
        self._consulta = consulta
        self._catalogo = catalogo
        self._tabelas = (
            consulta.tabela_origem,
            *(juncao.tabela for juncao in consulta.juncoes),
        )
        self._condicoes_on = tuple(
            comparacao  
            for juncao in consulta.juncoes 
            for comparacao in separar_conjuncoes(juncao.condicao)  
        )

        self._condicoes_where = separar_conjuncoes(consulta.condicao)
        self._selecoes: dict[str, list[Comparacao]] = {
            tabela: [] for tabela in self._tabelas
        }
        juncoes_where = []
        for comparacao in self._condicoes_where:
            tabelas = tabelas_da_comparacao(comparacao)
            if len(tabelas) == 1:
                self._selecoes[next(iter(tabelas))].append(comparacao)
            else:
                juncoes_where.append(comparacao)
        # Comparações entre colunas de tabelas diferentes no WHERE são
        # condições de junção e passam a acompanhar o operador ⨝.
        self._condicoes_juncao = (*self._condicoes_on, *juncoes_where)

    def otimizar(self) -> ResultadoOtimizacao:
        passos = []

        # PASSO 1 - Heurística de junção: árvore inicial, igual à consulta original
        inicial = self._projecao_final(
            self._filtro(
                self._montar_juncoes(
                    self._tabelas,
                    self._folhas_simples(),
                    self._condicoes_on,
                ),
                self._condicoes_where,
            )
        )
        passos.append(
            PassoOtimizacao(
                "Heurística de junção",
                self._descrever_juncoes(),
                para_texto(inicial),
                inicial,
            )
        )

        # PASSO 2 - Redução de tuplas: cada filtro desce para cima da sua tabela
        folhas_filtradas = self._folhas_com_selecao()
        reducao_tuplas = self._projecao_final(
            self._montar_juncoes(
                self._tabelas,
                folhas_filtradas,
                self._condicoes_juncao,
            )
        )
        passos.append(
            PassoOtimizacao(
                "Heurística de redução de tuplas",
                self._descrever_selecoes(),
                para_texto(reducao_tuplas),
                reducao_tuplas,
            )
        )

        # PASSO 3 - Redução de atributos: π acima de cada tabela com só as colunas necessárias
        folhas_projetadas, descricao_projecoes = self._folhas_com_projecao(
            folhas_filtradas
        )
        reducao_atributos = self._projecao_final(
            self._montar_juncoes(
                self._tabelas,
                folhas_projetadas,
                self._condicoes_juncao,
            )
        )
        passos.append(
            PassoOtimizacao(
                "Heurística de redução de atributos",
                descricao_projecoes,
                para_texto(reducao_atributos),
                reducao_atributos,
            )
        )

        # PASSO 4 - Mais restritivas primeiro: reordena as tabelas sem criar produto cartesiano
        ordem = self._ordenar_por_restritividade()
        final = self._projecao_final(
            self._montar_juncoes(
                ordem,
                folhas_projetadas,
                self._condicoes_juncao,
            )
        )
        passos.append(
            PassoOtimizacao(
                "Heurística de seleções e junções mais restritivas",
                self._descrever_ordem(ordem),
                para_texto(final),
                final,
            )
        )

        return ResultadoOtimizacao(final, tuple(passos))

    # Construção da árvore

    def _folhas_simples(self) -> dict[str, NoAlgebra]:
        return {
            tabela: NoAlgebra("Tabela", tabela=tabela)
            for tabela in self._tabelas
        }

    def _folhas_com_selecao(self) -> dict[str, NoAlgebra]:
        return {
            tabela: self._filtro(folha, tuple(self._selecoes[tabela]))
            for tabela, folha in self._folhas_simples().items()
        }

    def _folhas_com_projecao(
        self,
        folhas: dict[str, NoAlgebra],
    ) -> tuple[dict[str, NoAlgebra], str]:
        if len(self._tabelas) == 1:
            return folhas, (
                "Consulta com uma única tabela: a projeção final já mantém "
                "apenas os atributos necessários."
            )

        projetadas = {}
        reducoes = []
        for tabela, folha in folhas.items():
            colunas = self._atributos_necessarios(tabela)
            total = len(self._catalogo.buscar_tabela(tabela).colunas)
            if len(colunas) < total:
                projetadas[tabela] = NoAlgebra(
                    "Projecao",
                    (folha,),
                    colunas=colunas,
                )
                reducoes.append(f"{tabela} ({total} → {len(colunas)})")
            else:
                projetadas[tabela] = folha

        if not reducoes:
            return projetadas, (
                "Todas as colunas das tabelas são usadas acima delas; "
                "nenhuma projeção intermediária reduziria atributos."
            )
        return projetadas, (
            "Projeções (π) colocadas logo acima de cada tabela, mantendo só "
            "as colunas do SELECT e das condições de junção: "
            + ", ".join(reducoes)
            + "."
        )

    def _montar_juncoes(
        self,
        ordem: tuple[str, ...],
        folhas: dict[str, NoAlgebra],
        condicoes: tuple[Comparacao, ...],
    ) -> NoAlgebra:
        atual = folhas[ordem[0]]
        presentes = {ordem[0]}
        pendentes = list(condicoes)

        for tabela in ordem[1:]:
            presentes.add(tabela)
            usadas = [
                comparacao
                for comparacao in pendentes
                if tabela in tabelas_da_comparacao(comparacao)
                and tabelas_da_comparacao(comparacao) <= presentes
            ]
            for comparacao in usadas:
                pendentes.remove(comparacao)

            if usadas:
                atual = NoAlgebra(
                    "Juncao",
                    (atual, folhas[tabela]),
                    condicoes=tuple(usadas),
                )
            else:
                raise _erro_sem_juncao(tabela)

        return atual

    def _filtro(
        self,
        filho: NoAlgebra,
        condicoes: tuple[Comparacao, ...],
    ) -> NoAlgebra:
        if not condicoes:
            return filho
        return NoAlgebra("Filtro", (filho,), condicoes=tuple(condicoes))

    def _projecao_final(self, filho: NoAlgebra) -> NoAlgebra:
        return NoAlgebra("Projecao", (filho,), colunas=self._consulta.colunas)

    def _atributos_necessarios(self, tabela: str) -> tuple[ReferenciaColuna, ...]:
        referencias = [
            coluna for coluna in self._consulta.colunas if coluna.tabela == tabela
        ]
        for comparacao in self._condicoes_juncao:
            for operando in (comparacao.esquerda, comparacao.direita):
                if (
                    isinstance(operando, ReferenciaColuna)
                    and operando.tabela == tabela
                ):
                    referencias.append(operando)

        nomes = {referencia.nome for referencia in referencias}
        # Mantém a ordem das colunas definida no catálogo.
        return tuple(
            ReferenciaColuna(coluna.nome, tabela, coluna.tipo)
            for coluna in self._catalogo.buscar_tabela(tabela).colunas
            if coluna.nome in nomes
        )

    # Restritividade

    def _ordenar_por_restritividade(self) -> tuple[str, ...]:
        restantes = list(self._tabelas)
        ordem = [min(restantes, key=self._chave_ordenacao)]
        restantes.remove(ordem[0])

        while restantes:
            conectadas = [
                tabela
                for tabela in restantes
                if self._conecta(tabela, set(ordem))
            ]
            if not conectadas:
                raise _erro_sem_juncao(restantes[0])
            proxima = min(conectadas, key=self._chave_ordenacao)
            ordem.append(proxima)
            restantes.remove(proxima)

        return tuple(ordem)

    def _chave_ordenacao(self, tabela: str) -> tuple[int, int]:
        # Empate: mantém a ordem em que a tabela aparece na consulta.
        return self._peso_tabela(tabela), self._tabelas.index(tabela)

    def _conecta(self, tabela: str, presentes: set[str]) -> bool:
        for comparacao in self._condicoes_juncao:
            tabelas = tabelas_da_comparacao(comparacao)
            if tabela in tabelas and (tabelas - {tabela}) <= presentes:
                return True
        return False

    def _peso_tabela(self, tabela: str) -> int:
        return min(
            (self._peso_selecao(comparacao) for comparacao in self._selecoes[tabela]),
            default=_PESO_SEM_SELECAO,
        )

    def _peso_selecao(self, comparacao: Comparacao) -> int:
        coluna, literal = _coluna_e_literal(comparacao)
        if coluna is None or literal is None:
            return _PESO_ENTRE_COLUNAS
        if comparacao.operador == "=":
            definicao = self._catalogo.buscar_coluna(coluna.tabela, coluna.nome)
            if definicao is not None and definicao.chave_primaria:
                return _PESO_IGUALDADE_CHAVE
            return _PESO_IGUALDADE
        if comparacao.operador in _OPERADORES_INTERVALO:
            return _PESO_INTERVALO
        return _PESO_DIFERENCA

    # Descrições

    def _descrever_juncoes(self) -> str:
        if len(self._tabelas) == 1:
            return (
                "Consulta com uma única tabela: não há junções a montar. "
                "A seleção do WHERE e a projeção do SELECT ficam no topo."
            )
        return (
            "Árvore inicial: as tabelas são combinadas com junções (⨝) "
            "usando as condições do ON, no lugar de produtos cartesianos. "
            "A seleção do WHERE e a projeção do SELECT ficam no topo."
        )

    def _descrever_selecoes(self) -> str:
        movidas = [
            f"σ {formatar_condicoes(tuple(condicoes))} → {tabela}"
            for tabela, condicoes in self._selecoes.items()
            if condicoes
        ]
        if not movidas:
            return "A consulta não tem seleções (WHERE) para antecipar."
        if len(self._tabelas) == 1:
            return (
                "Consulta com uma única tabela: a seleção já fica logo acima "
                f"da tabela {self._tabelas[0]}, sem junções para antecipar."
            )
        return (
            "Seleções (σ) do WHERE movidas para logo acima da tabela que "
            "filtram, reduzindo as tuplas antes das junções: "
            + "; ".join(movidas)
            + "."
        )

    def _descrever_ordem(self, ordem: tuple[str, ...]) -> str:
        if len(ordem) == 1:
            return "Consulta com uma única tabela: não há folhas para reordenar."
        nomes_pesos = {
            _PESO_IGUALDADE_CHAVE: "igualdade em chave primária",
            _PESO_IGUALDADE: "igualdade",
            _PESO_INTERVALO: "intervalo",
            _PESO_DIFERENCA: "diferença",
            _PESO_ENTRE_COLUNAS: "comparação entre colunas",
            _PESO_SEM_SELECAO: "sem seleção",
        }
        detalhes = ", ".join(
            f"{tabela} ({nomes_pesos[self._peso_tabela(tabela)]})"
            for tabela in ordem
        )
        if ordem == self._tabelas:
            return (
                "A ordem original das tabelas já vai da seleção mais restritiva "
                "para a menos restritiva, sem produto cartesiano; nenhuma "
                f"reordenação foi necessária: {detalhes}."
            )
        return (
            "Folhas reordenadas da seleção mais restritiva para a menos "
            "restritiva, sempre juntando uma tabela que tenha condição de "
            f"junção com as anteriores (evita produto cartesiano): {detalhes}."
        )


def _erro_sem_juncao(tabela: str) -> ErroSemantico:
    return ErroSemantico(
        f"a tabela '{tabela}' não tem condição de junção com as tabelas "
        "anteriores; produto cartesiano não é suportado, use JOIN ... ON."
    )


def separar_conjuncoes(condicao: Condicao | None) -> tuple[Comparacao, ...]:
    if condicao is None:
        return ()
    comparacoes = []
    pendentes = [condicao]
    while pendentes:
        atual = pendentes.pop()
        if isinstance(atual, Conjuncao):
            pendentes.extend((atual.direita, atual.esquerda))
        else:
            comparacoes.append(atual)
    return tuple(comparacoes)


def tabelas_da_comparacao(comparacao: Comparacao) -> frozenset[str]:
    return frozenset(
        operando.tabela
        for operando in (comparacao.esquerda, comparacao.direita)
        if isinstance(operando, ReferenciaColuna)
    )


def _coluna_e_literal(
    comparacao: Comparacao,
) -> tuple[ReferenciaColuna | None, Literal | None]:
    esquerda, direita = comparacao.esquerda, comparacao.direita
    if isinstance(esquerda, ReferenciaColuna) and isinstance(direita, Literal):
        return esquerda, direita
    if isinstance(esquerda, Literal) and isinstance(direita, ReferenciaColuna):
        return direita, esquerda
    return None, None


def formatar_condicoes(condicoes: tuple[Comparacao, ...]) -> str:
    return " ∧ ".join(
        AlgebraRelacional._formatar_no(comparacao) for comparacao in condicoes
    )


def formatar_colunas(colunas: tuple[ReferenciaColuna, ...]) -> str:
    return ", ".join(AlgebraRelacional._formatar_no(coluna) for coluna in colunas)


def para_texto(no: NoAlgebra) -> str:
    """Representa a árvore como expressão linear de álgebra relacional."""
    if no.tipo == "Tabela":
        return no.tabela
    if no.tipo == "Filtro":
        return f"σ_{{{formatar_condicoes(no.condicoes)}}}({para_texto(no.filhos[0])})"
    if no.tipo == "Projecao":
        return f"π_{{{formatar_colunas(no.colunas)}}}({para_texto(no.filhos[0])})"
    esquerda, direita = (para_texto(filho) for filho in no.filhos)
    return f"({esquerda} ⨝_{{{formatar_condicoes(no.condicoes)}}} {direita})"


# Mesmos símbolos e cores da aba "Álgebra Relacional" (AlgebraRelacional.converter_html)
_HTML_PROJECAO = "<span style='font-size: 20px; color: #bd4a3c;'>π</span>"
_HTML_SELECAO = "<span style='font-size: 20px; color: #f0b84b;'>σ</span>"
_HTML_JUNCAO = "<span style='font-size: 20px; color: #d9f45d;'>⨝</span>"
_HTML_RECUO = "&nbsp;" * 4


def para_html(no: NoAlgebra) -> str:
    """Representa a árvore como expressão de álgebra relacional formatada em HTML."""
    if no.tipo == "Tabela":
        return f"<b>{escape(no.tabela)}</b>"
    if no.tipo in ("Filtro", "Projecao"):
        filho = no.filhos[0]
        if no.tipo == "Filtro":
            cabeca = f"{_HTML_SELECAO} <sub>{escape(formatar_condicoes(no.condicoes))}</sub>"
        else:
            cabeca = f"{_HTML_PROJECAO} <sub>{escape(formatar_colunas(no.colunas))}</sub>"
        if _so_uma_tabela(filho):
            return f"{cabeca}({para_html(filho)})"
        recuo = "&nbsp;&nbsp;" if no.tipo == "Filtro" else ""
        return f"{cabeca}<br>{recuo}({para_html(filho)})"
    # Como nos slides, cada lado da junção com σ/π fica entre parênteses próprios.
    esquerda, direita = (
        f"({para_html(filho)})" if filho.tipo in ("Filtro", "Projecao") else para_html(filho)
        for filho in no.filhos
    )
    operador = f"{_HTML_JUNCAO} <sub>{escape(formatar_condicoes(no.condicoes))}</sub>"
    return f"({esquerda} <br>{_HTML_RECUO}{operador} {direita})"


def _so_uma_tabela(no: NoAlgebra) -> bool:
    return no.tipo == "Tabela" or (
        no.tipo in ("Filtro", "Projecao") and _so_uma_tabela(no.filhos[0])
    )


def para_dicionario(no: NoAlgebra) -> dict:
    """Converte a árvore para o formato aceito por GrafoOperadores."""
    contador_id = 0

    def converter(atual: NoAlgebra) -> dict:
        nonlocal contador_id
        contador_id += 1
        if atual.tipo == "Tabela":
            label = atual.tabela
        elif atual.tipo == "Filtro":
            label = f"σ\n{formatar_condicoes(atual.condicoes)}"
        elif atual.tipo == "Projecao":
            label = f"π\n{formatar_colunas(atual.colunas)}"
        else:
            label = f"⨝\n{formatar_condicoes(atual.condicoes)}"
        return {
            "id": str(contador_id),
            "label": label,
            "tipo": atual.tipo,
            "filhos": [converter(filho) for filho in atual.filhos],
            "ast_no": atual,
        }

    return converter(no)


def otimizar_consulta(
    consulta: ConsultaSQL,
    catalogo: Catalogo = CATALOGO,
) -> ResultadoOtimizacao:
    return _Otimizador(consulta, catalogo).otimizar()
