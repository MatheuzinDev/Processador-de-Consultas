import sys
import unittest
from unittest.mock import patch

import main


class TestMain(unittest.TestCase):
    def test_main_configura_aplicacao_e_mostra_janela(self) -> None:
        with patch("main.QApplication") as classe_aplicacao:
            with patch("main.JanelaPrincipal") as classe_janela:
                aplicacao = classe_aplicacao.return_value
                aplicacao.exec.return_value = 7

                resultado = main.main()

        classe_aplicacao.assert_called_once_with(sys.argv)
        aplicacao.setApplicationName.assert_called_once_with(
            "Processador de Consultas"
        )
        classe_janela.assert_called_once_with()
        classe_janela.return_value.show.assert_called_once_with()
        aplicacao.exec.assert_called_once_with()
        self.assertEqual(resultado, 7)


if __name__ == "__main__":
    unittest.main()
