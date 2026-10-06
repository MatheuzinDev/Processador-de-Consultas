import unittest

from core.catalogo import CATALOGO
from core.modelos import TipoDado


COLUNAS_ESPERADAS = {
    "Categoria": ("idCategoria", "Descricao"),
    "Produto": (
        "idProduto",
        "Nome",
        "Descricao",
        "Preco",
        "QuantEstoque",
        "Categoria_idCategoria",
    ),
    "TipoCliente": ("idTipoCliente", "Descricao"),
    "Cliente": (
        "idCliente",
        "Nome",
        "Email",
        "Nascimento",
        "Senha",
        "TipoCliente_idTipoCliente",
        "DataRegistro",
    ),
    "TipoEndereco": ("idTipoEndereco", "Descricao"),
    "Endereco": (
        "idEndereco",
        "EnderecoPadrao",
        "Logradouro",
        "Numero",
        "Complemento",
        "Bairro",
        "Cidade",
        "UF",
        "CEP",
        "TipoEndereco_idTipoEndereco",
        "Cliente_idCliente",
    ),
    "Telefone": ("Numero", "Cliente_idCliente"),
    "Status": ("idStatus", "Descricao"),
    "Pedido": (
        "idPedido",
        "Status_idStatus",
        "DataPedido",
        "ValorTotalPedido",
        "Cliente_idCliente",
    ),
    "Pedido_has_Produto": (
        "idPedidoProduto",
        "Pedido_idPedido",
        "Produto_idProduto",
        "Quantidade",
        "PrecoUnitario",
    ),
}

CHAVES_PRIMARIAS_ESPERADAS = {
    "Categoria": "idCategoria",
    "Produto": "idProduto",
    "TipoCliente": "idTipoCliente",
    "Cliente": "idCliente",
    "TipoEndereco": "idTipoEndereco",
    "Endereco": "idEndereco",
    "Telefone": "Numero",
    "Status": "idStatus",
    "Pedido": "idPedido",
    "Pedido_has_Produto": "idPedidoProduto",
}

TIPOS_ESPERADOS = {
    "Categoria": (TipoDado.INTEIRO, TipoDado.TEXTO),
    "Produto": (
        TipoDado.INTEIRO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.DECIMAL,
        TipoDado.DECIMAL,
        TipoDado.INTEIRO,
    ),
    "TipoCliente": (TipoDado.INTEIRO, TipoDado.TEXTO),
    "Cliente": (
        TipoDado.INTEIRO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.DATA_HORA,
        TipoDado.TEXTO,
        TipoDado.INTEIRO,
        TipoDado.DATA_HORA,
    ),
    "TipoEndereco": (TipoDado.INTEIRO, TipoDado.TEXTO),
    "Endereco": (
        TipoDado.INTEIRO,
        TipoDado.INTEIRO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.TEXTO,
        TipoDado.INTEIRO,
        TipoDado.INTEIRO,
    ),
    "Telefone": (TipoDado.TEXTO, TipoDado.INTEIRO),
    "Status": (TipoDado.INTEIRO, TipoDado.TEXTO),
    "Pedido": (
        TipoDado.INTEIRO,
        TipoDado.INTEIRO,
        TipoDado.DATA_HORA,
        TipoDado.DECIMAL,
        TipoDado.INTEIRO,
    ),
    "Pedido_has_Produto": (
        TipoDado.INTEIRO,
        TipoDado.INTEIRO,
        TipoDado.INTEIRO,
        TipoDado.DECIMAL,
        TipoDado.DECIMAL,
    ),
}

CHAVES_ESTRANGEIRAS_ESPERADAS = {
    ("Produto", "Categoria_idCategoria", "Categoria", "idCategoria"),
    ("Cliente", "TipoCliente_idTipoCliente", "TipoCliente", "idTipoCliente"),
    (
        "Endereco",
        "TipoEndereco_idTipoEndereco",
        "TipoEndereco",
        "idTipoEndereco",
    ),
    ("Endereco", "Cliente_idCliente", "Cliente", "idCliente"),
    ("Telefone", "Cliente_idCliente", "Cliente", "idCliente"),
    ("Pedido", "Status_idStatus", "Status", "idStatus"),
    ("Pedido", "Cliente_idCliente", "Cliente", "idCliente"),
    ("Pedido_has_Produto", "Pedido_idPedido", "Pedido", "idPedido"),
    ("Pedido_has_Produto", "Produto_idProduto", "Produto", "idProduto"),
}


class TestCatalogo(unittest.TestCase):
    def test_catalogo_contem_as_dez_tabelas_na_ordem_definida(self) -> None:
        self.assertEqual(
            tuple(tabela.nome for tabela in CATALOGO.tabelas),
            tuple(COLUNAS_ESPERADAS),
        )

    def test_tabelas_contem_as_colunas_e_tipos_corretos(self) -> None:
        for nome_tabela, nomes_colunas in COLUNAS_ESPERADAS.items():
            with self.subTest(tabela=nome_tabela):
                tabela = CATALOGO.buscar_tabela(nome_tabela)
                self.assertIsNotNone(tabela)
                self.assertEqual(
                    tuple(coluna.nome for coluna in tabela.colunas),
                    nomes_colunas,
                )
                self.assertEqual(
                    tuple(coluna.tipo for coluna in tabela.colunas),
                    TIPOS_ESPERADOS[nome_tabela],
                )

    def test_cada_tabela_possui_exatamente_uma_chave_primaria(self) -> None:
        for tabela in CATALOGO.tabelas:
            with self.subTest(tabela=tabela.nome):
                chaves = tuple(
                    coluna.nome for coluna in tabela.colunas if coluna.chave_primaria
                )
                self.assertEqual(chaves, (CHAVES_PRIMARIAS_ESPERADAS[tabela.nome],))

    def test_numero_e_a_chave_primaria_de_telefone(self) -> None:
        numero = CATALOGO.buscar_coluna("Telefone", "Numero")

        self.assertIsNotNone(numero)
        self.assertTrue(numero.chave_primaria)
        self.assertEqual(numero.tipo, TipoDado.TEXTO)

    def test_busca_de_tabela_ignora_caixa_e_preserva_nome_canonico(self) -> None:
        for nome in ("cliente", "CLIENTE", "Cliente"):
            with self.subTest(nome=nome):
                tabela = CATALOGO.buscar_tabela(nome)
                self.assertIsNotNone(tabela)
                self.assertEqual(tabela.nome, "Cliente")

    def test_busca_de_tabela_inexistente_retorna_none(self) -> None:
        self.assertIsNone(CATALOGO.buscar_tabela("Pessoa"))

    def test_busca_de_coluna_ignora_caixa_e_preserva_nome_canonico(self) -> None:
        coluna = CATALOGO.buscar_coluna("CLIENTE", "email")

        self.assertIsNotNone(coluna)
        self.assertEqual(coluna.nome, "Email")
        self.assertEqual(coluna.tipo, TipoDado.TEXTO)

    def test_busca_de_coluna_inexistente_retorna_none(self) -> None:
        self.assertIsNone(CATALOGO.buscar_coluna("Cliente", "Apelido"))
        self.assertIsNone(CATALOGO.buscar_coluna("Pessoa", "Nome"))

    def test_busca_de_ocorrencias_preserva_ordem_das_tabelas(self) -> None:
        ocorrencias = CATALOGO.buscar_tabelas_com_coluna(
            ("Status", "Categoria", "Produto"),
            "descricao",
        )

        self.assertEqual(
            tuple(tabela.nome for tabela, _ in ocorrencias),
            ("Status", "Categoria", "Produto"),
        )
        self.assertTrue(all(coluna.nome == "Descricao" for _, coluna in ocorrencias))

    def test_busca_de_ocorrencias_inexistentes_retorna_tupla_vazia(self) -> None:
        self.assertEqual(
            CATALOGO.buscar_tabelas_com_coluna(("Cliente", "Pedido"), "Apelido"),
            (),
        )

    def test_catalogo_contem_as_nove_chaves_estrangeiras(self) -> None:
        relacionamentos = {
            (
                chave.tabela_origem,
                chave.coluna_origem,
                chave.tabela_destino,
                chave.coluna_destino,
            )
            for chave in CATALOGO.chaves_estrangeiras
        }

        self.assertEqual(relacionamentos, CHAVES_ESTRANGEIRAS_ESPERADAS)

    def test_relacionamento_e_encontrado_nas_duas_orientacoes(self) -> None:
        direto = CATALOGO.buscar_relacionamento(
            "Pedido",
            "Cliente_idCliente",
            "Cliente",
            "idCliente",
        )
        inverso = CATALOGO.buscar_relacionamento(
            "cliente",
            "IDCLIENTE",
            "pedido",
            "cliente_idcliente",
        )

        self.assertIsNotNone(direto)
        self.assertIs(direto, inverso)

    def test_relacionamento_inexistente_retorna_none(self) -> None:
        self.assertIsNone(
            CATALOGO.buscar_relacionamento(
                "Cliente",
                "Nome",
                "Produto",
                "Nome",
            )
        )

    def test_chaves_estrangeiras_referenciam_colunas_validas_e_compativeis(self) -> None:
        for chave in CATALOGO.chaves_estrangeiras:
            with self.subTest(
                origem=f"{chave.tabela_origem}.{chave.coluna_origem}",
                destino=f"{chave.tabela_destino}.{chave.coluna_destino}",
            ):
                coluna_origem = CATALOGO.buscar_coluna(
                    chave.tabela_origem,
                    chave.coluna_origem,
                )
                coluna_destino = CATALOGO.buscar_coluna(
                    chave.tabela_destino,
                    chave.coluna_destino,
                )
                self.assertIsNotNone(coluna_origem)
                self.assertIsNotNone(coluna_destino)
                self.assertTrue(coluna_destino.chave_primaria)
                self.assertEqual(coluna_origem.tipo, coluna_destino.tipo)


if __name__ == "__main__":
    unittest.main()
