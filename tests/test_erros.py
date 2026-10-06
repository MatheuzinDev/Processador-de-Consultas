import unittest

from core.erros import ErroConsulta, ErroSemantico, ErroSintatico


class TestErros(unittest.TestCase):
    def test_erro_sintatico_sem_posicao(self) -> None:
        erro = ErroSintatico("esperado SELECT.")

        self.assertEqual(str(erro), "Erro sintático: esperado SELECT.")

    def test_erro_sintatico_com_linha_e_coluna(self) -> None:
        erro = ErroSintatico("esperado ON após a tabela Pedido.", 2, 14)

        self.assertEqual(
            str(erro),
            "Erro sintático na linha 2, coluna 14: esperado ON após a tabela Pedido.",
        )

    def test_erro_semantico_sem_posicao(self) -> None:
        erro = ErroSemantico("a tabela Pessoa não existe no modelo.")

        self.assertEqual(
            str(erro),
            "Erro semântico: a tabela Pessoa não existe no modelo.",
        )

    def test_erro_semantico_com_apenas_linha(self) -> None:
        erro = ErroSemantico("a coluna Apelido não existe.", linha=3)

        self.assertEqual(
            str(erro),
            "Erro semântico na linha 3: a coluna Apelido não existe.",
        )

    def test_erro_com_apenas_coluna(self) -> None:
        erro = ErroSintatico("caractere inválido.", coluna=7)

        self.assertEqual(
            str(erro),
            "Erro sintático na coluna 7: caractere inválido.",
        )

    def test_subclasses_podem_ser_capturadas_pela_classe_base(self) -> None:
        for tipo_erro in (ErroSintatico, ErroSemantico):
            with self.subTest(tipo_erro=tipo_erro):
                with self.assertRaises(ErroConsulta):
                    raise tipo_erro("falha de teste.")


if __name__ == "__main__":
    unittest.main()
