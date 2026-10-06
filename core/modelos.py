from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import TypeAlias


class TipoToken(Enum):
    SELECT = auto()
    FROM = auto()
    WHERE = auto()
    JOIN = auto()
    ON = auto()
    AND = auto()
    IDENTIFICADOR = auto()
    NUMERO = auto()
    TEXTO = auto()
    VIRGULA = auto()
    PONTO = auto()
    ABRE_PARENTESE = auto()
    FECHA_PARENTESE = auto()
    OPERADOR = auto()
    PONTO_E_VIRGULA = auto()
    FIM = auto()


class TipoDado(Enum):
    INTEIRO = auto()
    DECIMAL = auto()
    TEXTO = auto()
    DATA_HORA = auto()


@dataclass(frozen=True, slots=True)
class Token:
    tipo: TipoToken
    texto: str
    linha: int
    coluna: int


@dataclass(frozen=True, slots=True)
class ReferenciaColuna:
    nome: str
    tabela: str | None = None
    tipo: TipoDado | None = None


@dataclass(frozen=True, slots=True)
class Literal:
    texto: str
    valor: int | Decimal | str | datetime
    tipo: TipoDado


Operando: TypeAlias = ReferenciaColuna | Literal


@dataclass(frozen=True, slots=True)
class Comparacao:
    esquerda: Operando
    operador: str
    direita: Operando


@dataclass(frozen=True, slots=True)
class Conjuncao:
    esquerda: Condicao
    direita: Condicao


Condicao: TypeAlias = Comparacao | Conjuncao


@dataclass(frozen=True, slots=True)
class JuncaoSQL:
    tabela: str
    condicao: Condicao


@dataclass(frozen=True, slots=True)
class ConsultaSQL:
    colunas: tuple[ReferenciaColuna, ...]
    tabela_origem: str
    juncoes: tuple[JuncaoSQL, ...] = ()
    condicao: Condicao | None = None
