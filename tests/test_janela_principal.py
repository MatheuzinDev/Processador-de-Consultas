import os
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.modelos import ConsultaSQL, ReferenciaColuna, TipoDado
from ui.janela_principal import JanelaPrincipal


class TestJanelaPrincipal(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aplicacao = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.janela = JanelaPrincipal()
        self.janela.show()
        self.janela.activateWindow()
        self.aplicacao.processEvents()
        self.addCleanup(self._fechar_janela)

    def _fechar_janela(self) -> None:
        self.janela.close()
        self.aplicacao.processEvents()

    def _analisar(self, sql: str) -> None:
        self.janela.editor_sql.setPlainText(sql)
        QTest.mouseClick(
            self.janela.botao_analisar,
            Qt.MouseButton.LeftButton,
        )
        self.aplicacao.processEvents()

    def test_constroi_componentes_e_estado_inicial(self) -> None:
        self.assertEqual(self.janela.windowTitle(), "Processador de Consultas SQL")
        self.assertEqual(self.janela.editor_sql.toPlainText(), "")
        self.assertEqual(self.janela.botao_analisar.text(), "ANALISAR CONSULTA")
        self.assertEqual(self.janela.rotulo_status.property("estado"), "neutro")
        self.assertEqual(self.janela.rotulo_tipo_status.text(), "EDITOR PRONTO")
        self.assertEqual(
            self.janela.editor_sql.placeholderText(),
            "SELECT Cliente.Nome\nFROM Cliente;",
        )
        self.assertEqual(self.janela.editor_sql.extraSelections(), [])
        self.assertIn(
            "Digite uma consulta SQL",
            self.janela.rotulo_status.toPlainText(),
        )

    def test_editor_exibe_area_numerada_para_consulta_multilinha(self) -> None:
        self.janela.editor_sql.setPlainText("SELECT Nome\nFROM Cliente\n;")
        self.aplicacao.processEvents()

        editor = self.janela.editor_sql
        self.assertEqual(editor.blockCount(), 3)
        self.assertTrue(editor.area_numeros.isVisibleTo(self.janela))
        self.assertEqual(
            editor.viewportMargins().left(),
            editor.largura_area_numeros(),
        )
        self.assertEqual(len(editor.extraSelections()), 1)

    def test_estatisticas_acompanham_texto_do_editor(self) -> None:
        self.janela.editor_sql.setPlainText("SELECT Nome\nFROM Cliente;")
        self.aplicacao.processEvents()

        self.assertEqual(
            self.janela.rotulo_estatisticas.text(),
            "02 LINHAS  /  025 CARACTERES",
        )

    def test_consulta_valida_mostra_resumo(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "sucesso")
        self.assertEqual(self.janela.rotulo_tipo_status.text(), "CONSULTA VÁLIDA")
        self.assertEqual(
            self.janela.rotulo_tipo_status.property("estado"),
            "sucesso",
        )
        self.assertEqual(
            self.janela.rotulo_status.toPlainText(),
            "Consulta válida. Colunas: 1. Tabelas: 1.",
        )

    def test_consulta_multilinha_com_juncao_mostra_contagens(self) -> None:
        self._analisar(
            "SELECT Cliente.Nome, Pedido.idPedido\n"
            "FROM Cliente\n"
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        self.assertEqual(self.janela.rotulo_status.property("estado"), "sucesso")
        self.assertEqual(
            self.janela.rotulo_status.toPlainText(),
            "Consulta válida. Colunas: 2. Tabelas: 2.",
        )

    def test_erro_sintatico_mostra_categoria_e_posicao(self) -> None:
        self._analisar("SELECT Nome FROM Cliente")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "sintatico")
        mensagem = self.janela.rotulo_status.toPlainText()
        self.assertIn("Erro sintático", mensagem)
        self.assertIn("linha 1, coluna 25", mensagem)

    def test_consulta_vazia_mostra_erro_sintatico(self) -> None:
        self._analisar("")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "sintatico")
        self.assertIn("esperado SELECT", self.janela.rotulo_status.toPlainText())

    def test_erros_semanticos_mostram_categoria(self) -> None:
        casos = (
            "SELECT Nome FROM Pessoa;",
            "SELECT Nome FROM Cliente WHERE idCliente = 'invalido';",
        )

        for sql in casos:
            with self.subTest(sql=sql):
                self._analisar(sql)
                self.assertEqual(
                    self.janela.rotulo_status.property("estado"),
                    "semantico",
                )
                self.assertIn(
                    "Erro semântico",
                    self.janela.rotulo_status.toPlainText(),
                )

    def test_abas_incluem_algebra_e_grafo_otimizados(self) -> None:
        abas = self.janela.abas_visualizacao

        self.assertEqual(
            [abas.tabText(indice) for indice in range(abas.count())],
            [
                "Álgebra Relacional",
                "Grafo Original",
                "Álgebra Otimizada",
                "Grafo Otimizado",
                "Plano de Execução"
            ],
        )

    def test_sucesso_seguido_de_erro_remove_mensagem_anterior(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")
        self._analisar("SELECT Nome FROM Pessoa;")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "semantico")
        self.assertNotIn(
            "Consulta válida",
            self.janela.rotulo_status.toPlainText(),
        )

    def test_erro_seguido_de_sucesso_remove_mensagem_anterior(self) -> None:
        self._analisar("SELECT Nome FROM Cliente")
        self._analisar("SELECT Nome FROM Cliente;")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "sucesso")
        self.assertNotIn(
            "Erro sintático",
            self.janela.rotulo_status.toPlainText(),
        )

    def test_erro_mantem_texto_e_devolve_foco_ao_editor(self) -> None:
        sql = "SELECT Nome FROM Pessoa;"
        self._analisar(sql)

        self.assertEqual(self.janela.editor_sql.toPlainText(), sql)
        self.assertIs(QApplication.focusWidget(), self.janela.editor_sql)

    def test_botao_chama_fachada_uma_vez_com_sql_exato(self) -> None:
        sql = "consulta controlada pelo teste"
        consulta = ConsultaSQL(
            (ReferenciaColuna("Nome", "Cliente", TipoDado.TEXTO),),
            "Cliente",
        )

        with patch(
            "ui.janela_principal.processar_consulta",
            return_value=consulta,
        ) as processar:
            self._analisar(sql)

        processar.assert_called_once_with(sql)
        self.assertEqual(self.janela.rotulo_status.property("estado"), "sucesso")

    def test_ctrl_enter_chama_fachada_com_sql_exato(self) -> None:
        sql = "SELECT Nome FROM Cliente;"
        consulta = ConsultaSQL(
            (ReferenciaColuna("Nome", "Cliente", TipoDado.TEXTO),),
            "Cliente",
        )
        self.janela.editor_sql.setPlainText(sql)
        self.janela.editor_sql.setFocus()

        with patch(
            "ui.janela_principal.processar_consulta",
            return_value=consulta,
        ) as processar:
            QTest.keyClick(
                self.janela.editor_sql,
                Qt.Key.Key_Return,
                Qt.KeyboardModifier.ControlModifier,
            )
            self.aplicacao.processEvents()

        processar.assert_called_once_with(sql)

    def test_status_e_neutralizado_antes_de_chamar_fachada(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")
        estados_durante_chamada = []

        def observar_estado(sql: str) -> ConsultaSQL:
            estados_durante_chamada.append(
                self.janela.rotulo_status.property("estado")
            )
            self.assertEqual(
                self.janela.rotulo_status.toPlainText(),
                "Analisando consulta...",
            )
            raise RuntimeError(sql)

        with patch(
            "ui.janela_principal.processar_consulta",
            side_effect=observar_estado,
        ):
            with self.assertRaises(RuntimeError):
                self.janela._analisar()

        self.assertEqual(estados_durante_chamada, ["neutro"])
        self.assertNotIn(
            "Consulta válida",
            self.janela.rotulo_status.toPlainText(),
        )

    def test_status_mantem_erro_com_identificador_longo_acessivel(self) -> None:
        identificador = "Tabela" + "MuitoLonga" * 60
        self._analisar(f"SELECT Nome FROM {identificador};")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "semantico")
        self.assertIn(identificador, self.janela.rotulo_status.toPlainText())
        self.assertLessEqual(
            self.janela.rotulo_status.minimumSizeHint().width(),
            self.janela.rotulo_status.width(),
        )

    def test_componentes_ficam_visiveis_no_tamanho_minimo(self) -> None:
        self.janela.resize(640, 420)
        self.aplicacao.processEvents()
        central = self.janela.centralWidget()

        for componente in (
            self.janela.editor_sql,
            self.janela.botao_analisar,
            self.janela.rotulo_status,
        ):
            with self.subTest(componente=componente.objectName()):
                origem = componente.mapTo(central, QPoint(0, 0))
                geometria = QRect(origem, componente.size())
                self.assertTrue(componente.isVisibleTo(self.janela))
                self.assertTrue(central.rect().contains(geometria))

    def test_plano_de_execucao_lista_passos_e_heuristicas(self) -> None:
        self._analisar(
            "SELECT Cliente.Nome, Pedido.idPedido FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "WHERE Cliente.TipoCliente_idTipoCliente = 1 "
            "AND Pedido.ValorTotalPedido = 0;"
        )

        texto = self.janela.texto_plano.toPlainText()
        self.assertIn("Plano de execução", texto)
        self.assertIn("8 passos", texto)
        for trecho in (
            "Leitura de tabela",
            "Seleção (σ)",
            "Projeção (π)",
            "Junção (⨝)",
            "Projeção final (π)",
            "Heurística de junção",
            "Heurística de redução de tuplas",
            "Heurística de redução de atributos",
            "Heurística de seleções e junções mais restritivas",
        ):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, texto)

    def test_plano_de_execucao_mostra_passos_na_ordem_do_plano(self) -> None:
        self._analisar(
            "SELECT Cliente.Nome, Pedido.idPedido FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        texto = self.janela.texto_plano.toPlainText()
        posicoes = [texto.index(f"R{numero}") for numero in range(1, 6)]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_plano_de_execucao_de_consulta_simples(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")

        texto = self.janela.texto_plano.toPlainText()
        self.assertIn("2 passos", texto)
        self.assertIn("Única tabela da consulta.", texto)

    def test_plano_de_execucao_e_atualizado_em_nova_analise(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")
        self._analisar(
            "SELECT Cliente.Nome FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente;"
        )

        texto = self.janela.texto_plano.toPlainText()
        self.assertNotIn("2 passos", texto)
        self.assertIn("Junção (⨝)", texto)

    def test_plano_de_execucao_escapa_texto_dos_literais(self) -> None:
        self._analisar("SELECT Nome FROM Cliente WHERE Nome = '<b>&';")

        self.assertIn("<b>&", self.janela.texto_plano.toPlainText())

    def test_erro_nao_gera_plano_de_execucao(self) -> None:
        self._analisar("SELECT Nome FROM Pessoa;")

        self.assertEqual(self.janela.texto_plano.toPlainText(), "")
        self.assertFalse(self.janela.botao_alternar.isEnabled())

    def test_plano_de_execucao_fica_na_aba_da_visualizacao(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")

        abas = self.janela.abas_visualizacao
        indice = abas.indexOf(self.janela.texto_plano)
        self.assertEqual(abas.tabText(indice), "Plano de Execução")
        self.assertTrue(self.janela.botao_alternar.isEnabled())

if __name__ == "__main__":
    unittest.main()
