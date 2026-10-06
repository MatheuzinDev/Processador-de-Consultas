import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal

from core.modelos import (
    Comparacao,
    Conjuncao,
    ConsultaSQL,
    JuncaoSQL,
    Literal,
    ReferenciaColuna,
    TipoDado,
    TipoToken,
    Token,
)


class TestModelos(unittest.TestCase):
    def test_tipos_de_token_cobrem_a_gramatica(self) -> None:
        esperados = {
            "SELECT",
            "FROM",
            "WHERE",
            "JOIN",
            "ON",
            "AND",
            "IDENTIFICADOR",
            "NUMERO",
            "TEXTO",
            "VIRGULA",
            "PONTO",
            "ABRE_PARENTESE",
            "FECHA_PARENTESE",
            "OPERADOR",
            "PONTO_E_VIRGULA",
            "FIM",
        }

        self.assertEqual({tipo.name for tipo in TipoToken}, esperados)

    def test_tipos_de_dado_cobrem_as_familias_do_modelo(self) -> None:
        self.assertEqual(
            {tipo.name for tipo in TipoDado},
            {"INTEIRO", "DECIMAL", "TEXTO", "DATA_HORA"},
        )

    def test_token_preserva_texto_e_posicao(self) -> None:
        token = Token(TipoToken.SELECT, "Select", 2, 5)

        self.assertEqual(token.tipo, TipoToken.SELECT)
        self.assertEqual(token.texto, "Select")
        self.assertEqual(token.linha, 2)
        self.assertEqual(token.coluna, 5)

    def test_modelos_sao_imutaveis(self) -> None:
        token = Token(TipoToken.IDENTIFICADOR, "Cliente", 1, 1)

        with self.assertRaises(FrozenInstanceError):
            token.texto = "Pedido"

    def test_referencia_nao_qualificada(self) -> None:
        referencia = ReferenciaColuna("Nome")

        self.assertEqual(referencia.nome, "Nome")
        self.assertIsNone(referencia.tabela)
        self.assertIsNone(referencia.tipo)

    def test_referencia_qualificada_e_resolvida(self) -> None:
        referencia = ReferenciaColuna("Nome", "Cliente", TipoDado.TEXTO)

        self.assertEqual(referencia.tabela, "Cliente")
        self.assertEqual(referencia.nome, "Nome")
        self.assertEqual(referencia.tipo, TipoDado.TEXTO)

    def test_literais_preservam_valores_tipados(self) -> None:
        casos = (
            (Literal("10", 10, TipoDado.INTEIRO), int),
            (Literal("10.50", Decimal("10.50"), TipoDado.DECIMAL), Decimal),
            (Literal("'Aberto'", "Aberto", TipoDado.TEXTO), str),
            (
                Literal(
                    "'2026-10-05'",
                    datetime(2026, 10, 5),
                    TipoDado.DATA_HORA,
                ),
                datetime,
            ),
        )

        for literal, tipo_python in casos:
            with self.subTest(literal=literal):
                self.assertIsInstance(literal.valor, tipo_python)

    def test_comparacao_e_conjuncao_preservam_a_estrutura(self) -> None:
        preco = ReferenciaColuna("Preco", "Produto")
        estoque = ReferenciaColuna("QuantEstoque", "Produto")
        comparacao_preco = Comparacao(
            preco,
            ">=",
            Literal("10.50", Decimal("10.50"), TipoDado.DECIMAL),
        )
        comparacao_estoque = Comparacao(
            estoque,
            ">",
            Literal("0", 0, TipoDado.INTEIRO),
        )
        condicao = Conjuncao(comparacao_preco, comparacao_estoque)

        self.assertIs(condicao.esquerda, comparacao_preco)
        self.assertIs(condicao.direita, comparacao_estoque)
        self.assertEqual(comparacao_preco.operador, ">=")

    def test_consulta_minima_usa_defaults_imutaveis(self) -> None:
        consulta = ConsultaSQL((ReferenciaColuna("Nome", "Cliente"),), "Cliente")

        self.assertEqual(consulta.juncoes, ())
        self.assertIsNone(consulta.condicao)

    def test_consulta_preserva_a_ordem_das_juncoes(self) -> None:
        cliente_pedido = Comparacao(
            ReferenciaColuna("idCliente", "Cliente"),
            "=",
            ReferenciaColuna("Cliente_idCliente", "Pedido"),
        )
        pedido_status = Comparacao(
            ReferenciaColuna("Status_idStatus", "Pedido"),
            "=",
            ReferenciaColuna("idStatus", "Status"),
        )
        juncoes = (
            JuncaoSQL("Pedido", cliente_pedido),
            JuncaoSQL("Status", pedido_status),
        )
        consulta = ConsultaSQL(
            (ReferenciaColuna("Nome", "Cliente"),),
            "Cliente",
            juncoes,
        )

        self.assertEqual(
            tuple(juncao.tabela for juncao in consulta.juncoes),
            ("Pedido", "Status"),
        )


if __name__ == "__main__":
    unittest.main()
