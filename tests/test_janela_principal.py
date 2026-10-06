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
        self.assertEqual(self.janela.botao_analisar.text(), "Analisar consulta")
        self.assertEqual(self.janela.rotulo_status.property("estado"), "neutro")
        self.assertIn(
            "Digite uma consulta SQL",
            self.janela.rotulo_status.toPlainText(),
        )

    def test_consulta_valida_mostra_resumo(self) -> None:
        self._analisar("SELECT Nome FROM Cliente;")

        self.assertEqual(self.janela.rotulo_status.property("estado"), "sucesso")
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


if __name__ == "__main__":
    unittest.main()
