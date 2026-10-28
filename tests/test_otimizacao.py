import unittest

from core.erros import ErroSemantico
from core.otimizacao import (
    NoAlgebra,
    otimizar_consulta,
    para_dicionario,
    para_html,
    para_texto,
)
from core.parser import parsear
from core.processador import processar_consulta


_CONSULTA_DUAS_TABELAS = (
    "SELECT Cliente.Nome, Pedido.idPedido, Pedido.DataPedido, "
    "Pedido.ValorTotalPedido FROM Cliente "
    "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
    "WHERE Cliente.TipoCliente_idTipoCliente = 1 "
    "AND Pedido.ValorTotalPedido = 0;"
)

_CONSULTA_CINCO_TABELAS = (
    "SELECT Cliente.Nome, Pedido.idPedido, Pedido.DataPedido, "
    "Status.Descricao, Pedido.ValorTotalPedido, Produto.QuantEstoque "
    "FROM Cliente JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
    "JOIN Status ON Status.idStatus = Pedido.Status_idStatus "
    "JOIN Pedido_has_Produto ON Pedido.idPedido = Pedido_has_Produto.Pedido_idPedido "
    "JOIN Produto ON Produto.idProduto = Pedido_has_Produto.Produto_idProduto "
    "WHERE Status.Descricao = 'Aberto' "
    "AND Cliente.TipoCliente_idTipoCliente = 1 "
    "AND Pedido.ValorTotalPedido = 0 AND Produto.QuantEstoque > 0;"
)

_CONSULTA_OITO_TABELAS = (
    "SELECT Cliente.Nome, TipoCliente.Descricao, Pedido.idPedido, "
    "Pedido.DataPedido, Status.Descricao, Pedido.ValorTotalPedido, "
    "Categoria.Descricao, Produto.QuantEstoque "
    "FROM Cliente JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
    "JOIN TipoCliente ON Cliente.TipoCliente_idTipoCliente = TipoCliente.idTipoCliente "
    "JOIN Endereco ON Cliente.idCliente = Endereco.Cliente_idCliente "
    "JOIN Status ON Status.idStatus = Pedido.Status_idStatus "
    "JOIN Pedido_has_Produto ON Pedido.idPedido = Pedido_has_Produto.Pedido_idPedido "
    "JOIN Produto ON Produto.idProduto = Pedido_has_Produto.Produto_idProduto "
    "JOIN Categoria ON Categoria.idCategoria = Produto.Categoria_idCategoria "
    "WHERE Status.Descricao = 'Aberto' AND Cliente.Email = 'Luffy@gmail.com' "
    "AND Pedido.ValorTotalPedido = 0;"
)


def _nos(no: NoAlgebra) -> list[NoAlgebra]:
    resultado = [no]
    for filho in no.filhos:
        resultado.extend(_nos(filho))
    return resultado


def _nos_do_tipo(no: NoAlgebra, tipo: str) -> list[NoAlgebra]:
    return [atual for atual in _nos(no) if atual.tipo == tipo]


def _ramo_da_tabela(no: NoAlgebra, tabela: str) -> list[str]:
    """Tipos dos nós logo abaixo de uma junção até a folha da tabela."""
    for juncao in _nos_do_tipo(no, "Juncao"):
        for filho in juncao.filhos:
            caminho = []
            atual = filho
            while atual.tipo in ("Projecao", "Filtro", "Tabela"):
                caminho.append(atual.tipo)
                if atual.tipo == "Tabela":
                    if atual.tabela == tabela:
                        return caminho
                    break
                atual = atual.filhos[0]
    return []


def _ordem_folhas(no: NoAlgebra) -> list[str]:
    return [atual.tabela for atual in _nos(no) if atual.tipo == "Tabela"]


def _otimizar(sql: str):
    return otimizar_consulta(processar_consulta(sql))


class TestOtimizacao(unittest.TestCase):
    def test_registra_as_quatro_heuristicas_em_ordem(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        self.assertEqual(
            [passo.heuristica for passo in resultado.passos],
            [
                "Heurística de junção",
                "Heurística de redução de tuplas",
                "Heurística de redução de atributos",
                "Heurística de seleções e junções mais restritivas",
            ],
        )
        self.assertEqual(resultado.passos[-1].expressao, para_texto(resultado.arvore))

    def test_raiz_e_a_projecao_final(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        self.assertEqual(resultado.arvore.tipo, "Projecao")
        self.assertEqual(
            [coluna.nome for coluna in resultado.arvore.colunas],
            ["Nome", "idPedido", "DataPedido", "ValorTotalPedido"],
        )

    def test_selecoes_descem_para_cima_da_propria_tabela(self) -> None:
        arvore = _otimizar(_CONSULTA_DUAS_TABELAS).arvore

        filtros = _nos_do_tipo(arvore, "Filtro")
        self.assertEqual(len(filtros), 2)
        for filtro in filtros:
            folha = filtro.filhos[0]
            self.assertEqual(folha.tipo, "Tabela")
            tabelas = {
                comparacao.esquerda.tabela for comparacao in filtro.condicoes
            }
            self.assertEqual(tabelas, {folha.tabela})

    def test_nenhum_filtro_acima_das_juncoes(self) -> None:
        arvore = _otimizar(_CONSULTA_CINCO_TABELAS).arvore

        for juncao in _nos_do_tipo(arvore, "Juncao"):
            for no in _nos(juncao):
                if no.tipo == "Filtro":
                    self.assertEqual(no.filhos[0].tipo, "Tabela")

    def test_projecoes_mantem_so_colunas_do_select_e_das_juncoes(self) -> None:
        arvore = _otimizar(_CONSULTA_DUAS_TABELAS).arvore

        projecoes = {
            no.filhos[0].filhos[0].tabela: [coluna.nome for coluna in no.colunas]
            for no in _nos_do_tipo(arvore, "Projecao")
            if no is not arvore
        }
        self.assertEqual(
            projecoes,
            {
                "Cliente": ["idCliente", "Nome"],
                "Pedido": [
                    "idPedido",
                    "DataPedido",
                    "ValorTotalPedido",
                    "Cliente_idCliente",
                ],
            },
        )

    def test_projecao_fica_acima_da_selecao(self) -> None:
        arvore = _otimizar(_CONSULTA_DUAS_TABELAS).arvore

        self.assertEqual(
            _ramo_da_tabela(arvore, "Cliente"),
            ["Projecao", "Filtro", "Tabela"],
        )

    def test_omite_projecao_quando_todas_as_colunas_sao_usadas(self) -> None:
        arvore = _otimizar(
            "SELECT Status.Descricao FROM Pedido "
            "JOIN Status ON Pedido.Status_idStatus = Status.idStatus;"
        ).arvore

        self.assertEqual(_ramo_da_tabela(arvore, "Status"), ["Tabela"])

    def test_evita_produto_cartesiano_nos_exemplos(self) -> None:
        for sql, quantidade_tabelas in (
            (_CONSULTA_DUAS_TABELAS, 2),
            (_CONSULTA_CINCO_TABELAS, 5),
            (_CONSULTA_OITO_TABELAS, 8),
        ):
            with self.subTest(tabelas=quantidade_tabelas):
                arvore = _otimizar(sql).arvore
                self.assertEqual(_nos_do_tipo(arvore, "Produto"), [])
                self.assertEqual(
                    len(_nos_do_tipo(arvore, "Juncao")),
                    quantidade_tabelas - 1,
                )

    def test_tabela_sem_condicao_de_juncao_gera_erro_em_vez_de_produto(self) -> None:
        # A validação já barra essa consulta; aqui ela chega direto do parser.
        consulta = parsear(
            "SELECT Cliente.Nome FROM Cliente JOIN Status "
            "ON Cliente.idCliente = Cliente.TipoCliente_idTipoCliente;"
        )

        with self.assertRaises(ErroSemantico) as contexto:
            otimizar_consulta(consulta)

        self.assertIn("a tabela 'Status' não tem condição de junção", str(contexto.exception))
        self.assertIn("produto cartesiano não é suportado", str(contexto.exception))

    def test_tabela_mais_restritiva_entra_primeiro(self) -> None:
        arvore = _otimizar(
            "SELECT Cliente.Nome, Pedido.DataPedido FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Cliente.Nome <> 'Ana' AND Pedido.idPedido = 10;"
        ).arvore

        self.assertEqual(_ordem_folhas(arvore), ["Pedido", "Cliente"])

    def test_igualdade_em_chave_primaria_vence_igualdade_comum(self) -> None:
        arvore = _otimizar(
            "SELECT Cliente.Nome, Pedido.DataPedido FROM Pedido "
            "JOIN Cliente ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Pedido.ValorTotalPedido = 0 AND Cliente.idCliente = 7;"
        ).arvore

        self.assertEqual(_ordem_folhas(arvore), ["Cliente", "Pedido"])

    def test_reordenacao_respeita_conexao_entre_tabelas(self) -> None:
        # Produto tem seleção, mas só se liga a Pedido via Pedido_has_Produto.
        arvore = _otimizar(_CONSULTA_CINCO_TABELAS).arvore

        ordem = _ordem_folhas(arvore)
        self.assertLess(
            ordem.index("Pedido_has_Produto"),
            ordem.index("Produto"),
        )

    def test_empate_mantem_ordem_original(self) -> None:
        arvore = _otimizar(_CONSULTA_DUAS_TABELAS).arvore

        self.assertEqual(_ordem_folhas(arvore), ["Cliente", "Pedido"])

    def test_comparacao_entre_tabelas_no_where_vira_condicao_de_juncao(self) -> None:
        arvore = _otimizar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Pedido.ValorTotalPedido > Cliente.TipoCliente_idTipoCliente;"
        ).arvore

        self.assertEqual(_nos_do_tipo(arvore, "Filtro"), [])
        (juncao,) = _nos_do_tipo(arvore, "Juncao")
        self.assertEqual(len(juncao.condicoes), 2)

    def test_consulta_de_uma_tabela_sem_where(self) -> None:
        resultado = _otimizar("SELECT Nome FROM Cliente;")

        self.assertEqual(para_texto(resultado.arvore), "π_{Cliente.Nome}(Cliente)")

    def test_consulta_de_uma_tabela_com_where(self) -> None:
        resultado = _otimizar("SELECT Nome FROM Cliente WHERE idCliente = 1;")

        self.assertEqual(
            para_texto(resultado.arvore),
            "π_{Cliente.Nome}(σ_{Cliente.idCliente = 1}(Cliente))",
        )

    def test_descricoes_de_consulta_de_uma_tabela_nao_citam_juncoes(self) -> None:
        resultado = _otimizar(
            "SELECT Cliente.Nome FROM Cliente "
            "WHERE Cliente.TipoCliente_idTipoCliente = 1;"
        )

        for passo in resultado.passos:
            with self.subTest(heuristica=passo.heuristica):
                self.assertTrue(
                    passo.descricao.startswith("Consulta com uma única tabela")
                )
                self.assertNotIn("reordenadas", passo.descricao)

    def test_ordem_mantida_nao_e_descrita_como_reordenada(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        descricao = resultado.passos[-1].descricao
        self.assertNotIn("reordenadas", descricao)
        self.assertIn("nenhuma reordenação foi necessária", descricao)

    def test_ordem_alterada_e_descrita_como_reordenada(self) -> None:
        resultado = _otimizar(
            "SELECT Cliente.Nome, Pedido.DataPedido FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Cliente.Nome <> 'Ana' AND Pedido.idPedido = 10;"
        )

        self.assertTrue(
            resultado.passos[-1].descricao.startswith("Folhas reordenadas")
        )

    def test_texto_da_arvore_otimizada(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        self.assertEqual(
            para_texto(resultado.arvore),
            "π_{Cliente.Nome, Pedido.idPedido, Pedido.DataPedido, "
            "Pedido.ValorTotalPedido}("
            "(π_{Cliente.idCliente, Cliente.Nome}"
            "(σ_{Cliente.TipoCliente_idTipoCliente = 1}(Cliente)) "
            "⨝_{Cliente.idCliente = Pedido.Cliente_idCliente} "
            "π_{Pedido.idPedido, Pedido.DataPedido, Pedido.ValorTotalPedido, "
            "Pedido.Cliente_idCliente}(σ_{Pedido.ValorTotalPedido = 0}(Pedido))))",
        )

    def test_cada_passo_guarda_a_propria_arvore(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        for passo in resultado.passos:
            with self.subTest(heuristica=passo.heuristica):
                self.assertEqual(passo.expressao, para_texto(passo.arvore))
        self.assertIs(resultado.passos[-1].arvore, resultado.arvore)

    def test_html_segue_o_estilo_da_algebra_relacional(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        html = para_html(resultado.arvore)
        self.assertTrue(html.startswith("<span style='font-size: 20px; color: #bd4a3c;'>π</span>"))
        self.assertIn("color: #f0b84b;'>σ</span>", html)
        self.assertIn("color: #d9f45d;'>⨝</span>", html)
        self.assertIn("<b>Cliente</b>", html)
        self.assertIn("<sub>Cliente.idCliente = Pedido.Cliente_idCliente</sub>", html)

    def test_html_coloca_parenteses_em_cada_lado_da_juncao(self) -> None:
        resultado = _otimizar(_CONSULTA_DUAS_TABELAS)

        html = para_html(resultado.passos[1].arvore)
        self.assertIn("Pedido.Cliente_idCliente</sub> (<span", html)
        self.assertIn("(<b>Cliente</b>))", html)

    def test_html_escapa_operadores_e_textos(self) -> None:
        resultado = _otimizar(
            "SELECT Cliente.Nome FROM Cliente WHERE Cliente.Nome <> 'Ana';"
        )

        html = para_html(resultado.arvore)
        self.assertIn("Cliente.Nome &lt;&gt; &#x27;Ana&#x27;", html)
        self.assertNotIn("<>", html)

    def test_dicionario_compativel_com_grafo(self) -> None:
        arvore = _otimizar(_CONSULTA_DUAS_TABELAS).arvore

        dicionario = para_dicionario(arvore)
        ids = []

        def visitar(no: dict) -> None:
            self.assertEqual(
                set(no),
                {"id", "label", "tipo", "filhos", "ast_no"},
            )
            ids.append(no["id"])
            for filho in no["filhos"]:
                visitar(filho)

        visitar(dicionario)
        self.assertEqual(dicionario["tipo"], "Projecao")
        self.assertTrue(dicionario["label"].startswith("π\n"))
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
