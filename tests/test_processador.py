import unittest
from pathlib import Path
from unittest.mock import patch

from core.erros import ErroSemantico, ErroSintatico
from core.modelos import ConsultaSQL, ReferenciaColuna, TipoDado
from core.processador import processar_consulta


class TestProcessador(unittest.TestCase):
    def test_processa_consulta_minima_ate_ast_resolvida(self) -> None:
        consulta = processar_consulta("select nome from cliente;")

        self.assertEqual(consulta.tabela_origem, "Cliente")
        self.assertEqual(
            consulta.colunas,
            (ReferenciaColuna("Nome", "Cliente", TipoDado.TEXTO),),
        )

    def test_processa_consulta_com_multiplas_juncoes(self) -> None:
        consulta = processar_consulta(
            "SELECT Cliente.Nome, Status.Descricao FROM Cliente "
            "JOIN Pedido ON Cliente.idCliente = Pedido.Cliente_idCliente "
            "JOIN Status ON Pedido.Status_idStatus = Status.idStatus;"
        )

        self.assertEqual(
            tuple(juncao.tabela for juncao in consulta.juncoes),
            ("Pedido", "Status"),
        )

    def test_propaga_erro_lexico_como_sintatico(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            processar_consulta("SELECT * FROM Cliente;")

        self.assertIn("caractere '*' não reconhecido", str(contexto.exception))

    def test_propaga_erro_do_parser_com_posicao(self) -> None:
        with self.assertRaises(ErroSintatico) as contexto:
            processar_consulta("SELECT Nome FROM Cliente")

        erro = contexto.exception
        self.assertEqual((erro.linha, erro.coluna), (1, 25))
        self.assertIn("';' ao final da consulta", str(erro))

    def test_propaga_erro_semantico_de_tabela(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            processar_consulta("SELECT Nome FROM Pessoa;")

        self.assertIn("Tabela 'Pessoa' não existe", str(contexto.exception))

    def test_propaga_erro_semantico_de_tipo(self) -> None:
        with self.assertRaises(ErroSemantico) as contexto:
            processar_consulta(
                "SELECT Nome FROM Cliente WHERE idCliente = 'invalido';"
            )

        self.assertIn("Tipos incompatíveis", str(contexto.exception))

    def test_consulta_vazia_continua_sendo_erro_sintatico(self) -> None:
        with self.assertRaises(ErroSintatico):
            processar_consulta("")

    def test_preserva_a_mesma_instancia_de_erro_sintatico(self) -> None:
        erro = ErroSintatico("falha controlada", 2, 3)

        with patch("core.processador.parsear", side_effect=erro):
            with self.assertRaises(ErroSintatico) as contexto:
                processar_consulta("SQL")

        self.assertIs(contexto.exception, erro)

    def test_preserva_a_mesma_instancia_de_erro_semantico(self) -> None:
        consulta = ConsultaSQL((ReferenciaColuna("Nome"),), "Cliente")
        erro = ErroSemantico("falha controlada")

        with patch("core.processador.parsear", return_value=consulta):
            with patch("core.processador.validar_consulta", side_effect=erro):
                with self.assertRaises(ErroSemantico) as contexto:
                    processar_consulta("SQL")

        self.assertIs(contexto.exception, erro)

    def test_consultas_de_referencia_passam_pela_fachada(self) -> None:
        caminho = Path(__file__).resolve().parents[1] / "exemplos-consultas.txt"
        texto = caminho.read_text(encoding="utf-8").replace("\r\n", "\n")
        consultas = tuple(
            bloco.strip() for bloco in texto.split("\n\n") if bloco.strip()
        )

        self.assertEqual(len(consultas), 4)
        for indice, sql in enumerate(consultas[:3], start=1):
            with self.subTest(consulta=indice):
                self.assertEqual(
                    processar_consulta(sql).tabela_origem,
                    "Cliente",
                )

        with self.assertRaises(ErroSintatico):
            processar_consulta(consultas[3])
        self.assertEqual(
            processar_consulta(consultas[3] + ";").tabela_origem,
            "Cliente",
        )


if __name__ == "__main__":
    unittest.main()
