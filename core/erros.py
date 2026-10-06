class ErroConsulta(Exception):
    categoria = "Erro na consulta"

    def __init__(
        self,
        mensagem: str,
        linha: int | None = None,
        coluna: int | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.linha = linha
        self.coluna = coluna

    def __str__(self) -> str:
        localizacao = ""
        if self.linha is not None:
            localizacao = f" na linha {self.linha}"
            if self.coluna is not None:
                localizacao += f", coluna {self.coluna}"
        elif self.coluna is not None:
            localizacao = f" na coluna {self.coluna}"

        return f"{self.categoria}{localizacao}: {self.mensagem}"


class ErroSintatico(ErroConsulta):
    categoria = "Erro sintático"


class ErroSemantico(ErroConsulta):
    categoria = "Erro semântico"
