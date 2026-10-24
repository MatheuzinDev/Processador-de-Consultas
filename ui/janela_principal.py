from html import escape

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
    QStackedWidget,  # <-- Nova importação
    QTabWidget,      # <-- Nova importação
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.erros import ErroSemantico, ErroSintatico
from core.grafo import GrafoOperadores
from core.processador import processar_consulta
from core.conversao import AlgebraRelacional
from core.otimizacao import ResultadoOtimizacao, otimizar_consulta, para_dicionario

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

QPlainTextEdit#editorSql,
QTextEdit#textoAlgebra,
QTextEdit#textoGrafo,
QTextEdit#textoOtimizacao,
QTextEdit#textoGrafoOtimizado {
    background-color: #0d2745;
    color: #fff8eb;
    border: none;
    selection-background-color: #2457c5;
    selection-color: #fff8eb;
    font-family: Consolas, monospace;
    font-size: 16px;
    padding: 14px;
}

QPlainTextEdit#editorSql:focus,
QTextEdit#textoAlgebra:focus,
QTextEdit#textoGrafo:focus,
QTextEdit#textoOtimizacao:focus,
QTextEdit#textoGrafoOtimizado:focus {
    border: none;
}

/* Estilo para as abas de visualização */
QTabWidget::pane {
    border: none;
    background-color: #0d2745;
}

QTabBar::tab {
    background-color: #071a30;
    color: #93a8bf;
    padding: 8px 16px;
    border-right: 1px solid #0d2745;
    font-family: Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
}

QTabBar::tab:selected {
    background-color: #0d2745;
    color: #fff8eb;
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

QPushButton#botaoAlternar {
    background-color: #2457c5;
    color: #fff8eb;
    border: 1px solid #fff8eb;
    border-radius: 3px;
    padding: 9px 18px;
    font-family: Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton#botaoAlternar:hover {
    background-color: #386de0;
}

QPushButton#botaoAlternar:disabled {
    background-color: #4e6279;
    color: #93a8bf;
    border-color: #4e6279;
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

        # Barra do arquivo (mantida fixa no topo do painel)
        barra = QFrame()
        barra.setObjectName("barraArquivo")
        layout_barra = QHBoxLayout(barra)
        layout_barra.setContentsMargins(15, 10, 15, 10)
        layout_barra.setSpacing(10)
        controles = QLabel("●  ●  ●")
        controles.setObjectName("controlesJanela")
        layout_barra.addWidget(controles)
        nome_arquivo = QLabel("consulta.sql")
        nome_arquivo.setObjectName("nomeArquivo")
        layout_barra.addWidget(nome_arquivo)
        layout_barra.addStretch(1)
        layout.addWidget(barra)

        # QStackedWidget para alternar entre Editor e Visualização
        self.pilha_visoes = QStackedWidget()
        
        # --- Visão 0: Editor SQL ---
        self.editor_sql = _EditorSQL()
        self.editor_sql.setObjectName("editorSql")
        self.editor_sql.setPlaceholderText("SELECT Cliente.Nome\nFROM Cliente;")
        self.editor_sql.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor_sql.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        # Margem ajustada para zero pois o QStackedWidget vai preencher
        self.editor_sql.document().setDocumentMargin(0) 
        self.pilha_visoes.addWidget(self.editor_sql)

        # --- Visão 1: Abas de Álgebra e Grafo ---
        self.abas_visualizacao = QTabWidget()
        
        self.texto_algebra = QTextEdit()
        self.texto_algebra.setObjectName("textoAlgebra")
        self.texto_algebra.setReadOnly(True)
        
        self.texto_grafo = QTextEdit()
        self.texto_grafo.setObjectName("textoGrafo")
        self.texto_grafo.setReadOnly(True)
        
        self.texto_otimizacao = QTextEdit()
        self.texto_otimizacao.setObjectName("textoOtimizacao")
        self.texto_otimizacao.setReadOnly(True)

        self.texto_grafo_otimizado = QTextEdit()
        self.texto_grafo_otimizado.setObjectName("textoGrafoOtimizado")
        self.texto_grafo_otimizado.setReadOnly(True)

        self.abas_visualizacao.addTab(self.texto_algebra, "Álgebra Relacional")
        self.abas_visualizacao.addTab(self.texto_grafo, "Grafo Original")
        self.abas_visualizacao.addTab(self.texto_otimizacao, "Álgebra Otimizada")
        self.abas_visualizacao.addTab(
            self.texto_grafo_otimizado,
            "Grafo Otimizado",
        )
        self.pilha_visoes.addWidget(self.abas_visualizacao)

        # Adiciona a pilha ao layout central
        layout.addWidget(self.pilha_visoes, 1)

        # Barra de Ações Inferior (mantida fixa na base)
        acoes = QFrame()
        acoes.setObjectName("acoesEditor")
        layout_acoes = QHBoxLayout(acoes)
        layout_acoes.setContentsMargins(15, 10, 15, 10)
        layout_acoes.setSpacing(12)

        self.rotulo_estatisticas = QLabel()
        self.rotulo_estatisticas.setObjectName("estatisticas")
        layout_acoes.addWidget(self.rotulo_estatisticas)
        layout_acoes.addStretch(1)

        # Botão para alternar entre as visões
        self.botao_alternar = QPushButton("VER ÁLGEBRA E GRAFO")
        self.botao_alternar.setObjectName("botaoAlternar")
        self.botao_alternar.setEnabled(False)  # Só habilita se a consulta for válida
        self.botao_alternar.clicked.connect(self._alternar_visao)
        layout_acoes.addWidget(self.botao_alternar)

        self.botao_analisar = QPushButton("ANALISAR CONSULTA")
        self.botao_analisar.setObjectName("botaoAnalisar")
        self.botao_analisar.clicked.connect(self._analisar)

        atalho = QLabel("ATALHO: CTRL + ENTER")
        atalho.setObjectName("atalho")
        layout_acoes.addWidget(atalho)
        layout_acoes.addWidget(self.botao_analisar)
        layout.addWidget(acoes)

        self.atalho_analisar = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.atalho_analisar.activated.connect(self._analisar)

        self.editor_sql.textChanged.connect(self._ao_alterar_texto)
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

    def _ao_alterar_texto(self) -> None:
        self._atualizar_estatisticas()
        # Se o usuário edita a consulta, desabilita a visualização até nova análise
        self.botao_alternar.setEnabled(False)
        # E se estiver na aba de visualização, volta automaticamente para o editor
        if self.pilha_visoes.currentIndex() != 0:
            self._alternar_visao()

    def _analisar(self) -> None:
        # Reseta o botão de alternar visão
        self.botao_alternar.setEnabled(False)
        
        sql = self.editor_sql.toPlainText()
        self._definir_status("Analisando consulta...", "neutro", "ANALISANDO")

        try:
            consulta = processar_consulta(sql)
        except ErroSintatico as erro:
            self._definir_status(str(erro), "sintatico", "ERRO SINTÁTICO")
            self.editor_sql.setFocus()
            # Força voltar para a consulta em caso de erro
            if self.pilha_visoes.currentIndex() != 0:
                self._alternar_visao()
            return
        except ErroSemantico as erro:
            self._definir_status(str(erro), "semantico", "ERRO SEMÂNTICO")
            self.editor_sql.setFocus()
            # Força voltar para a consulta em caso de erro
            if self.pilha_visoes.currentIndex() != 0:
                self._alternar_visao()
            return

        quantidade_tabelas = 1 + len(consulta.juncoes)
        self._definir_status(
            f"Consulta válida. Colunas: {len(consulta.colunas)}. "
            f"Tabelas: {quantidade_tabelas}.",
            "sucesso",
            "CONSULTA VÁLIDA",
        )

        expressao_algebra = AlgebraRelacional.converter_html(consulta)
        self.texto_algebra.setText(expressao_algebra)
        
        ast_dict = AlgebraRelacional.converter_dicionario(consulta)
        caminho_imagem = GrafoOperadores.gerar_imagem_grafo(ast_dict, "grafo_atual")
        self.texto_grafo.setHtml(self._html_imagem(caminho_imagem, "Grafo de Operadores"))

        otimizacao = otimizar_consulta(consulta)
        self.texto_otimizacao.setHtml(self._html_otimizacao(otimizacao))
        caminho_otimizado = GrafoOperadores.gerar_imagem_grafo(
            para_dicionario(otimizacao.arvore),
            "grafo_otimizado",
        )
        self.texto_grafo_otimizado.setHtml(
            self._html_imagem(caminho_otimizado, "Grafo Otimizado")
        )

        self.botao_alternar.setEnabled(True)

    @staticmethod
    def _html_imagem(caminho_imagem: str, descricao: str) -> str:
        return f"""
            <div style='text-align: center; padding: 10px; background-color: #0d2745;'>
                <img src='{caminho_imagem}' alt='{descricao}' style='max-width: 100%; height: auto; display: block; margin: 0 auto;'>
            </div>
        """

    @staticmethod
    def _html_otimizacao(otimizacao: ResultadoOtimizacao) -> str:
        blocos = []
        for numero, passo in enumerate(otimizacao.passos, start=1):
            blocos.append(
                f"<p style='color: #d9f45d; font-size: 18px; font-weight: 700;'>"
                f"Passo {numero} – {escape(passo.heuristica)}</p>"
                f"<p style='color: #93a8bf; font-size: 13px;'>{escape(passo.descricao)}</p>"
                f"<p style='color: #fff8eb; font-size: 15px;'>{escape(passo.expressao)}</p>"
            )
        return (
            "<div style='font-family: Consolas, monospace; line-height: 1.6; padding: 15px;'>"
            + "<hr style='border-color: #294868;'>".join(blocos)
            + "</div>"
        )

    def _alternar_visao(self) -> None:
        if self.pilha_visoes.currentIndex() == 0:
            # Vai para visualização (Álgebra/Grafo)
            self.pilha_visoes.setCurrentIndex(1)
            self.botao_alternar.setText("VER CONSULTA")
            self.botao_analisar.hide()
        else:
            # Volta para o Editor SQL
            self.pilha_visoes.setCurrentIndex(0)
            self.botao_alternar.setText("VER ÁLGEBRA E GRAFO")
            self.botao_analisar.show()

    def _definir_status(self, mensagem: str, estado: str, titulo: str) -> None:
        self.rotulo_tipo_status.setText(titulo)
        self.rotulo_status.setPlainText(mensagem)

        for componente in (self.rotulo_tipo_status, self.rotulo_status):
            componente.setProperty("estado", estado)
            estilo = componente.style()
            estilo.unpolish(componente)
            estilo.polish(componente)
            componente.update()