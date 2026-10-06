import unittest
from datetime import datetime

from core.catalogo import Catalogo, Coluna, Tabela
from core.erros import ErroSemantico
from core.modelos import (
    Comparacao,
    Conjuncao,
    ConsultaSQL,
    Literal,
    ReferenciaColuna,
    TipoDado,
)
from core.parser import parsear
from core.validacao import validar_consulta


CONSULTAS_REFERENCIA = (
    """Select cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
where cliente.TipoCliente_idTipoCliente = 1 and pedido.ValorTotalPedido = 0;""",
    """Select cliente.nome, pedido.idPedido, pedido.DataPedido, Status.descricao, pedido.ValorTotalPedido
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
Join Status on Status.idstatus = Pedido.status_idstatus
where Status.descricao = 'Aberto' and cliente.TipoCliente_idTipoCliente = 1 and pedido.ValorTotalPedido = 0;""",
    """Select cliente.nome, pedido.idPedido, pedido.DataPedido, Status.descricao, pedido.ValorTotalPedido, produto.QuantEstoque
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
Join Status on Status.idstatus = Pedido.status_idstatus
Join pedido_has_produto on pedido.idPedido = pedido_has_produto.Pedido_idPedido
Join produto on produto.idProduto = pedido_has_produto.Produto_idProduto
where Status.descricao = 'Aberto' and cliente.TipoCliente_idTipoCliente = 1 and pedido.ValorTotalPedido = 0 and produto.QuantEstoque > 0;""",
    """Select cliente.nome, tipocliente.descricao, pedido.idPedido, pedido.DataPedido, Status.descricao, pedido.ValorTotalPedido, categoria.descricao, produto.QuantEstoque
from Cliente Join pedido on cliente.idcliente = pedido.Cliente_idCliente
Join tipocliente on cliente.tipocliente_idtipocliente = tipocliente.idTipoCliente
Join endereco on cliente.idcliente = endereco.Cliente_idCliente
Join Status on Status.idstatus = Pedido.status_idstatus
Join pedido_has_produto on pedido.idPedido = pedido_has_produto.Pedido_idPedido
Join produto on produto.idProduto = pedido_has_produto.Produto_idProduto
Join categoria on categoria.idcategoria = produto.Categoria_idCategoria
where Status.descricao = 'Aberto' and cliente.email = 'Luffy@gmail.com' and pedido.ValorTotalPedido = 0;""",
)


def validar(sql: str) -> ConsultaSQL:
    return validar_consulta(parsear(sql))


class TestValidacaoTabelasEColunas(unittest.TestCase):
    def test_canoniza_consulta_minima_e_qualifica_coluna(self) -> None:
        consulta = validar("select nome from cliente;")

        self.assertEqual(
            consulta,
            ConsultaSQL(
                (ReferenciaColuna("Nome", "Cliente", TipoDado.TEXTO),),
                "Cliente",
            ),
        )

    def test_canoniza_tabelas_e_preserva_ordem_das_juncoes(self) -> None:
        consulta = validar(
            "SELECT cliente.email FROM cliente "
            "JOIN pedido ON cliente.idcliente = pedido.cliente_idcliente "
            "JOIN status ON pedido.status_idstatus = status.idstatus;"
        )

        self.assertEqual(consulta.tabela_origem, "Cliente")
        self.assertEqual(
            tuple(juncao.tabela for juncao in consulta.juncoes),
            ("Pedido", "Status"),
        )

    def test_rejeita_tabela_de_origem_inexistente(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar("SELECT Nome FROM Pessoa;")

        self.assertIn("Tabela 'Pessoa' não existe", str(contexto.exception))

    def test_rejeita_tabela_de_juncao_inexistente(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pessoa ON Cliente.idCliente = Pessoa.idCliente;"
            )

        self.assertIn("Tabela 'Pessoa' não existe", str(contexto.exception))

    def test_rejeita_tabela_repetida_sem_diferenca_de_caixa(self) -> None:
        for tabela in ("Cliente", "cliente"):
            with self.subTest(tabela=tabela):
                with self.assertRaises(ErroSemantico) as contexto:
                    validar(
                        "SELECT Cliente.Nome FROM Cliente "
                        f"JOIN {tabela} ON Cliente.idCliente = Cliente.idCliente;"
                    )
                self.assertIn("aparece mais de uma vez", str(contexto.exception))

    def test_rejeita_tabela_qualificadora_que_nao_participa(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar("SELECT Pedido.idPedido FROM Cliente;")

        self.assertIn("não participa", str(contexto.exception))

    def test_rejeita_coluna_qualificada_inexistente(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar("SELECT Cliente.Apelido FROM Cliente;")

        self.assertIn("não existe na tabela 'Cliente'", str(contexto.exception))

    def test_rejeita_coluna_nao_qualificada_inexistente(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar("SELECT Apelido FROM Cliente;")

        self.assertIn("não existe nas tabelas", str(contexto.exception))

    def test_rejeita_coluna_nao_qualificada_ambigua(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Descricao FROM Status "
                "JOIN TipoCliente ON Status.idStatus = TipoCliente.idTipoCliente;"
            )

        mensagem = str(contexto.exception)
        self.assertIn("é ambígua", mensagem)
        self.assertIn("Status, TipoCliente", mensagem)

    def test_qualifica_coluna_unica_em_consulta_com_juncao(self) -> None:
        consulta = validar(
            "SELECT Email FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        self.assertEqual(
            consulta.colunas,
            (ReferenciaColuna("Email", "Cliente", TipoDado.TEXTO),),
        )

    def test_catalogo_pode_ser_injetado(self) -> None:
        catalogo = Catalogo(
            (
                Tabela(
                    "Unica",
                    (Coluna("Codigo", TipoDado.INTEIRO, chave_primaria=True),),
                ),
            ),
            (),
        )

        consulta = validar_consulta(parsear("SELECT codigo FROM unica;"), catalogo)

        self.assertEqual(
            consulta.colunas,
            (ReferenciaColuna("Codigo", "Unica", TipoDado.INTEIRO),),
        )

    def test_tipo_da_referencia_e_sempre_obtido_do_catalogo(self) -> None:
        original = ConsultaSQL(
            (ReferenciaColuna("Nome", "Cliente", TipoDado.INTEIRO),),
            "Cliente",
        )

        consulta = validar_consulta(original)

        self.assertEqual(consulta.colunas[0].tipo, TipoDado.TEXTO)
        self.assertEqual(original.colunas[0].tipo, TipoDado.INTEIRO)

    def test_ast_sintatica_nao_e_modificada(self) -> None:
        original = parsear(
            "SELECT nome FROM cliente WHERE nascimento >= '2000-01-01';"
        )

        validar_consulta(original)

        self.assertEqual(original.tabela_origem, "cliente")
        self.assertIsNone(original.colunas[0].tabela)
        self.assertIsNone(original.colunas[0].tipo)
        self.assertEqual(original.condicao.direita.tipo, TipoDado.TEXTO)


class TestValidacaoEscoposECondicoes(unittest.TestCase):
    def test_on_nao_pode_referenciar_tabela_de_juncao_futura(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pedido ON Status.idStatus = Pedido.Status_idStatus "
                "JOIN Status ON Pedido.Status_idStatus = Status.idStatus;"
            )

        self.assertIn("Status", str(contexto.exception))
        self.assertIn("não participa", str(contexto.exception))

    def test_on_resolve_colunas_nao_qualificadas_no_escopo_incremental(self) -> None:
        consulta = validar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON idCliente = Cliente_idCliente;"
        )
        comparacao = consulta.juncoes[0].condicao

        self.assertEqual(
            comparacao.esquerda,
            ReferenciaColuna("idCliente", "Cliente", TipoDado.INTEIRO),
        )
        self.assertEqual(
            comparacao.direita,
            ReferenciaColuna("Cliente_idCliente", "Pedido", TipoDado.INTEIRO),
        )

    def test_select_e_where_usam_escopo_completo(self) -> None:
        consulta = validar(
            "SELECT Status.Descricao FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "JOIN Status ON Pedido.Status_idStatus = Status.idStatus "
            "WHERE Status.Descricao = 'Aberto';"
        )

        self.assertEqual(consulta.colunas[0].tabela, "Status")
        self.assertEqual(consulta.condicao.esquerda.tabela, "Status")

    def test_preserva_associacao_das_conjuncoes(self) -> None:
        consulta = validar(
            "SELECT Nome FROM Cliente WHERE idCliente = 1 "
            "AND (Nome = 'Maria' AND Email = 'maria@email.com');"
        )

        self.assertIsInstance(consulta.condicao, Conjuncao)
        self.assertIsInstance(consulta.condicao.esquerda, Comparacao)
        self.assertIsInstance(consulta.condicao.direita, Conjuncao)

    def test_valida_where_com_muitos_ands_sem_estourar_recursao(self) -> None:
        condicoes = " AND ".join("idCliente > 0" for _ in range(1100))

        consulta = validar(
            f"SELECT Nome FROM Cliente WHERE {condicoes};"
        )

        self.assertIsInstance(consulta.condicao, Conjuncao)

    def test_where_ausente_permanece_ausente(self) -> None:
        consulta = validar("SELECT Nome FROM Cliente;")

        self.assertIsNone(consulta.condicao)


class TestValidacaoTiposELiterais(unittest.TestCase):
    def test_aceita_combinacoes_numericas(self) -> None:
        casos = (
            "idCliente = 1",
            "idCliente = 1.5",
            "ValorTotalPedido = 1",
            "ValorTotalPedido = 1.5",
        )

        for condicao in casos:
            with self.subTest(condicao=condicao):
                tabela = "Pedido" if "ValorTotalPedido" in condicao else "Cliente"
                consulta = validar(
                    f"SELECT {tabela}.id{tabela} FROM {tabela} WHERE {condicao};"
                )
                self.assertIsInstance(consulta.condicao, Comparacao)

    def test_aceita_colunas_de_familias_numericas_diferentes(self) -> None:
        consulta = validar(
            "SELECT Pedido.idPedido FROM Pedido "
            "WHERE Pedido.idPedido < Pedido.ValorTotalPedido;"
        )

        self.assertIsInstance(consulta.condicao, Comparacao)

    def test_aceita_texto_com_texto(self) -> None:
        consulta = validar("SELECT Nome FROM Cliente WHERE Nome = 'Maria';")

        self.assertEqual(consulta.condicao.direita.tipo, TipoDado.TEXTO)

    def test_rejeita_numero_com_texto(self) -> None:
        casos = (
            "idCliente = '1'",
            "Nome = 1",
            "Cliente.Nome = Cliente.idCliente",
        )

        for condicao in casos:
            with self.subTest(condicao=condicao):
                with self.assertRaises(ErroSemantico) as contexto:
                    validar(f"SELECT Nome FROM Cliente WHERE {condicao};")
                self.assertIn("Tipos incompatíveis", str(contexto.exception))

    def test_aceita_literal_a_esquerda_e_preserva_ordem(self) -> None:
        consulta = validar("SELECT Nome FROM Cliente WHERE 1 < idCliente;")

        self.assertIsInstance(consulta.condicao.esquerda, Literal)
        self.assertIsInstance(consulta.condicao.direita, ReferenciaColuna)

    def test_rejeita_comparacao_entre_dois_literais(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar("SELECT Nome FROM Cliente WHERE 1 = 1;")

        self.assertIn("ao menos uma coluna", str(contexto.exception))

    def test_aceita_todos_os_operadores_com_tipos_compativeis(self) -> None:
        for operador in ("=", ">", "<", "<=", ">=", "<>"):
            with self.subTest(operador=operador):
                consulta = validar(
                    f"SELECT Nome FROM Cliente WHERE idCliente {operador} 1;"
                )
                self.assertEqual(consulta.condicao.operador, operador)

    def test_converte_formatos_iso_de_data_hora(self) -> None:
        casos = (
            ("2000-01-01", datetime(2000, 1, 1)),
            ("2000-01-01 14:30:00", datetime(2000, 1, 1, 14, 30)),
            ("2000-01-01T14:30:00", datetime(2000, 1, 1, 14, 30)),
            ("2024-02-29", datetime(2024, 2, 29)),
        )

        for texto, esperado in casos:
            with self.subTest(texto=texto):
                consulta = validar(
                    "SELECT Nascimento FROM Cliente "
                    f"WHERE Nascimento = '{texto}';"
                )
                literal = consulta.condicao.direita
                self.assertEqual(literal.valor, esperado)
                self.assertEqual(literal.tipo, TipoDado.DATA_HORA)
                self.assertEqual(literal.texto, f"'{texto}'")

    def test_converte_data_com_literal_a_esquerda(self) -> None:
        consulta = validar(
            "SELECT Nascimento FROM Cliente "
            "WHERE '2000-01-01' <= Nascimento;"
        )

        self.assertEqual(consulta.condicao.esquerda.tipo, TipoDado.DATA_HORA)
        self.assertEqual(consulta.condicao.esquerda.valor, datetime(2000, 1, 1))

    def test_rejeita_data_hora_invalida(self) -> None:
        for texto in ("31/02/2020", "2023-02-29", ""):
            with self.subTest(texto=texto):
                with self.assertRaises(ErroSemantico) as contexto:
                    validar(
                        "SELECT Nascimento FROM Cliente "
                        f"WHERE Nascimento = '{texto}';"
                    )
                self.assertIn("não é uma data/hora válida", str(contexto.exception))

    def test_texto_com_aparencia_de_data_permanece_texto(self) -> None:
        consulta = validar(
            "SELECT Nome FROM Cliente WHERE Nome = '2000-01-01';"
        )

        literal = consulta.condicao.direita
        self.assertEqual(literal.valor, "2000-01-01")
        self.assertEqual(literal.tipo, TipoDado.TEXTO)

    def test_rejeita_data_hora_com_numero(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar("SELECT Nascimento FROM Cliente WHERE Nascimento = 1;")

        self.assertIn("Tipos incompatíveis", str(contexto.exception))

    def test_validacao_e_idempotente(self) -> None:
        primeira = validar(
            "SELECT Nome FROM Cliente WHERE Nascimento >= '2000-01-01';"
        )

        segunda = validar_consulta(primeira)

        self.assertEqual(segunda, primeira)


class TestValidacaoJuncoes(unittest.TestCase):
    def test_aceita_juncao_pk_fk_oficial(self) -> None:
        consulta = validar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        self.assertEqual(consulta.juncoes[0].tabela, "Pedido")

    def test_aceita_juncao_nao_oficial_e_operador_diferente(self) -> None:
        consulta = validar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente > Pedido.Status_idStatus;"
        )

        self.assertEqual(consulta.juncoes[0].condicao.operador, ">")

    def test_aceita_conexao_na_orientacao_inversa(self) -> None:
        consulta = validar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Pedido.Cliente_idCliente = Cliente.idCliente;"
        )

        self.assertEqual(consulta.juncoes[0].tabela, "Pedido")

    def test_rejeita_literal_em_on(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pedido ON Pedido.ValorTotalPedido > 0;"
            )

        self.assertIn("comparar somente colunas", str(contexto.exception))

    def test_rejeita_tipos_incompativeis_em_on(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pedido ON Cliente.Nome = Pedido.idPedido;"
            )

        self.assertIn("Tipos incompatíveis", str(contexto.exception))

    def test_rejeita_on_que_usa_apenas_tabela_anterior(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pedido ON Cliente.idCliente = "
                "Cliente.TipoCliente_idTipoCliente;"
            )

        self.assertIn("deve conectá-la", str(contexto.exception))

    def test_rejeita_on_que_usa_apenas_nova_tabela(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pedido ON Pedido.idPedido = Pedido.Status_idStatus;"
            )

        self.assertIn("deve conectá-la", str(contexto.exception))

    def test_condicao_composta_precisa_de_ao_menos_uma_aresta(self) -> None:
        consulta = validar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "AND Cliente.idCliente = Cliente.TipoCliente_idTipoCliente;"
        )

        self.assertIsInstance(consulta.juncoes[0].condicao, Conjuncao)

    def test_on_extenso_encontra_conexao_sem_estourar_recursao(self) -> None:
        condicoes_locais = " AND ".join(
            "Cliente.idCliente = Cliente.TipoCliente_idTipoCliente"
            for _ in range(1100)
        )
        sql = (
            "SELECT Cliente.Nome FROM Cliente JOIN Pedido ON "
            f"{condicoes_locais} AND "
            "Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        consulta = validar(sql)

        self.assertEqual(consulta.juncoes[0].tabela, "Pedido")

    def test_segunda_juncao_deve_usar_a_nova_tabela(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            validar(
                "SELECT Cliente.Nome FROM Cliente "
                "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
                "JOIN Status ON Cliente.idCliente = Pedido.Status_idStatus;"
            )

        self.assertIn("tabela 'Status'", str(contexto.exception))


class TestValidacaoConsultasReferencia(unittest.TestCase):
    def test_preserva_ordem_das_projecoes(self) -> None:
        consulta = validar(CONSULTAS_REFERENCIA[0])

        self.assertEqual(
            tuple((coluna.tabela, coluna.nome) for coluna in consulta.colunas),
            (
                ("Cliente", "Nome"),
                ("Pedido", "idPedido"),
                ("Pedido", "DataPedido"),
                ("Pedido", "ValorTotalPedido"),
            ),
        )

    def test_consultas_de_referencia_sao_validadas(self) -> None:
        quantidades_juncoes = (1, 2, 4, 7)

        for indice, (sql, quantidade) in enumerate(
            zip(CONSULTAS_REFERENCIA, quantidades_juncoes, strict=True),
            start=1,
        ):
            with self.subTest(consulta=indice):
                consulta = validar(sql)
                self.assertEqual(len(consulta.juncoes), quantidade)
                self.assertTrue(
                    all(coluna.tipo is not None for coluna in consulta.colunas)
                )
                self.assertEqual(consulta.tabela_origem, "Cliente")


if __name__ == "__main__":
    unittest.main()
