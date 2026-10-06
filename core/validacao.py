from datetime import datetime

from core.catalogo import CATALOGO, Catalogo
from core.erros import ErroSemantico
from core.modelos import (
    Comparacao,
    Condicao,
    Conjuncao,
    ConsultaSQL,
    JuncaoSQL,
    Literal,
    Operando,
    ReferenciaColuna,
    TipoDado,
)


_TIPOS_NUMERICOS = frozenset((TipoDado.INTEIRO, TipoDado.DECIMAL))
_NOMES_TIPOS = {
    TipoDado.INTEIRO: "inteiro",
    TipoDado.DECIMAL: "decimal",
    TipoDado.TEXTO: "texto",
    TipoDado.DATA_HORA: "data/hora",
}


class _Validador:
    def __init__(self, catalogo: Catalogo) -> None:
        self._catalogo = catalogo

    def validar(self, consulta: ConsultaSQL) -> ConsultaSQL:
        tabela_origem = self._resolver_tabela(consulta.tabela_origem)
        tabelas_juncoes = self._resolver_tabelas_juncoes(
            tabela_origem,
            consulta.juncoes,
        )
        escopo_completo = (tabela_origem, *tabelas_juncoes)

        colunas = tuple(
            self._resolver_referencia(referencia, escopo_completo)
            for referencia in consulta.colunas
        )

        juncoes = []
        tabelas_anteriores = (tabela_origem,)
        for juncao, tabela in zip(
            consulta.juncoes,
            tabelas_juncoes,
            strict=True,
        ):
            escopo_juncao = (*tabelas_anteriores, tabela)
            condicao = self._resolver_condicao(
                juncao.condicao,
                escopo_juncao,
                em_juncao=True,
            )
            if not self._conecta_nova_tabela(
                condicao,
                tabela,
                tabelas_anteriores,
            ):
                raise ErroSemantico(
                    f"JOIN com a tabela '{tabela}' deve conectá-la a uma "
                    "tabela anterior."
                )

            juncoes.append(JuncaoSQL(tabela, condicao))
            tabelas_anteriores = escopo_juncao

        condicao = None
        if consulta.condicao is not None:
            condicao = self._resolver_condicao(
                consulta.condicao,
                escopo_completo,
                em_juncao=False,
            )

        return ConsultaSQL(
            colunas,
            tabela_origem,
            tuple(juncoes),
            condicao,
        )

    def _resolver_tabela(self, nome: str) -> str:
        tabela = self._catalogo.buscar_tabela(nome)
        if tabela is None:
            raise ErroSemantico(f"Tabela '{nome}' não existe no catálogo.")
        return tabela.nome

    def _resolver_tabelas_juncoes(
        self,
        tabela_origem: str,
        juncoes: tuple[JuncaoSQL, ...],
    ) -> tuple[str, ...]:
        nomes = []
        nomes_usados = {tabela_origem.casefold()}

        for juncao in juncoes:
            tabela = self._resolver_tabela(juncao.tabela)
            nome_normalizado = tabela.casefold()
            if nome_normalizado in nomes_usados:
                raise ErroSemantico(
                    f"Tabela '{tabela}' aparece mais de uma vez; aliases não "
                    "são suportados."
                )
            nomes_usados.add(nome_normalizado)
            nomes.append(tabela)

        return tuple(nomes)

    def _resolver_referencia(
        self,
        referencia: ReferenciaColuna,
        escopo: tuple[str, ...],
    ) -> ReferenciaColuna:
        if referencia.tabela is not None:
            return self._resolver_referencia_qualificada(referencia, escopo)

        ocorrencias = self._catalogo.buscar_tabelas_com_coluna(
            escopo,
            referencia.nome,
        )
        if not ocorrencias:
            raise ErroSemantico(
                f"Coluna '{referencia.nome}' não existe nas tabelas da consulta."
            )
        if len(ocorrencias) > 1:
            tabelas = ", ".join(tabela.nome for tabela, _ in ocorrencias)
            raise ErroSemantico(
                f"Coluna '{referencia.nome}' é ambígua entre: {tabelas}."
            )

        tabela, coluna = ocorrencias[0]
        return ReferenciaColuna(coluna.nome, tabela.nome, coluna.tipo)

    def _resolver_referencia_qualificada(
        self,
        referencia: ReferenciaColuna,
        escopo: tuple[str, ...],
    ) -> ReferenciaColuna:
        tabela_escopo = next(
            (
                tabela
                for tabela in escopo
                if tabela.casefold() == referencia.tabela.casefold()
            ),
            None,
        )
        if tabela_escopo is None:
            raise ErroSemantico(
                f"Tabela '{referencia.tabela}' não participa deste ponto da "
                "consulta."
            )

        coluna = self._catalogo.buscar_coluna(tabela_escopo, referencia.nome)
        if coluna is None:
            raise ErroSemantico(
                f"Coluna '{referencia.nome}' não existe na tabela "
                f"'{tabela_escopo}'."
            )
        return ReferenciaColuna(coluna.nome, tabela_escopo, coluna.tipo)

    def _resolver_condicao(
        self,
        condicao: Condicao,
        escopo: tuple[str, ...],
        *,
        em_juncao: bool,
    ) -> Condicao:
        pendentes = [(condicao, False)]
        resolvidas = []

        while pendentes:
            atual, filhos_visitados = pendentes.pop()
            if isinstance(atual, Comparacao):
                resolvidas.append(
                    self._resolver_comparacao(
                        atual,
                        escopo,
                        em_juncao=em_juncao,
                    )
                )
            elif filhos_visitados:
                direita = resolvidas.pop()
                esquerda = resolvidas.pop()
                resolvidas.append(Conjuncao(esquerda, direita))
            else:
                pendentes.append((atual, True))
                pendentes.append((atual.direita, False))
                pendentes.append((atual.esquerda, False))

        return resolvidas[0]

    def _resolver_comparacao(
        self,
        comparacao: Comparacao,
        escopo: tuple[str, ...],
        *,
        em_juncao: bool,
    ) -> Comparacao:
        esquerda = self._resolver_operando(comparacao.esquerda, escopo)
        direita = self._resolver_operando(comparacao.direita, escopo)

        esquerda_coluna = isinstance(esquerda, ReferenciaColuna)
        direita_coluna = isinstance(direita, ReferenciaColuna)
        if em_juncao and not (esquerda_coluna and direita_coluna):
            raise ErroSemantico("Condições de JOIN devem comparar somente colunas.")
        if not em_juncao and not (esquerda_coluna or direita_coluna):
            raise ErroSemantico(
                "Condições de WHERE devem envolver ao menos uma coluna."
            )

        esquerda, direita = self._ajustar_literais_data(esquerda, direita)
        if not self._tipos_compativeis(esquerda.tipo, direita.tipo):
            raise ErroSemantico(
                "Tipos incompatíveis na comparação: "
                f"{self._descrever_operando(esquerda)} "
                f"({_NOMES_TIPOS[esquerda.tipo]}) e "
                f"{self._descrever_operando(direita)} "
                f"({_NOMES_TIPOS[direita.tipo]})."
            )

        return Comparacao(esquerda, comparacao.operador, direita)

    def _resolver_operando(
        self,
        operando: Operando,
        escopo: tuple[str, ...],
    ) -> Operando:
        if isinstance(operando, ReferenciaColuna):
            return self._resolver_referencia(operando, escopo)
        return operando

    def _ajustar_literais_data(
        self,
        esquerda: Operando,
        direita: Operando,
    ) -> tuple[Operando, Operando]:
        if (
            isinstance(esquerda, ReferenciaColuna)
            and esquerda.tipo == TipoDado.DATA_HORA
            and isinstance(direita, Literal)
            and direita.tipo == TipoDado.TEXTO
        ):
            direita = self._converter_literal_data(direita, esquerda)
        elif (
            isinstance(esquerda, Literal)
            and esquerda.tipo == TipoDado.TEXTO
            and isinstance(direita, ReferenciaColuna)
            and direita.tipo == TipoDado.DATA_HORA
        ):
            esquerda = self._converter_literal_data(esquerda, direita)
        return esquerda, direita

    @staticmethod
    def _converter_literal_data(
        literal: Literal,
        referencia: ReferenciaColuna,
    ) -> Literal:
        try:
            if not isinstance(literal.valor, str):
                raise ValueError
            valor = datetime.fromisoformat(literal.valor)
        except ValueError:
            raise ErroSemantico(
                f"Literal {literal.texto} não é uma data/hora válida para "
                f"{referencia.tabela}.{referencia.nome}."
            ) from None

        return Literal(literal.texto, valor, TipoDado.DATA_HORA)

    @staticmethod
    def _tipos_compativeis(esquerda: TipoDado, direita: TipoDado) -> bool:
        return esquerda == direita or {esquerda, direita} <= _TIPOS_NUMERICOS

    @staticmethod
    def _descrever_operando(operando: Operando) -> str:
        if isinstance(operando, ReferenciaColuna):
            return f"{operando.tabela}.{operando.nome}"
        return operando.texto

    def _conecta_nova_tabela(
        self,
        condicao: Condicao,
        nova_tabela: str,
        tabelas_anteriores: tuple[str, ...],
    ) -> bool:
        anteriores = {tabela.casefold() for tabela in tabelas_anteriores}
        nova = nova_tabela.casefold()
        pendentes = [condicao]

        while pendentes:
            atual = pendentes.pop()
            if isinstance(atual, Conjuncao):
                pendentes.extend((atual.direita, atual.esquerda))
                continue

            esquerda = atual.esquerda
            direita = atual.direita
            if not isinstance(esquerda, ReferenciaColuna) or not isinstance(
                direita,
                ReferenciaColuna,
            ):
                continue

            tabela_esquerda = esquerda.tabela.casefold()
            tabela_direita = direita.tabela.casefold()
            if (
                tabela_esquerda == nova and tabela_direita in anteriores
            ) or (tabela_direita == nova and tabela_esquerda in anteriores):
                return True

        return False


def validar_consulta(
    consulta: ConsultaSQL,
    catalogo: Catalogo = CATALOGO,
) -> ConsultaSQL:
    return _Validador(catalogo).validar(consulta)
