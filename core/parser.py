from decimal import Decimal
from typing import NoReturn

from core.erros import ErroSintatico
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
    TipoToken,
    Token,
)
from core.tokenizador import tokenizar


class _Parser:
    def __init__(self, tokens: tuple[Token, ...]) -> None:
        self._tokens = tokens
        self._indice = 0

    def executar(self) -> ConsultaSQL:
        self._exigir(TipoToken.SELECT, "SELECT")
        colunas = self._analisar_lista_colunas()
        self._exigir(TipoToken.FROM, "FROM após a lista de colunas")
        tabela_origem = self._exigir(
            TipoToken.IDENTIFICADOR,
            "nome da tabela após FROM",
        ).texto

        juncoes = []
        while self._aceitar(TipoToken.JOIN) is not None:
            juncoes.append(self._analisar_juncao())

        condicao = None
        if self._aceitar(TipoToken.WHERE) is not None:
            condicao = self._analisar_condicao()

        self._exigir(TipoToken.PONTO_E_VIRGULA, "';' ao final da consulta")
        self._exigir(TipoToken.FIM, "fim da consulta")

        return ConsultaSQL(
            colunas,
            tabela_origem,
            tuple(juncoes),
            condicao,
        )

    def _analisar_lista_colunas(self) -> tuple[ReferenciaColuna, ...]:
        colunas = [self._analisar_referencia("nome de coluna após SELECT")]
        while self._aceitar(TipoToken.VIRGULA) is not None:
            colunas.append(self._analisar_referencia("nome de coluna após ','"))
        return tuple(colunas)

    def _analisar_referencia(self, esperado: str = "referência de coluna") -> ReferenciaColuna:
        primeiro = self._exigir(TipoToken.IDENTIFICADOR, esperado)
        if self._aceitar(TipoToken.PONTO) is None:
            return ReferenciaColuna(primeiro.texto)

        segundo = self._exigir(
            TipoToken.IDENTIFICADOR,
            "nome de coluna após '.'",
        )
        return ReferenciaColuna(segundo.texto, primeiro.texto)

    def _analisar_juncao(self) -> JuncaoSQL:
        tabela = self._exigir(
            TipoToken.IDENTIFICADOR,
            "nome da tabela após JOIN",
        ).texto
        self._exigir(TipoToken.ON, f"ON após a tabela {tabela}")
        return JuncaoSQL(tabela, self._analisar_condicao())

    def _analisar_condicao(self) -> Condicao:
        condicao = self._analisar_termo()
        while self._aceitar(TipoToken.AND) is not None:
            condicao = Conjuncao(condicao, self._analisar_termo())
        return condicao

    def _analisar_termo(self) -> Condicao:
        if self._aceitar(TipoToken.ABRE_PARENTESE) is None:
            return self._analisar_comparacao()

        condicao = self._analisar_condicao()
        self._exigir(TipoToken.FECHA_PARENTESE, "')' para fechar a condição")
        return condicao

    def _analisar_comparacao(self) -> Comparacao:
        esquerda = self._analisar_operando()
        operador = self._exigir(
            TipoToken.OPERADOR,
            "operador de comparação",
        )
        direita = self._analisar_operando()
        return Comparacao(esquerda, operador.texto, direita)

    def _analisar_operando(self) -> Operando:
        if self._verificar(TipoToken.IDENTIFICADOR):
            return self._analisar_referencia()

        if self._verificar(TipoToken.NUMERO) or self._verificar(TipoToken.TEXTO):
            return self._criar_literal(self._avancar())

        self._erro_esperado("operando")

    def _criar_literal(self, token: Token) -> Literal:
        if token.tipo == TipoToken.NUMERO:
            if "." in token.texto:
                return Literal(token.texto, Decimal(token.texto), TipoDado.DECIMAL)
            return Literal(token.texto, int(token.texto), TipoDado.INTEIRO)

        valor = token.texto[1:-1].replace("''", "'")
        return Literal(token.texto, valor, TipoDado.TEXTO)

    def _atual(self) -> Token:
        return self._tokens[self._indice]

    def _verificar(self, tipo: TipoToken) -> bool:
        return self._atual().tipo == tipo

    def _aceitar(self, tipo: TipoToken) -> Token | None:
        if not self._verificar(tipo):
            return None
        return self._avancar()

    def _exigir(self, tipo: TipoToken, esperado: str) -> Token:
        if not self._verificar(tipo):
            self._erro_esperado(esperado)
        return self._avancar()

    def _avancar(self) -> Token:
        token = self._atual()
        if token.tipo != TipoToken.FIM:
            self._indice += 1
        return token

    def _erro_esperado(self, esperado: str) -> NoReturn:
        token = self._atual()
        encontrado = (
            "fim da consulta" if token.tipo == TipoToken.FIM else repr(token.texto)
        )
        raise ErroSintatico(
            f"esperado {esperado}, encontrado {encontrado}.",
            token.linha,
            token.coluna,
        )


def parsear(sql: str) -> ConsultaSQL:
    return _Parser(tokenizar(sql)).executar()
