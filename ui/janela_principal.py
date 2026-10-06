from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QTextOption
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


_ESTILO = """
QMainWindow#janelaPrincipal,
QWidget#conteudoPrincipal {
    background-color: #07111f;
    color: #dbeafe;
}

QLabel#marca {
    color: #2dd4bf;
    font-size: 11px;
    font-weight: 700;
}

QLabel#titulo {
    color: #f8fafc;
    font-size: 28px;
    font-weight: 700;
}

QLabel#descricao {
    color: #94a3b8;
    font-size: 13px;
}

QFrame#painelEntrada {
    background-color: #0e1a2b;
    border: 1px solid #22324a;
    border-radius: 14px;
}

QLabel#rotuloEditor {
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 700;
}

QPlainTextEdit#editorSql {
    background-color: #050c16;
    color: #dbeafe;
    border: 1px solid #293b55;
    border-radius: 9px;
    padding: 12px;
    selection-background-color: #0f766e;
    selection-color: #f8fafc;
}

QPlainTextEdit#editorSql:focus {
    border: 1px solid #2dd4bf;
}

QPushButton#botaoAnalisar {
    background-color: #22c3ad;
    color: #031411;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#botaoAnalisar:hover {
    background-color: #5eead4;
}

QPushButton#botaoAnalisar:pressed {
    background-color: #14a995;
}

QTextEdit#status {
    border: 1px solid #334155;
    border-radius: 9px;
    padding: 12px 14px;
    font-size: 13px;
}

QTextEdit#status[estado="neutro"] {
    background-color: #101c2e;
    border-color: #334155;
    color: #cbd5e1;
}

QTextEdit#status[estado="sucesso"] {
    background-color: #0b2923;
    border-color: #1c8c73;
    color: #a7f3d0;
}

QTextEdit#status[estado="sintatico"] {
    background-color: #30230c;
    border-color: #b7791f;
    color: #fde68a;
}

QTextEdit#status[estado="semantico"] {
    background-color: #321419;
    border-color: #b94755;
    color: #fecdd3;
}
"""


class JanelaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("janelaPrincipal")
        self.setWindowTitle("Processador de Consultas SQL")
        self.resize(960, 640)
        self.setMinimumSize(640, 420)

        conteudo = QWidget()
        conteudo.setObjectName("conteudoPrincipal")
        layout = QVBoxLayout(conteudo)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        layout.addLayout(self._criar_cabecalho())
        layout.addWidget(self._criar_painel_entrada(), 1)

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
        self.rotulo_status.setMinimumHeight(58)
        self.rotulo_status.setMaximumHeight(100)
        layout.addWidget(self.rotulo_status)

        self.setCentralWidget(conteudo)
        self.setStyleSheet(_ESTILO)
        self._definir_status(
            "Digite uma consulta SQL e selecione Analisar consulta.",
            "neutro",
        )

    def _criar_cabecalho(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)

        marca = QLabel("PROCESSADOR SQL / VALIDAÇÃO")
        marca.setObjectName("marca")
        layout.addWidget(marca)

        titulo = QLabel("Laboratório de consultas")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        descricao = QLabel(
            "Analise a estrutura, os identificadores e os tipos da consulta "
            "antes das próximas etapas do plano de execução."
        )
        descricao.setObjectName("descricao")
        descricao.setWordWrap(True)
        layout.addWidget(descricao)
        return layout

    def _criar_painel_entrada(self) -> QFrame:
        painel = QFrame()
        painel.setObjectName("painelEntrada")
        painel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(painel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        rotulo_editor = QLabel("Consulta SQL")
        rotulo_editor.setObjectName("rotuloEditor")
        layout.addWidget(rotulo_editor)

        self.editor_sql = QPlainTextEdit()
        self.editor_sql.setObjectName("editorSql")
        self.editor_sql.setAccessibleName("Editor da consulta SQL")
        self.editor_sql.setToolTip("Digite uma consulta SQL terminada por ponto e vírgula.")
        self.editor_sql.setPlaceholderText(
            "SELECT Cliente.Nome\nFROM Cliente;"
        )
        self.editor_sql.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor_sql.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        rotulo_editor.setBuddy(self.editor_sql)
        layout.addWidget(self.editor_sql, 1)

        acoes = QHBoxLayout()
        acoes.addStretch(1)
        self.botao_analisar = QPushButton("Analisar consulta")
        self.botao_analisar.setObjectName("botaoAnalisar")
        self.botao_analisar.setAccessibleName("Analisar consulta SQL")
        self.botao_analisar.setToolTip("Executar análise sintática e semântica.")
        self.botao_analisar.clicked.connect(self._analisar)
        acoes.addWidget(self.botao_analisar)
        layout.addLayout(acoes)

        return painel

    def _analisar(self) -> None:
        sql = self.editor_sql.toPlainText()
        self._definir_status("Analisando consulta...", "neutro")

        try:
            consulta = processar_consulta(sql)
        except ErroSintatico as erro:
            self._definir_status(str(erro), "sintatico")
            self.editor_sql.setFocus()
            return
        except ErroSemantico as erro:
            self._definir_status(str(erro), "semantico")
            self.editor_sql.setFocus()
            return

        quantidade_tabelas = 1 + len(consulta.juncoes)
        self._definir_status(
            f"Consulta válida. Colunas: {len(consulta.colunas)}. "
            f"Tabelas: {quantidade_tabelas}.",
            "sucesso",
        )

    def _definir_status(self, mensagem: str, estado: str) -> None:
        self.rotulo_status.setPlainText(mensagem)
        self.rotulo_status.setProperty("estado", estado)
        estilo = self.rotulo_status.style()
        estilo.unpolish(self.rotulo_status)
        estilo.polish(self.rotulo_status)
        self.rotulo_status.update()
