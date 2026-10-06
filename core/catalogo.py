from __future__ import annotations

from dataclasses import dataclass

from core.modelos import TipoDado


@dataclass(frozen=True, slots=True)
class Coluna:
    nome: str
    tipo: TipoDado
    chave_primaria: bool = False


@dataclass(frozen=True, slots=True)
class Tabela:
    nome: str
    colunas: tuple[Coluna, ...]


@dataclass(frozen=True, slots=True)
class ChaveEstrangeira:
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str


def _normalizar(nome: str) -> str:
    return nome.casefold()


class Catalogo:
    def __init__(
        self,
        tabelas: tuple[Tabela, ...],
        chaves_estrangeiras: tuple[ChaveEstrangeira, ...],
    ) -> None:
        self._tabelas = tuple(tabelas)
        self._chaves_estrangeiras = tuple(chaves_estrangeiras)
        self._tabelas_por_nome = {
            _normalizar(tabela.nome): tabela for tabela in self._tabelas
        }

    @property
    def tabelas(self) -> tuple[Tabela, ...]:
        return self._tabelas

    @property
    def chaves_estrangeiras(self) -> tuple[ChaveEstrangeira, ...]:
        return self._chaves_estrangeiras

    def buscar_tabela(self, nome: str) -> Tabela | None:
        return self._tabelas_por_nome.get(_normalizar(nome))

    def buscar_coluna(self, nome_tabela: str, nome_coluna: str) -> Coluna | None:
        tabela = self.buscar_tabela(nome_tabela)
        if tabela is None:
            return None

        nome_normalizado = _normalizar(nome_coluna)
        return next(
            (
                coluna
                for coluna in tabela.colunas
                if _normalizar(coluna.nome) == nome_normalizado
            ),
            None,
        )

    def buscar_tabelas_com_coluna(
        self,
        nomes_tabelas: tuple[str, ...],
        nome_coluna: str,
    ) -> tuple[tuple[Tabela, Coluna], ...]:
        ocorrencias = []
        for nome_tabela in nomes_tabelas:
            tabela = self.buscar_tabela(nome_tabela)
            coluna = self.buscar_coluna(nome_tabela, nome_coluna)
            if tabela is not None and coluna is not None:
                ocorrencias.append((tabela, coluna))

        return tuple(ocorrencias)

    def buscar_relacionamento(
        self,
        tabela_esquerda: str,
        coluna_esquerda: str,
        tabela_direita: str,
        coluna_direita: str,
    ) -> ChaveEstrangeira | None:
        esquerda = (
            _normalizar(tabela_esquerda),
            _normalizar(coluna_esquerda),
        )
        direita = (
            _normalizar(tabela_direita),
            _normalizar(coluna_direita),
        )

        for relacionamento in self._chaves_estrangeiras:
            origem = (
                _normalizar(relacionamento.tabela_origem),
                _normalizar(relacionamento.coluna_origem),
            )
            destino = (
                _normalizar(relacionamento.tabela_destino),
                _normalizar(relacionamento.coluna_destino),
            )
            if (esquerda, direita) in ((origem, destino), (destino, origem)):
                return relacionamento

        return None


_CATEGORIA = Tabela(
    "Categoria",
    (
        Coluna("idCategoria", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Descricao", TipoDado.TEXTO),
    ),
)

_PRODUTO = Tabela(
    "Produto",
    (
        Coluna("idProduto", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Nome", TipoDado.TEXTO),
        Coluna("Descricao", TipoDado.TEXTO),
        Coluna("Preco", TipoDado.DECIMAL),
        Coluna("QuantEstoque", TipoDado.DECIMAL),
        Coluna("Categoria_idCategoria", TipoDado.INTEIRO),
    ),
)

_TIPO_CLIENTE = Tabela(
    "TipoCliente",
    (
        Coluna("idTipoCliente", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Descricao", TipoDado.TEXTO),
    ),
)

_CLIENTE = Tabela(
    "Cliente",
    (
        Coluna("idCliente", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Nome", TipoDado.TEXTO),
        Coluna("Email", TipoDado.TEXTO),
        Coluna("Nascimento", TipoDado.DATA_HORA),
        Coluna("Senha", TipoDado.TEXTO),
        Coluna("TipoCliente_idTipoCliente", TipoDado.INTEIRO),
        Coluna("DataRegistro", TipoDado.DATA_HORA),
    ),
)

_TIPO_ENDERECO = Tabela(
    "TipoEndereco",
    (
        Coluna("idTipoEndereco", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Descricao", TipoDado.TEXTO),
    ),
)

_ENDERECO = Tabela(
    "Endereco",
    (
        Coluna("idEndereco", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("EnderecoPadrao", TipoDado.INTEIRO),
        Coluna("Logradouro", TipoDado.TEXTO),
        Coluna("Numero", TipoDado.TEXTO),
        Coluna("Complemento", TipoDado.TEXTO),
        Coluna("Bairro", TipoDado.TEXTO),
        Coluna("Cidade", TipoDado.TEXTO),
        Coluna("UF", TipoDado.TEXTO),
        Coluna("CEP", TipoDado.TEXTO),
        Coluna("TipoEndereco_idTipoEndereco", TipoDado.INTEIRO),
        Coluna("Cliente_idCliente", TipoDado.INTEIRO),
    ),
)

_TELEFONE = Tabela(
    "Telefone",
    (
        Coluna("Numero", TipoDado.TEXTO, chave_primaria=True),
        Coluna("Cliente_idCliente", TipoDado.INTEIRO),
    ),
)

_STATUS = Tabela(
    "Status",
    (
        Coluna("idStatus", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Descricao", TipoDado.TEXTO),
    ),
)

_PEDIDO = Tabela(
    "Pedido",
    (
        Coluna("idPedido", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Status_idStatus", TipoDado.INTEIRO),
        Coluna("DataPedido", TipoDado.DATA_HORA),
        Coluna("ValorTotalPedido", TipoDado.DECIMAL),
        Coluna("Cliente_idCliente", TipoDado.INTEIRO),
    ),
)

_PEDIDO_HAS_PRODUTO = Tabela(
    "Pedido_has_Produto",
    (
        Coluna("idPedidoProduto", TipoDado.INTEIRO, chave_primaria=True),
        Coluna("Pedido_idPedido", TipoDado.INTEIRO),
        Coluna("Produto_idProduto", TipoDado.INTEIRO),
        Coluna("Quantidade", TipoDado.DECIMAL),
        Coluna("PrecoUnitario", TipoDado.DECIMAL),
    ),
)

_TABELAS = (
    _CATEGORIA,
    _PRODUTO,
    _TIPO_CLIENTE,
    _CLIENTE,
    _TIPO_ENDERECO,
    _ENDERECO,
    _TELEFONE,
    _STATUS,
    _PEDIDO,
    _PEDIDO_HAS_PRODUTO,
)

_CHAVES_ESTRANGEIRAS = (
    ChaveEstrangeira(
        "Produto", "Categoria_idCategoria", "Categoria", "idCategoria"
    ),
    ChaveEstrangeira(
        "Cliente", "TipoCliente_idTipoCliente", "TipoCliente", "idTipoCliente"
    ),
    ChaveEstrangeira(
        "Endereco",
        "TipoEndereco_idTipoEndereco",
        "TipoEndereco",
        "idTipoEndereco",
    ),
    ChaveEstrangeira("Endereco", "Cliente_idCliente", "Cliente", "idCliente"),
    ChaveEstrangeira("Telefone", "Cliente_idCliente", "Cliente", "idCliente"),
    ChaveEstrangeira("Pedido", "Status_idStatus", "Status", "idStatus"),
    ChaveEstrangeira("Pedido", "Cliente_idCliente", "Cliente", "idCliente"),
    ChaveEstrangeira(
        "Pedido_has_Produto", "Pedido_idPedido", "Pedido", "idPedido"
    ),
    ChaveEstrangeira(
        "Pedido_has_Produto", "Produto_idProduto", "Produto", "idProduto"
    ),
)

CATALOGO = Catalogo(_TABELAS, _CHAVES_ESTRANGEIRAS)
