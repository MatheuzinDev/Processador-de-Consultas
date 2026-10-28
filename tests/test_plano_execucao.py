import unittest

from core.catalogo import CATALOGO
from core.modelos import ReferenciaColuna, TipoDado
from core.otimizacao import NoAlgebra, otimizar_consulta
from core.plano_execucao import (
    HEURISTICA_ATRIBUTOS,
    HEURISTICA_JUNCAO,
    HEURISTICA_RESTRITIVAS,
    HEURISTICA_TUPLAS,
    PassoExecucao,
    PlanoExecucao,
    gerar_plano_execucao,
    plano_para_texto,
)
from core.processador import processar_consulta

_CONSULTA_UMA_TABELA = "SELECT Nome FROM Cliente;"

_CONSULTA_UMA_TABELA_COM_WHERE = (
    "SELECT Nome FROM Cliente WHERE TipoCliente_idTipoCliente = 1;"
)

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

_CONSULTAS = (
    _CONSULTA_UMA_TABELA,
    _CONSULTA_UMA_TABELA_COM_WHERE,
    _CONSULTA_DUAS_TABELAS,
    _CONSULTA_CINCO_TABELAS,
    _CONSULTA_OITO_TABELAS,
)


def _otimizar(sql: str):
    return otimizar_consulta(processar_consulta(sql))


def _plano(sql: str) -> PlanoExecucao:
    return gerar_plano_execucao(_otimizar(sql).arvore)


def _nos_em_pos_ordem(no: NoAlgebra) -> list[NoAlgebra]:
    resultado = []
    for filho in no.filhos:
        resultado.extend(_nos_em_pos_ordem(filho))
    resultado.append(no)
    return resultado


def _passos_do_tipo(plano: PlanoExecucao, tipo: str) -> list[PassoExecucao]:
    return [passo for passo in plano.passos if passo.tipo == tipo]


def _coluna(tabela: str, nome: str) -> ReferenciaColuna:
    return ReferenciaColuna(nome, tabela, TipoDado.INTEIRO)


class TestPlanoExecucao(unittest.TestCase):
    def test_segue_ordem_pos_ordem_do_grafo_otimizado(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                arvore = _otimizar(sql).arvore
                plano = gerar_plano_execucao(arvore)

                esperado = [no.tipo for no in _nos_em_pos_ordem(arvore)]
                self.assertEqual([passo.tipo for passo in plano.passos], esperado)

    def test_um_passo_por_no_do_grafo(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                arvore = _otimizar(sql).arvore
                plano = gerar_plano_execucao(arvore)

                self.assertEqual(
                    len(plano.passos),
                    len(_nos_em_pos_ordem(arvore)),
                )

    def test_numeracao_e_resultados_sequenciais(self) -> None:
        plano = _plano(_CONSULTA_CINCO_TABELAS)

        self.assertEqual(
            [passo.numero for passo in plano.passos],
            list(range(1, len(plano.passos) + 1)),
        )
        self.assertEqual(
            [passo.resultado for passo in plano.passos],
            [f"R{numero}" for numero in range(1, len(plano.passos) + 1)],
        )

    def test_entradas_sao_sempre_resultados_ja_produzidos(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                plano = _plano(sql)
                produzidos = set()
                for passo in plano.passos:
                    self.assertLessEqual(set(passo.entradas), produzidos)
                    produzidos.add(passo.resultado)

    def test_cada_resultado_intermediario_e_consumido_uma_vez(self) -> None:
        plano = _plano(_CONSULTA_OITO_TABELAS)

        consumos = [entrada for passo in plano.passos for entrada in passo.entradas]
        intermediarios = [passo.resultado for passo in plano.passos[:-1]]
        self.assertEqual(sorted(consumos), sorted(intermediarios))

    def test_ultimo_passo_e_a_projecao_final(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                plano = _plano(sql)

                ultimo = plano.passos[-1]
                self.assertEqual(ultimo.tipo, "Projecao")
                self.assertEqual(ultimo.operacao, "Projeção final (π)")
                self.assertEqual(plano.resultado_final, ultimo.resultado)
                self.assertEqual(
                    [p.operacao for p in plano.passos].count("Projeção final (π)"),
                    1,
                )

    def test_primeiros_passos_sao_leituras_de_tabela(self) -> None:
        plano = _plano(_CONSULTA_DUAS_TABELAS)

        self.assertEqual(plano.passos[0].tipo, "Tabela")
        self.assertEqual(plano.passos[0].entradas, ())
        self.assertEqual(plano.passos[0].operacao, "Leitura de tabela")

    def test_leituras_seguem_ordem_das_folhas_do_grafo(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                arvore = _otimizar(sql).arvore
                plano = gerar_plano_execucao(arvore)

                folhas = [
                    no.tabela
                    for no in _nos_em_pos_ordem(arvore)
                    if no.tipo == "Tabela"
                ]
                self.assertEqual(
                    [passo.expressao for passo in _passos_do_tipo(plano, "Tabela")],
                    folhas,
                )

    def test_nenhuma_selecao_consome_resultado_de_juncao(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                plano = _plano(sql)
                for selecao in _passos_do_tipo(plano, "Filtro"):
                    entrada = plano.passos[int(selecao.entradas[0][1:]) - 1]
                    self.assertEqual(entrada.tipo, "Tabela")

    def test_cada_selecao_vem_logo_apos_a_leitura_da_propria_tabela(self) -> None:
        plano = _plano(_CONSULTA_OITO_TABELAS)

        for selecao in _passos_do_tipo(plano, "Filtro"):
            anterior = plano.passos[selecao.numero - 2]
            self.assertEqual(anterior.tipo, "Tabela")
            self.assertEqual(selecao.entradas, (anterior.resultado,))

    def test_consulta_de_uma_tabela_gera_leitura_e_projecao_final(self) -> None:
        plano = _plano(_CONSULTA_UMA_TABELA)

        self.assertEqual(
            [passo.tipo for passo in plano.passos],
            ["Tabela", "Projecao"],
        )
        self.assertEqual(plano.passos[0].heuristicas, ())
        self.assertEqual(plano.passos[0].justificativa, "Única tabela da consulta.")
        self.assertEqual(plano.passos[1].expressao, "π_{Cliente.Nome}(R1)")

    def test_consulta_de_uma_tabela_com_where_aplica_selecao(self) -> None:
        plano = _plano(_CONSULTA_UMA_TABELA_COM_WHERE)

        self.assertEqual(
            [passo.tipo for passo in plano.passos],
            ["Tabela", "Filtro", "Projecao"],
        )
        self.assertEqual(plano.passos[1].heuristicas, (HEURISTICA_TUPLAS,))
        self.assertEqual(
            plano.passos[1].expressao,
            "σ_{Cliente.TipoCliente_idTipoCliente = 1}(R1)",
        )

    def test_expressoes_do_plano_de_duas_tabelas(self) -> None:
        plano = _plano(_CONSULTA_DUAS_TABELAS)

        self.assertEqual(
            [passo.expressao for passo in plano.passos],
            [
                "Cliente",
                "σ_{Cliente.TipoCliente_idTipoCliente = 1}(R1)",
                "π_{Cliente.idCliente, Cliente.Nome}(R2)",
                "Pedido",
                "σ_{Pedido.ValorTotalPedido = 0}(R4)",
                "π_{Pedido.idPedido, Pedido.DataPedido, "
                "Pedido.ValorTotalPedido, Pedido.Cliente_idCliente}(R5)",
                "R3 ⨝_{Cliente.idCliente = Pedido.Cliente_idCliente} R6",
                "π_{Cliente.Nome, Pedido.idPedido, Pedido.DataPedido, "
                "Pedido.ValorTotalPedido}(R7)",
            ],
        )

    def test_heuristicas_por_tipo_de_operacao(self) -> None:
        plano = _plano(_CONSULTA_CINCO_TABELAS)

        for passo in plano.passos:
            with self.subTest(passo=passo.numero):
                if passo.tipo == "Tabela":
                    self.assertEqual(passo.heuristicas, (HEURISTICA_RESTRITIVAS,))
                elif passo.tipo == "Filtro":
                    self.assertEqual(passo.heuristicas, (HEURISTICA_TUPLAS,))
                elif passo.tipo == "Projecao":
                    self.assertEqual(passo.heuristicas, (HEURISTICA_ATRIBUTOS,))
                elif passo.tipo == "Juncao":
                    self.assertEqual(
                        passo.heuristicas,
                        (HEURISTICA_JUNCAO, HEURISTICA_RESTRITIVAS),
                    )

    def test_todo_passo_de_consulta_com_juncao_tem_heuristica(self) -> None:
        for sql in _CONSULTAS[2:]:
            with self.subTest(sql=sql):
                for passo in _plano(sql).passos:
                    self.assertTrue(passo.heuristicas)
                    self.assertTrue(passo.justificativa)

    def test_nomes_das_heuristicas_coincidem_com_os_passos_da_otimizacao(self) -> None:
        nomes_otimizacao = {
            passo.heuristica for passo in _otimizar(_CONSULTA_DUAS_TABELAS).passos
        }

        self.assertEqual(
            nomes_otimizacao,
            {
                HEURISTICA_JUNCAO,
                HEURISTICA_TUPLAS,
                HEURISTICA_ATRIBUTOS,
                HEURISTICA_RESTRITIVAS,
            },
        )

    def test_consultas_validas_nao_geram_produto_cartesiano(self) -> None:
        for sql in _CONSULTAS:
            with self.subTest(sql=sql):
                self.assertEqual(_passos_do_tipo(_plano(sql), "Produto"), [])

    def test_quantidade_de_juncoes_acompanha_a_consulta(self) -> None:
        casos = (
            (_CONSULTA_UMA_TABELA, 0),
            (_CONSULTA_DUAS_TABELAS, 1),
            (_CONSULTA_CINCO_TABELAS, 4),
            (_CONSULTA_OITO_TABELAS, 7),
        )

        for sql, quantidade in casos:
            with self.subTest(sql=sql):
                self.assertEqual(
                    len(_passos_do_tipo(_plano(sql), "Juncao")),
                    quantidade,
                )

    def test_projecoes_intermediarias_informam_reducao_de_atributos(self) -> None:
        plano = _plano(_CONSULTA_DUAS_TABELAS)

        projecoes = _passos_do_tipo(plano, "Projecao")[:-1]
        self.assertEqual(len(projecoes), 2)
        self.assertIn("Mantém 2 de 7 atributos de Cliente", projecoes[0].justificativa)
        self.assertIn("Mantém 4 de 5 atributos de Pedido", projecoes[1].justificativa)

    def test_justificativa_da_leitura_informa_posicao_e_selecao(self) -> None:
        plano = _plano(_CONSULTA_CINCO_TABELAS)

        leituras = _passos_do_tipo(plano, "Tabela")
        total = len(leituras)
        for posicao, leitura in enumerate(leituras, start=1):
            self.assertIn(f"Folha {posicao} de {total}", leitura.justificativa)
        com_selecao = {
            leitura.expressao
            for leitura in leituras
            if "com seleção antecipada" in leitura.justificativa
        }
        self.assertEqual(com_selecao, {"Status", "Cliente", "Pedido", "Produto"})

    def test_juncao_informa_tabela_que_entra_na_posicao(self) -> None:
        plano = _plano(_CONSULTA_CINCO_TABELAS)

        tabelas = [
            leitura.expressao for leitura in _passos_do_tipo(plano, "Tabela")
        ]
        juncoes = _passos_do_tipo(plano, "Juncao")
        for juncao, tabela in zip(juncoes, tabelas[1:]):
            self.assertIn(f"{tabela} entra nesta posição", juncao.justificativa)

    def test_primeira_leitura_e_a_tabela_mais_restritiva(self) -> None:
        plano = _plano(
            "SELECT Cliente.Nome, Pedido.idPedido FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Cliente.Nome = 'Ana' AND Pedido.idPedido = 10;"
        )

        leituras = _passos_do_tipo(plano, "Tabela")
        self.assertEqual([leitura.expressao for leitura in leituras], ["Pedido", "Cliente"])
        juncao = _passos_do_tipo(plano, "Juncao")[0]
        self.assertIn("Cliente entra nesta posição", juncao.justificativa)

    def test_empate_de_restritividade_mantem_ordem_da_consulta(self) -> None:
        plano = _plano(_CONSULTA_DUAS_TABELAS)

        leituras = _passos_do_tipo(plano, "Tabela")
        self.assertEqual([leitura.expressao for leitura in leituras], ["Cliente", "Pedido"])

    def test_produto_cartesiano_e_listado_quando_nao_ha_condicao(self) -> None:
        arvore = NoAlgebra(
            "Projecao",
            (
                NoAlgebra(
                    "Produto",
                    (
                        NoAlgebra("Tabela", tabela="Cliente"),
                        NoAlgebra("Tabela", tabela="Status"),
                    ),
                ),
            ),
            colunas=(_coluna("Cliente", "idCliente"),),
        )

        plano = gerar_plano_execucao(arvore, CATALOGO)

        self.assertEqual(
            [passo.tipo for passo in plano.passos],
            ["Tabela", "Tabela", "Produto", "Projecao"],
        )
        produto = plano.passos[2]
        self.assertEqual(produto.expressao, "R1 × R2")
        self.assertEqual(produto.operacao, "Produto cartesiano (×)")
        self.assertEqual(produto.heuristicas, (HEURISTICA_JUNCAO,))
        self.assertIn("produto cartesiano", produto.justificativa)

    def test_plano_e_deterministico(self) -> None:
        self.assertEqual(_plano(_CONSULTA_OITO_TABELAS), _plano(_CONSULTA_OITO_TABELAS))

    def test_plano_e_imutavel(self) -> None:
        plano = _plano(_CONSULTA_UMA_TABELA)

        with self.assertRaises(AttributeError):
            plano.passos = ()
        with self.assertRaises(AttributeError):
            plano.passos[0].numero = 99

    def test_texto_lista_passos_heuristicas_e_justificativas(self) -> None:
        plano = _plano(_CONSULTA_DUAS_TABELAS)

        texto = plano_para_texto(plano)

        linhas = texto.split("\n")
        self.assertEqual(len(linhas), 3 * len(plano.passos))
        self.assertTrue(linhas[0].startswith("1. R1 ← Cliente  [Leitura de tabela]"))
        self.assertIn("Heurísticas: Heurística de redução de tuplas", texto)
        self.assertIn(
            "7. R7 ← R3 ⨝_{Cliente.idCliente = Pedido.Cliente_idCliente} R6",
            texto,
        )
        self.assertIn("[Projeção final (π)]", linhas[-3])

    def test_texto_indica_ausencia_de_heuristica(self) -> None:
        texto = plano_para_texto(_plano(_CONSULTA_UMA_TABELA))

        self.assertIn("Heurísticas: nenhuma", texto)


if __name__ == "__main__":
    unittest.main()