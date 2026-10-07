from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFontDatabase,
    QKeySequence,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QShortcut,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.erros import ErroSemantico, ErroSintatico
from core.processador import processar_consulta


_COR_LINHA_ATIVA = "#17395e"
_COR_GUTTER = "#071a30"
_COR_NUMERO = "#7890aa"
_COR_NUMERO_ATIVO = "#d9f45d"


_ESTILO = """
QMainWindow#janelaPrincipal,
QWidget#conteudoPrincipal {
    background-color: #f3ecdf;
    color: #10243e;
}

QLabel#titulo {
    color: #000000;
    font-size: 32px;
    font-weight: 700;
}

QFrame#painelEntrada {
    background-color: #0d2745;
    border: 2px solid #10243e;
    border-radius: 5px;
}

QFrame#barraArquivo {
    background-color: #071a30;
    border: none;
    border-bottom: 1px solid #294868;
}

QLabel#controlesJanela {
    color: #bd4a3c;
    font-size: 14px;
}

QLabel#nomeArquivo {
    color: #fff8eb;
    font-family: Consolas, monospace;
    font-size: 12px;
    font-weight: 700;
}

QPlainTextEdit#editorSql {
    background-color: #0d2745;
    color: #fff8eb;
    border: none;
    selection-background-color: #2457c5;
    selection-color: #fff8eb;
}

QPlainTextEdit#editorSql:focus {
    border: none;
}

QFrame#acoesEditor {
    background-color: #071a30;
    border: none;
    border-top: 1px solid #294868;
}

QLabel#estatisticas {
    color: #93a8bf;
    font-family: Consolas, monospace;
    font-size: 10px;
    letter-spacing: 1px;
}

QLabel#atalho {
    color: #93a8bf;
    font-family: Consolas, monospace;
    font-size: 9px;
}

QPushButton#botaoAnalisar {
    background-color: #bd4a3c;
    color: #fff8eb;
    border: 1px solid #fff8eb;
    border-radius: 3px;
    padding: 9px 18px;
    font-family: Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton#botaoAnalisar:hover {
    background-color: #d05a4b;
}

QPushButton#botaoAnalisar:pressed {
    background-color: #9f392f;
}

QPushButton#botaoAnalisar:focus {
    border: 2px solid #d9f45d;
}

QFrame#painelStatus {
    background-color: #fff8eb;
    border: 2px solid #10243e;
    border-radius: 4px;
}

QLabel#tipoStatus {
    background-color: #2457c5;
    color: #fff8eb;
    border: none;
    padding: 12px;
    font-family: Consolas, monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#tipoStatus[estado="sucesso"] {
    background-color: #d9f45d;
    color: #10243e;
}

QLabel#tipoStatus[estado="sintatico"] {
    background-color: #f0b84b;
    color: #10243e;
}

QLabel#tipoStatus[estado="semantico"] {
    background-color: #bd4a3c;
    color: #fff8eb;
}

QTextEdit#status {
    background-color: #fff8eb;
    color: #10243e;
    border: none;
    padding: 9px 12px;
    font-size: 12px;
}

QTextEdit#status[estado="neutro"] {
    color: #4e6279;
}

QTextEdit#status[estado="sucesso"] {
    color: #173f35;
}

QTextEdit#status[estado="sintatico"] {
    color: #704a08;
}

QTextEdit#status[estado="semantico"] {
    color: #7c2d26;
}
"""


class _AreaNumeros(QWidget):
    def __init__(self, editor: "_EditorSQL") -> None:
        super().__init__(editor)
        self.editor = editor
        self.setObjectName("areaNumeros")

    def sizeHint(self) -> QSize:
        return QSize(self.editor.largura_area_numeros(), 0)

    def paintEvent(self, evento: QPaintEvent) -> None:
        self.editor.pintar_area_numeros(evento)


class _EditorSQL(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.area_numeros = _AreaNumeros(self)

        self.blockCountChanged.connect(self._atualizar_largura_area_numeros)
        self.updateRequest.connect(self._atualizar_area_numeros)
        self.cursorPositionChanged.connect(self._destacar_linha_atual)
        self.textChanged.connect(self._destacar_linha_atual)

        self._atualizar_largura_area_numeros()
        self._destacar_linha_atual()

    def largura_area_numeros(self) -> int:
        quantidade_digitos = max(2, len(str(max(1, self.blockCount()))))
        largura_digito = self.fontMetrics().horizontalAdvance("9")
        return 20 + quantidade_digitos * largura_digito

    def _atualizar_largura_area_numeros(self, _quantidade: int = 0) -> None:
        self.setViewportMargins(self.largura_area_numeros(), 0, 0, 0)

    def _atualizar_area_numeros(self, retangulo: QRect, deslocamento: int) -> None:
        if deslocamento:
            self.area_numeros.scroll(0, deslocamento)
        else:
            self.area_numeros.update(
                0,
                retangulo.y(),
                self.area_numeros.width(),
                retangulo.height(),
            )

        if retangulo.contains(self.viewport().rect()):
            self._atualizar_largura_area_numeros()

    def resizeEvent(self, evento: QResizeEvent) -> None:
        super().resizeEvent(evento)
        conteudo = self.contentsRect()
        self.area_numeros.setGeometry(
            QRect(
                conteudo.left(),
                conteudo.top(),
                self.largura_area_numeros(),
                conteudo.height(),
            )
        )

    def _destacar_linha_atual(self) -> None:
        if self.document().isEmpty():
            self.setExtraSelections([])
            self.area_numeros.update()
            return

        selecao = QTextEdit.ExtraSelection()
        selecao.format.setBackground(QColor(_COR_LINHA_ATIVA))
        selecao.format.setProperty(
            QTextFormat.Property.FullWidthSelection,
            True,
        )
        selecao.cursor = self.textCursor()
        selecao.cursor.clearSelection()
        self.setExtraSelections([selecao])
        self.area_numeros.update()

    def pintar_area_numeros(self, evento: QPaintEvent) -> None:
        pintor = QPainter(self.area_numeros)
        pintor.fillRect(evento.rect(), QColor(_COR_GUTTER))

        bloco = self.firstVisibleBlock()
        numero_bloco = bloco.blockNumber()
        topo = round(
            self.blockBoundingGeometry(bloco).translated(self.contentOffset()).top()
        )
        base = topo + round(self.blockBoundingRect(bloco).height())
        linha_atual = self.textCursor().blockNumber()

        while bloco.isValid() and topo <= evento.rect().bottom():
            if bloco.isVisible() and base >= evento.rect().top():
                cor = (
                    _COR_NUMERO_ATIVO
                    if numero_bloco == linha_atual
                    else _COR_NUMERO
                )
                pintor.setPen(QColor(cor))
                pintor.drawText(
                    0,
                    topo,
                    self.area_numeros.width() - 10,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    f"{numero_bloco + 1:02d}",
                )

            bloco = bloco.next()
            topo = base
            if not bloco.isValid():
                break
            base = topo + round(self.blockBoundingRect(bloco).height())
            numero_bloco += 1


class JanelaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("janelaPrincipal")
        self.setWindowTitle("Processador de Consultas SQL")
        self.resize(1040, 700)
        self.setMinimumSize(640, 420)

        conteudo = QWidget()
        conteudo.setObjectName("conteudoPrincipal")
        layout = QVBoxLayout(conteudo)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        layout.addLayout(self._criar_cabecalho())
        layout.addWidget(self._criar_painel_entrada(), 1)
        layout.addWidget(self._criar_painel_status())

        self.setCentralWidget(conteudo)
        self.setStyleSheet(_ESTILO)
        self._definir_status(
            "Digite uma consulta SQL e selecione Analisar consulta.",
            "neutro",
            "EDITOR PRONTO",
        )

    def _criar_cabecalho(self) -> QVBoxLayout:
        cabecalho = QVBoxLayout()

        titulo = QLabel("Processador de Consultas SQL")
        titulo.setObjectName("titulo")
        cabecalho.addWidget(titulo)

        return cabecalho

    def _criar_painel_entrada(self) -> QFrame:
        painel = QFrame()
        painel.setObjectName("painelEntrada")
        painel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(painel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        barra = QFrame()
        barra.setObjectName("barraArquivo")
        layout_barra = QHBoxLayout(barra)
        layout_barra.setContentsMargins(15, 10, 15, 10)
        layout_barra.setSpacing(10)

        controles = QLabel("●  ●  ●")
        controles.setObjectName("controlesJanela")
        controles.setAccessibleName("Indicadores decorativos da janela")
        layout_barra.addWidget(controles)

        nome_arquivo = QLabel("consulta.sql")
        nome_arquivo.setObjectName("nomeArquivo")
        layout_barra.addWidget(nome_arquivo)
        layout_barra.addStretch(1)
        layout.addWidget(barra)

        self.editor_sql = _EditorSQL()
        self.editor_sql.setObjectName("editorSql")
        self.editor_sql.setAccessibleName("Editor da consulta SQL com linhas numeradas")
        self.editor_sql.setToolTip(
            "Digite uma consulta SQL terminada por ponto e vírgula."
        )
        self.editor_sql.setPlaceholderText("SELECT Cliente.Nome\nFROM Cliente;")
        self.editor_sql.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor_sql.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.editor_sql.document().setDocumentMargin(14)
        layout.addWidget(self.editor_sql, 1)

        acoes = QFrame()
        acoes.setObjectName("acoesEditor")
        layout_acoes = QHBoxLayout(acoes)
        layout_acoes.setContentsMargins(15, 10, 15, 10)
        layout_acoes.setSpacing(12)

        self.rotulo_estatisticas = QLabel()
        self.rotulo_estatisticas.setObjectName("estatisticas")
        self.rotulo_estatisticas.setAccessibleName("Estatísticas da consulta")
        layout_acoes.addWidget(self.rotulo_estatisticas)
        layout_acoes.addStretch(1)

        self.botao_analisar = QPushButton("ANALISAR CONSULTA")
        self.botao_analisar.setObjectName("botaoAnalisar")
        self.botao_analisar.setAccessibleName("Analisar consulta SQL")
        self.botao_analisar.setToolTip(
            "Executar análise sintática e semântica (Ctrl + Enter)."
        )
        self.botao_analisar.clicked.connect(self._analisar)

        atalho = QLabel("ATALHO: CTRL + ENTER")
        atalho.setObjectName("atalho")
        layout_acoes.addWidget(atalho)
        layout_acoes.addWidget(self.botao_analisar)
        layout.addWidget(acoes)

        self.atalho_analisar = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.atalho_analisar.activated.connect(self._analisar)

        self.editor_sql.textChanged.connect(self._atualizar_estatisticas)
        self._atualizar_estatisticas()
        return painel

    def _criar_painel_status(self) -> QFrame:
        self.painel_status = QFrame()
        self.painel_status.setObjectName("painelStatus")
        layout = QHBoxLayout(self.painel_status)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.rotulo_tipo_status = QLabel()
        self.rotulo_tipo_status.setObjectName("tipoStatus")
        self.rotulo_tipo_status.setMinimumWidth(150)
        self.rotulo_tipo_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rotulo_tipo_status)

        self.rotulo_status = QTextEdit()
        self.rotulo_status.setObjectName("status")
        self.rotulo_status.setAccessibleName("Status da análise")
        self.rotulo_status.setReadOnly(True)
        self.rotulo_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.rotulo_status.setWordWrapMode(
            QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.rotulo_status.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.rotulo_status.setMinimumHeight(62)
        self.rotulo_status.setMaximumHeight(94)
        layout.addWidget(self.rotulo_status, 1)

        return self.painel_status

    def _atualizar_estatisticas(self) -> None:
        linhas = self.editor_sql.blockCount()
        caracteres = len(self.editor_sql.toPlainText())
        texto_linhas = "LINHA" if linhas == 1 else "LINHAS"
        texto_caracteres = "CARACTERE" if caracteres == 1 else "CARACTERES"
        self.rotulo_estatisticas.setText(
            f"{linhas:02d} {texto_linhas}  /  "
            f"{caracteres:03d} {texto_caracteres}"
        )

    def _analisar(self) -> None:
        sql = self.editor_sql.toPlainText()
        self._definir_status("Analisando consulta...", "neutro", "ANALISANDO")

        try:
            consulta = processar_consulta(sql)
        except ErroSintatico as erro:
            self._definir_status(str(erro), "sintatico", "ERRO SINTÁTICO")
            self.editor_sql.setFocus()
            return
        except ErroSemantico as erro:
            self._definir_status(str(erro), "semantico", "ERRO SEMÂNTICO")
            self.editor_sql.setFocus()
            return

        quantidade_tabelas = 1 + len(consulta.juncoes)
        self._definir_status(
            f"Consulta válida. Colunas: {len(consulta.colunas)}. "
            f"Tabelas: {quantidade_tabelas}.",
            "sucesso",
            "CONSULTA VÁLIDA",
        )

    def _definir_status(self, mensagem: str, estado: str, titulo: str) -> None:
        self.rotulo_tipo_status.setText(titulo)
        self.rotulo_status.setPlainText(mensagem)

        for componente in (self.rotulo_tipo_status, self.rotulo_status):
            componente.setProperty("estado", estado)
            estilo = componente.style()
            estilo.unpolish(componente)
            estilo.polish(componente)
            componente.update()
