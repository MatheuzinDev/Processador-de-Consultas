from core.erros import ErroSintatico
from core.modelos import TipoToken, Token


_PALAVRAS_CHAVE = {
    "select": TipoToken.SELECT,
    "from": TipoToken.FROM,
    "where": TipoToken.WHERE,
    "join": TipoToken.JOIN,
    "on": TipoToken.ON,
    "and": TipoToken.AND,
}

_SIMBOLOS = {
    ",": TipoToken.VIRGULA,
    ".": TipoToken.PONTO,
    "(": TipoToken.ABRE_PARENTESE,
    ")": TipoToken.FECHA_PARENTESE,
    ";": TipoToken.PONTO_E_VIRGULA,
}


def _eh_digito(caractere: str) -> bool:
    return "0" <= caractere <= "9"


class _Tokenizador:
    def __init__(self, sql: str) -> None:
        self._sql = sql
        self._indice = 0
        self._linha = 1
        self._coluna = 1
        self._tokens: list[Token] = []

    def executar(self) -> tuple[Token, ...]:
        while not self._terminou():
            caractere = self._atual()

            if caractere.isspace():
                self._ignorar_espacos()
            elif caractere.isalpha() or caractere == "_":
                self._ler_identificador()
            elif _eh_digito(caractere):
                self._ler_numero()
            elif caractere == "-" and _eh_digito(self._seguinte()):
                self._ler_numero()
            elif caractere == "'":
                self._ler_texto()
            elif caractere in "=<>":
                self._ler_operador()
            elif caractere in _SIMBOLOS:
                self._ler_simbolo()
            else:
                raise ErroSintatico(
                    f"caractere {caractere!r} não reconhecido.",
                    self._linha,
                    self._coluna,
                )

        self._tokens.append(Token(TipoToken.FIM, "", self._linha, self._coluna))
        return tuple(self._tokens)

    def _terminou(self) -> bool:
        return self._indice >= len(self._sql)

    def _atual(self) -> str:
        return "" if self._terminou() else self._sql[self._indice]

    def _seguinte(self) -> str:
        proximo = self._indice + 1
        return "" if proximo >= len(self._sql) else self._sql[proximo]

    def _avancar(self) -> None:
        caractere = self._atual()
        if not caractere:
            return

        if caractere == "\r":
            self._indice += 1
            if self._atual() == "\n":
                self._indice += 1
            self._linha += 1
            self._coluna = 1
        elif caractere == "\n":
            self._indice += 1
            self._linha += 1
            self._coluna = 1
        else:
            self._indice += 1
            self._coluna += 1

    def _ignorar_espacos(self) -> None:
        while not self._terminou() and self._atual().isspace():
            self._avancar()

    def _ler_identificador(self) -> None:
        indice, linha, coluna = self._posicao_inicial()
        while not self._terminou():
            caractere = self._atual()
            if not (caractere.isalnum() or caractere == "_"):
                break
            self._avancar()

        texto = self._sql[indice : self._indice]
        tipo = _PALAVRAS_CHAVE.get(texto.casefold(), TipoToken.IDENTIFICADOR)
        self._tokens.append(Token(tipo, texto, linha, coluna))

    def _ler_numero(self) -> None:
        indice, linha, coluna = self._posicao_inicial()
        if self._atual() == "-":
            self._avancar()

        while _eh_digito(self._atual()):
            self._avancar()

        if self._atual() == ".":
            self._avancar()
            if not _eh_digito(self._atual()):
                raise ErroSintatico("número decimal malformado.", linha, coluna)
            while _eh_digito(self._atual()):
                self._avancar()

        texto = self._sql[indice : self._indice]
        self._tokens.append(Token(TipoToken.NUMERO, texto, linha, coluna))

    def _ler_texto(self) -> None:
        indice, linha, coluna = self._posicao_inicial()
        self._avancar()

        while not self._terminou():
            if self._atual() != "'":
                self._avancar()
                continue

            if self._seguinte() == "'":
                self._avancar()
                self._avancar()
                continue

            self._avancar()
            texto = self._sql[indice : self._indice]
            self._tokens.append(Token(TipoToken.TEXTO, texto, linha, coluna))
            return

        raise ErroSintatico(
            "texto iniciado nesta posição não foi fechado.",
            linha,
            coluna,
        )

    def _ler_operador(self) -> None:
        indice, linha, coluna = self._posicao_inicial()
        caractere = self._atual()
        seguinte = self._seguinte()

        self._avancar()
        if (caractere == "<" and seguinte in ("=", ">")) or (
            caractere == ">" and seguinte == "="
        ):
            self._avancar()

        texto = self._sql[indice : self._indice]
        self._tokens.append(Token(TipoToken.OPERADOR, texto, linha, coluna))

    def _ler_simbolo(self) -> None:
        indice, linha, coluna = self._posicao_inicial()
        caractere = self._atual()
        self._avancar()
        self._tokens.append(Token(_SIMBOLOS[caractere], caractere, linha, coluna))

    def _posicao_inicial(self) -> tuple[int, int, int]:
        return self._indice, self._linha, self._coluna


def tokenizar(sql: str) -> tuple[Token, ...]:
    return _Tokenizador(sql).executar()
