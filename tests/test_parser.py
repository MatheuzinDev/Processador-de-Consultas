import unittest
from decimal import Decimal

from core.erros import ErroSintatico
from core.modelos import (
    Comparacao,
    Conjuncao,
    ConsultaSQL,
    Literal,
    ReferenciaColuna,
    TipoDado,
)
from core.parser import parsear


CONSULTA_1 = """Select cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
where cliente.TipoCliente_idTipoCliente = 1 and pedido.ValorTotalPedido = 0;"""

CONSULTA_2 = """Select cliente.nome, pedido.idPedido, pedido.DataPedido, Status.descricao, pedido.ValorTotalPedido
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
Join Status on Status.idstatus = Pedido.status_idstatus
where Status.descricao = 'Aberto' and cliente.TipoCliente_idTipoCliente = 1 and pedido.ValorTotalPedido = 0;"""

CONSULTA_3 = """Select cliente.nome, pedido.idPedido, pedido.DataPedido, Status.descricao, pedido.ValorTotalPedido, produto.QuantEstoque
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
Join Status on Status.idstatus = Pedido.status_idstatus
Join pedido_has_produto on pedido.idPedido = pedido_has_produto.Pedido_idPedido
Join produto on produto.idProduto = pedido_has_produto.Produto_idProduto
where Status.descricao = 'Aberto' and cliente.TipoCliente_idTipoCliente = 1 and pedido.ValorTotalPedido = 0 and produto.QuantEstoque > 0;"""

CONSULTA_4 = """Select cliente.nome, tipocliente.descricao, pedido.idPedido, pedido.DataPedido, Status.descricao, pedido.ValorTotalPedido, categoria.descricao, produto.QuantEstoque
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
Join tipocliente on cliente.tipocliente_idtipocliente = tipocliente.idTipoCliente
Join endereco on cliente.idcliente = endereco.Cliente_idCliente
Join Status on Status.idstatus = Pedido.status_idstatus
Join pedido_has_produto on pedido.idPedido = pedido_has_produto.Pedido_idPedido
Join produto on produto.idProduto = pedido_has_produto.Produto_idProduto
Join categoria on categoria.idcategoria = produto.Categoria_idCategoria
where Status.descricao = 'Aberto' and cliente.email = 'Luffy@gmail.com' and pedido.ValorTotalPedido = 0"""


def comparacao_inteira(nome: str, valor: int) -> Comparacao:
    return Comparacao(
        ReferenciaColuna(nome),
        "=",
        Literal(str(valor), valor, TipoDado.INTEIRO),
    )


class TestParserConsulta(unittest.TestCase):
    def test_parseia_consulta_minima(self) -> None:
        consulta = parsear("SELECT Nome FROM Cliente;")

        self.assertEqual(
            consulta,
            ConsultaSQL((ReferenciaColuna("Nome"),), "Cliente"),
        )

    def test_preserva_colunas_qualificadas_e_ordem_da_projecao(self) -> None:
        consulta = parsear(
            "SELECT Cliente.Nome, Email, Cliente.DataRegistro FROM Cliente;"
        )

        self.assertEqual(
            consulta.colunas,
            (
                ReferenciaColuna("Nome", "Cliente"),
                ReferenciaColuna("Email"),
                ReferenciaColuna("DataRegistro", "Cliente"),
            ),
        )

    def test_preserva_caixa_dos_identificadores(self) -> None:
        consulta = parsear("Select CLIENTE.nome From cLiEnTe;")

        self.assertEqual(consulta.colunas, (ReferenciaColuna("nome", "CLIENTE"),))
        self.assertEqual(consulta.tabela_origem, "cLiEnTe")

    def test_aceita_nomes_desconhecidos_sem_validacao_semantica(self) -> None:
        consulta = parsear("SELECT Pessoa.Apelido FROM Pessoa;")

        self.assertEqual(
            consulta,
            ConsultaSQL(
                (ReferenciaColuna("Apelido", "Pessoa"),),
                "Pessoa",
            ),
        )

    def test_parseia_uma_juncao(self) -> None:
        consulta = parsear(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        self.assertEqual(len(consulta.juncoes), 1)
        self.assertEqual(consulta.juncoes[0].tabela, "Pedido")
        self.assertEqual(
            consulta.juncoes[0].condicao,
            Comparacao(
                ReferenciaColuna("idCliente", "Cliente"),
                "=",
                ReferenciaColuna("Cliente_idCliente", "Pedido"),
            ),
        )

    def test_preserva_ordem_de_multiplas_juncoes(self) -> None:
        consulta = parsear(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "JOIN Status ON Pedido.Status_idStatus = Status.idStatus;"
        )

        self.assertEqual(
            tuple(juncao.tabela for juncao in consulta.juncoes),
            ("Pedido", "Status"),
        )

    def test_aceita_operador_nao_igual_no_on(self) -> None:
        consulta = parsear(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente > Pedido.Cliente_idCliente;"
        )

        self.assertEqual(consulta.juncoes[0].condicao.operador, ">")

    def test_where_e_opcional(self) -> None:
        sem_where = parsear("SELECT Nome FROM Cliente;")
        com_where = parsear("SELECT Nome FROM Cliente WHERE idCliente = 1;")

        self.assertIsNone(sem_where.condicao)
        self.assertIsInstance(com_where.condicao, Comparacao)


class TestParserLiteraisECondicoes(unittest.TestCase):
    def test_converte_literais_numericos(self) -> None:
        casos = (
            ("10", 10, TipoDado.INTEIRO),
            ("-5", -5, TipoDado.INTEIRO),
            ("10.50", Decimal("10.50"), TipoDado.DECIMAL),
            ("-0.75", Decimal("-0.75"), TipoDado.DECIMAL),
        )

        for texto, valor, tipo in casos:
            with self.subTest(texto=texto):
                consulta = parsear(
                    f"SELECT Nome FROM Cliente WHERE idCliente = {texto};"
                )
                literal = consulta.condicao.direita
                self.assertEqual(literal, Literal(texto, valor, tipo))

    def test_converte_texto_vazio_e_aspa_escapada(self) -> None:
        casos = (("''", ""), ("'D''Ávila'", "D'Ávila"))

        for texto, valor in casos:
            with self.subTest(texto=texto):
                consulta = parsear(
                    f"SELECT Nome FROM Cliente WHERE Nome = {texto};"
                )
                literal = consulta.condicao.direita
                self.assertEqual(literal, Literal(texto, valor, TipoDado.TEXTO))

    def test_data_permanece_texto(self) -> None:
        consulta = parsear(
            "SELECT Nascimento FROM Cliente "
            "WHERE Nascimento >= '2000-01-01';"
        )

        literal = consulta.condicao.direita
        self.assertEqual(literal.tipo, TipoDado.TEXTO)
        self.assertEqual(literal.valor, "2000-01-01")

    def test_preserva_ordem_de_literal_e_coluna(self) -> None:
        consulta = parsear("SELECT Nome FROM Cliente WHERE 10 < idCliente;")

        self.assertIsInstance(consulta.condicao.esquerda, Literal)
        self.assertIsInstance(consulta.condicao.direita, ReferenciaColuna)

    def test_aceita_todos_os_operadores(self) -> None:
        for operador in ("=", ">", "<", "<=", ">=", "<>"):
            with self.subTest(operador=operador):
                consulta = parsear(
                    f"SELECT Nome FROM Cliente WHERE idCliente {operador} 1;"
                )
                self.assertEqual(consulta.condicao.operador, operador)

    def test_and_sem_parenteses_associa_a_esquerda(self) -> None:
        consulta = parsear(
            "SELECT Nome FROM Cliente WHERE A = 1 AND B = 2 AND C = 3;"
        )

        esperado = Conjuncao(
            Conjuncao(comparacao_inteira("A", 1), comparacao_inteira("B", 2)),
            comparacao_inteira("C", 3),
        )
        self.assertEqual(consulta.condicao, esperado)

    def test_parenteses_a_direita_preservam_associacao(self) -> None:
        consulta = parsear(
            "SELECT Nome FROM Cliente WHERE A = 1 AND (B = 2 AND C = 3);"
        )

        esperado = Conjuncao(
            comparacao_inteira("A", 1),
            Conjuncao(comparacao_inteira("B", 2), comparacao_inteira("C", 3)),
        )
        self.assertEqual(consulta.condicao, esperado)

    def test_parenteses_aninhados_sao_aceitos(self) -> None:
        consulta = parsear("SELECT Nome FROM Cliente WHERE (((A = 1)));")

        self.assertEqual(consulta.condicao, comparacao_inteira("A", 1))

    def test_on_aceita_condicao_composta(self) -> None:
        consulta = parsear(
            "SELECT Cliente.Nome FROM Cliente JOIN Pedido ON "
            "Cliente.idCliente = Pedido.Cliente_idCliente "
            "AND Pedido.ValorTotalPedido > 0;"
        )

        self.assertIsInstance(consulta.juncoes[0].condicao, Conjuncao)


class TestParserErros(unittest.TestCase):
    def test_consulta_vazia_espera_select(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            parsear("")

        self.assertEqual(
            str(contexto.exception),
            "Erro sintático na linha 1, coluna 1: esperado SELECT, "
            "encontrado fim da consulta.",
        )

    def test_erros_estruturais_informam_elemento_esperado(self) -> None:
        casos = (
            ("FROM Cliente;", "esperado SELECT"),
            ("SELECT FROM Cliente;", "esperado nome de coluna após SELECT"),
            ("SELECT , Nome FROM Cliente;", "esperado nome de coluna após SELECT"),
            ("SELECT Nome, FROM Cliente;", "esperado nome de coluna após ','"),
            ("SELECT Nome Email FROM Cliente;", "esperado FROM após a lista"),
            ("SELECT Nome FROM ;", "esperado nome da tabela após FROM"),
            (
                "SELECT Nome FROM Cliente JOIN ON Nome = Nome;",
                "esperado nome da tabela após JOIN",
            ),
            (
                "SELECT Nome FROM Cliente JOIN Pedido;",
                "esperado ON após a tabela Pedido",
            ),
            (
                "SELECT Nome FROM Cliente JOIN Pedido ON;",
                "esperado operando",
            ),
            ("SELECT Nome FROM Cliente WHERE;", "esperado operando"),
            ("SELECT Nome FROM Cliente WHERE Nome 1;", "esperado operador"),
            ("SELECT Nome FROM Cliente WHERE Nome =;", "esperado operando"),
            ("SELECT Nome FROM Cliente WHERE ();", "esperado operando"),
            ("SELECT Nome FROM Cliente WHERE Nome = 1 AND;", "esperado operando"),
        )

        for sql, trecho in casos:
            with self.subTest(sql=sql):
                with self.assertRaises(ErroSintatico) as contexto:
                    parsear(sql)
                self.assertIn(trecho, str(contexto.exception))

    def test_referencia_qualificada_exige_coluna_apos_ponto(self) -> None:
        for sql in (
            "SELECT Cliente. FROM Cliente;",
            "SELECT Cliente..Nome FROM Cliente;",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(ErroSintatico) as contexto:
                    parsear(sql)
                self.assertIn("nome de coluna após '.'", str(contexto.exception))

    def test_parentese_nao_fechado_informa_posicao_do_token_atual(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            parsear("SELECT Nome FROM Cliente\nWHERE (Nome = 'Maria';")

        erro = contexto.exception
        self.assertIn("')' para fechar a condição", str(erro))
        self.assertEqual((erro.linha, erro.coluna), (2, 22))

    def test_ponto_e_virgula_e_obrigatorio(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            parsear("SELECT Nome FROM Cliente")

        erro = contexto.exception
        self.assertIn("';' ao final da consulta", str(erro))
        self.assertEqual((erro.linha, erro.coluna), (1, 25))

    def test_rejeita_conteudo_apos_ponto_e_virgula(self) -> None:
        for sql in (
            "SELECT Nome FROM Cliente;;",
            "SELECT Nome FROM Cliente; SELECT Nome FROM Cliente;",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(ErroSintatico) as contexto:
                    parsear(sql)
                self.assertIn("esperado fim da consulta", str(contexto.exception))

    def test_rejeita_join_depois_do_where(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            parsear(
                "SELECT Nome FROM Cliente WHERE idCliente = 1 "
                "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
            )

        self.assertIn("';' ao final da consulta", str(contexto.exception))

    def test_rejeita_segundo_where(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            parsear(
                "SELECT Nome FROM Cliente WHERE idCliente = 1 "
                "WHERE Nome = 'Maria';"
            )

        self.assertIn("';' ao final da consulta", str(contexto.exception))

    def test_propaga_erros_lexicos(self) -> None:
        casos = (
            ("SELECT * FROM Cliente;", "caractere '*' não reconhecido"),
            (
                "SELECT Nome FROM Cliente WHERE Nome = 'Maria;",
                "texto iniciado nesta posição não foi fechado",
            ),
            (
                "SELECT Nome FROM Cliente WHERE idCliente = 10.;",
                "número decimal malformado",
            ),
        )

        for sql, trecho in casos:
            with self.subTest(sql=sql):
                with self.assertRaises(ErroSintatico) as contexto:
                    parsear(sql)
                self.assertIn(trecho, str(contexto.exception))


class TestParserConsultasReferencia(unittest.TestCase):
    def test_tres_primeiras_consultas_sao_aceitas(self) -> None:
        casos = (
            (CONSULTA_1, 4, ("pedido",)),
            (CONSULTA_2, 5, ("pedido", "Status")),
            (
                CONSULTA_3,
                6,
                ("pedido", "Status", "pedido_has_produto", "produto"),
            ),
        )

        for sql, qtd_colunas, tabelas_juntadas in casos:
            with self.subTest(qtd_colunas=qtd_colunas):
                consulta = parsear(sql)
                self.assertEqual(len(consulta.colunas), qtd_colunas)
                self.assertEqual(
                    tuple(juncao.tabela for juncao in consulta.juncoes),
                    tabelas_juntadas,
                )
                self.assertIsNotNone(consulta.condicao)

    def test_quarta_consulta_original_falha_sem_ponto_e_virgula(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            parsear(CONSULTA_4)

        self.assertIn("';' ao final da consulta", str(contexto.exception))

    def test_quarta_consulta_corrigida_e_aceita(self) -> None:
        consulta = parsear(CONSULTA_4 + ";")

        self.assertEqual(len(consulta.colunas), 8)
        self.assertEqual(
            tuple(juncao.tabela for juncao in consulta.juncoes),
            (
                "pedido",
                "tipocliente",
                "endereco",
                "Status",
                "pedido_has_produto",
                "produto",
                "categoria",
            ),
        )
        self.assertIsNotNone(consulta.condicao)


if __name__ == "__main__":
    unittest.main()
