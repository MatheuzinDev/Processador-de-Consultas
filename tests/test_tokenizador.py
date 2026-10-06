import unittest

from core.erros import ErroSintatico
from core.modelos import TipoToken
from core.tokenizador import tokenizar


def tipos(sql: str) -> tuple[TipoToken, ...]:
    return tuple(token.tipo for token in tokenizar(sql))


def textos(sql: str) -> tuple[str, ...]:
    return tuple(token.texto for token in tokenizar(sql))


class TestTokenizador(unittest.TestCase):
    def test_tokeniza_consulta_minima_com_posicoes(self) -> None:
        tokens = tokenizar("SELECT Cliente.Nome FROM Cliente;")

        self.assertEqual(
            tuple(
                (token.tipo, token.texto, token.linha, token.coluna)
                for token in tokens
            ),
            (
                (TipoToken.SELECT, "SELECT", 1, 1),
                (TipoToken.IDENTIFICADOR, "Cliente", 1, 8),
                (TipoToken.PONTO, ".", 1, 15),
                (TipoToken.IDENTIFICADOR, "Nome", 1, 16),
                (TipoToken.FROM, "FROM", 1, 21),
                (TipoToken.IDENTIFICADOR, "Cliente", 1, 26),
                (TipoToken.PONTO_E_VIRGULA, ";", 1, 33),
                (TipoToken.FIM, "", 1, 34),
            ),
        )

    def test_reconhece_palavras_chave_sem_diferenca_de_caixa(self) -> None:
        sql = "select FROM Where join ON aNd"

        self.assertEqual(
            tipos(sql),
            (
                TipoToken.SELECT,
                TipoToken.FROM,
                TipoToken.WHERE,
                TipoToken.JOIN,
                TipoToken.ON,
                TipoToken.AND,
                TipoToken.FIM,
            ),
        )
        self.assertEqual(
            textos(sql),
            ("select", "FROM", "Where", "join", "ON", "aNd", ""),
        )

    def test_reconhece_identificadores_com_underscore_e_digitos(self) -> None:
        sql = "Cliente pedido_has_produto Tabela2 _nome"

        self.assertEqual(
            tipos(sql),
            (
                TipoToken.IDENTIFICADOR,
                TipoToken.IDENTIFICADOR,
                TipoToken.IDENTIFICADOR,
                TipoToken.IDENTIFICADOR,
                TipoToken.FIM,
            ),
        )
        self.assertEqual(
            textos(sql),
            ("Cliente", "pedido_has_produto", "Tabela2", "_nome", ""),
        )

    def test_ignora_espacos_e_controla_quebras_de_linha(self) -> None:
        tokens = tokenizar("\n  SELECT\tNome\r\nFROM\rCliente;")

        self.assertEqual(
            tuple((token.texto, token.linha, token.coluna) for token in tokens),
            (
                ("SELECT", 2, 3),
                ("Nome", 2, 10),
                ("FROM", 3, 1),
                ("Cliente", 4, 1),
                (";", 4, 8),
                ("", 4, 9),
            ),
        )

    def test_entrada_vazia_produz_apenas_fim(self) -> None:
        tokens = tokenizar("")

        self.assertIsInstance(tokens, tuple)
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].tipo, TipoToken.FIM)
        self.assertEqual((tokens[0].linha, tokens[0].coluna), (1, 1))

    def test_posicao_de_fim_apos_quebras_de_linha(self) -> None:
        casos = (("A", 1, 2), ("A\n", 2, 1), ("A\r", 2, 1), ("A\r\n", 2, 1))

        for sql, linha, coluna in casos:
            with self.subTest(sql=repr(sql)):
                fim = tokenizar(sql)[-1]
                self.assertEqual((fim.linha, fim.coluna), (linha, coluna))

    def test_reconhece_simbolos(self) -> None:
        self.assertEqual(
            tipos(",.();"),
            (
                TipoToken.VIRGULA,
                TipoToken.PONTO,
                TipoToken.ABRE_PARENTESE,
                TipoToken.FECHA_PARENTESE,
                TipoToken.PONTO_E_VIRGULA,
                TipoToken.FIM,
            ),
        )

    def test_reconhece_operadores_simples_e_compostos(self) -> None:
        for operador in ("=", ">", "<", "<=", ">=", "<>"):
            with self.subTest(operador=operador):
                tokens = tokenizar(operador)
                self.assertEqual(tokens[0].tipo, TipoToken.OPERADOR)
                self.assertEqual(tokens[0].texto, operador)
                self.assertEqual((tokens[0].linha, tokens[0].coluna), (1, 1))
                self.assertEqual(tokens[1].tipo, TipoToken.FIM)

    def test_reconhece_operador_sem_espacos(self) -> None:
        self.assertEqual(
            tuple((token.tipo, token.texto) for token in tokenizar("Preco>=10")),
            (
                (TipoToken.IDENTIFICADOR, "Preco"),
                (TipoToken.OPERADOR, ">="),
                (TipoToken.NUMERO, "10"),
                (TipoToken.FIM, ""),
            ),
        )

    def test_operador_duplo_invalido_permanece_para_o_parser(self) -> None:
        self.assertEqual(
            tuple((token.tipo, token.texto) for token in tokenizar("==")),
            (
                (TipoToken.OPERADOR, "="),
                (TipoToken.OPERADOR, "="),
                (TipoToken.FIM, ""),
            ),
        )

    def test_reconhece_numeros_e_preserva_o_texto(self) -> None:
        for numero in ("0", "42", "0007", "-5", "10.50", "10.500", "-0.75"):
            with self.subTest(numero=numero):
                tokens = tokenizar(numero)
                self.assertEqual(tokens[0].tipo, TipoToken.NUMERO)
                self.assertEqual(tokens[0].texto, numero)

    def test_decimal_sem_parte_fracionaria_e_rejeitado(self) -> None:
        for numero in ("10.", "-5."):
            with self.subTest(numero=numero):
                with self.assertRaises(ErroSintatico) as contexto:
                    tokenizar(numero)

                erro = contexto.exception
                self.assertEqual(erro.mensagem, "número decimal malformado.")
                self.assertEqual((erro.linha, erro.coluna), (1, 1))

    def test_sinal_sem_numero_e_rejeitado(self) -> None:
        for sql in ("-", "- 5", "-.5"):
            with self.subTest(sql=sql):
                with self.assertRaises(ErroSintatico) as contexto:
                    tokenizar(sql)

                erro = contexto.exception
                self.assertEqual(erro.mensagem, "caractere '-' não reconhecido.")
                self.assertEqual((erro.linha, erro.coluna), (1, 1))

    def test_decimal_sem_parte_inteira_e_deixado_para_o_parser(self) -> None:
        self.assertEqual(
            tuple((token.tipo, token.texto) for token in tokenizar(".5")),
            (
                (TipoToken.PONTO, "."),
                (TipoToken.NUMERO, "5"),
                (TipoToken.FIM, ""),
            ),
        )

    def test_reconhece_textos_e_preserva_as_aspas(self) -> None:
        for texto in ("''", "'Aberto'", "'Maria da Silva'", "'SELECT AND FROM'"):
            with self.subTest(texto=texto):
                tokens = tokenizar(texto)
                self.assertEqual(tokens[0].tipo, TipoToken.TEXTO)
                self.assertEqual(tokens[0].texto, texto)

    def test_reconhece_aspa_escapada(self) -> None:
        texto = "'D''Ávila'"

        tokens = tokenizar(texto)

        self.assertEqual(tokens[0].tipo, TipoToken.TEXTO)
        self.assertEqual(tokens[0].texto, texto)

    def test_reconhece_texto_multilinha_e_atualiza_fim(self) -> None:
        for texto in (
            "'linha 1\nlinha 2'",
            "'linha 1\rlinha 2'",
            "'linha 1\r\nlinha 2'",
        ):
            with self.subTest(texto=repr(texto)):
                tokens = tokenizar(texto)

                self.assertEqual(tokens[0].texto, texto)
                self.assertEqual((tokens[0].linha, tokens[0].coluna), (1, 1))
                self.assertEqual((tokens[-1].linha, tokens[-1].coluna), (2, 9))

    def test_texto_sem_fechamento_aponta_para_aspa_inicial(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            tokenizar("SELECT 'Aberto\ncontinua")

        erro = contexto.exception
        self.assertEqual(
            erro.mensagem,
            "texto iniciado nesta posição não foi fechado.",
        )
        self.assertEqual((erro.linha, erro.coluna), (1, 8))

    def test_rejeita_caracteres_invalidos(self) -> None:
        for caractere in ("*", "+", "@", "[", "]"):
            with self.subTest(caractere=caractere):
                with self.assertRaises(ErroSintatico) as contexto:
                    tokenizar(caractere)

                erro = contexto.exception
                self.assertEqual(
                    erro.mensagem,
                    f"caractere {caractere!r} não reconhecido.",
                )
                self.assertEqual((erro.linha, erro.coluna), (1, 1))

    def test_erro_em_outra_linha_possui_posicao_correta(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            tokenizar("SELECT Nome\nFROM Cliente\n@")

        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (3, 1))

    def test_tokeniza_consulta_com_join_e_where(self) -> None:
        sql = (
            "Select Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Pedido.ValorTotalPedido >= -10.50 "
            "AND Cliente.Nome <> 'SELECT';"
        )

        tokens = tokenizar(sql)
        operadores = tuple(
            token.texto for token in tokens if token.tipo == TipoToken.OPERADOR
        )

        self.assertEqual(operadores, ("=", ">=", "<>"))
        self.assertEqual(tokens[-2].tipo, TipoToken.PONTO_E_VIRGULA)
        self.assertEqual(tokens[-1].tipo, TipoToken.FIM)
        self.assertEqual(
            tuple(
                token.tipo
                for token in tokens
                if token.tipo
                in {
                    TipoToken.SELECT,
                    TipoToken.FROM,
                    TipoToken.JOIN,
                    TipoToken.ON,
                    TipoToken.WHERE,
                    TipoToken.AND,
                }
            ),
            (
                TipoToken.SELECT,
                TipoToken.FROM,
                TipoToken.JOIN,
                TipoToken.ON,
                TipoToken.WHERE,
                TipoToken.AND,
            ),
        )


if __name__ == "__main__":
    unittest.main()
