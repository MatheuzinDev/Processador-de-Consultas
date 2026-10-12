from core.catalogo import CATALOGO, Catalogo
from core.modelos import (
    ConsultaSQL,
)

class AlgebraRelacional:
    def __init__(self, catalogo=None):
        self.catalogo = catalogo

    @staticmethod
    def _formatar_no(no) -> str:
        """
        Lê um nó da Árvore de Sintaxe Abstrata (AST) e retorna sua representação limpa em string.
        """
        if no is None:
            return ""
            
        nome_classe = no.__class__.__name__
        
        if nome_classe == "ReferenciaColuna":
            # Retorna no formato 'Tabela.Coluna' (ex: Cliente.Nome)
            if hasattr(no, 'tabela') and no.tabela:
                return f"{no.tabela}.{no.nome}"
            return str(no.nome)
            
        elif nome_classe == "Literal":
            # Retorna o valor direto (ex: '1', '0')
            return str(getattr(no, 'texto', getattr(no, 'valor', str(no))))
            
        elif nome_classe == "Comparacao":
            # Ex: Cliente.idCliente = Pedido.Cliente_idCliente
            esquerda = AlgebraRelacional._formatar_no(no.esquerda)
            direita = AlgebraRelacional._formatar_no(no.direita)
            operador = getattr(no, 'operador', '=')
            return f"{esquerda} {operador} {direita}"
            
        elif nome_classe == "Conjuncao":
            # Condição AND (Símbolo unicode ∧)
            esquerda = AlgebraRelacional._formatar_no(no.esquerda)
            direita = AlgebraRelacional._formatar_no(no.direita)
            return f"{esquerda} ∧ {direita}"
            
        elif nome_classe == "Disjuncao":
            # Condição OR (Símbolo unicode ∨)
            esquerda = AlgebraRelacional._formatar_no(no.esquerda)
            direita = AlgebraRelacional._formatar_no(no.direita)
            return f"{esquerda} ∨ {direita}"
            
        elif nome_classe == "JuncaoSQL":
            return getattr(no, 'tabela', str(no))
            
        else:
            return str(no)

    @staticmethod
    def converter_html(consulta_sql: 'ConsultaSQL') -> str:
        expressao = f"<b>{consulta_sql.tabela_origem}</b>"

        for juncao in consulta_sql.juncoes:
            condicao_juncao = AlgebraRelacional._formatar_no(juncao.condicao)
            tabela_juncao = getattr(juncao, 'tabela', str(juncao))
            juncao_html = f"<span style='font-size: 20px; color: #d9f45d;'>⨝</span> <sub>{condicao_juncao}</sub> <b>{tabela_juncao}</b>"
            expressao = f"({expressao} <br>&nbsp;&nbsp;&nbsp;&nbsp;{juncao_html})"

        if consulta_sql.condicao:
            condicao_str = AlgebraRelacional._formatar_no(consulta_sql.condicao)
            expressao = f"<span style='font-size: 20px; color: #f0b84b;'>σ</span> <sub>{condicao_str}</sub><br>&nbsp;&nbsp;({expressao})"

        if consulta_sql.colunas:
            colunas_formatadas = [AlgebraRelacional._formatar_no(col) for col in consulta_sql.colunas]
            colunas_str = ", ".join(colunas_formatadas)
            expressao = f"<span style='font-size: 20px; color: #bd4a3c;'>π</span> <sub>{colunas_str}</sub><br>({expressao})"

        return f"<div style='font-family: Consolas, monospace; white-space: nowrap; font-size: 24px; line-height: 2.0; padding: 15px;'>{expressao}</div>"


    @staticmethod
    def converter(consulta_sql: 'ConsultaSQL') -> str:
        expressao = consulta_sql.tabela_origem

        for juncao in consulta_sql.juncoes:
            condicao_juncao = AlgebraRelacional._formatar_no(juncao.condicao)
            tabela_juncao = getattr(juncao, 'tabela', str(juncao))
            expressao = f"({expressao} ⨝_{{{condicao_juncao}}} {tabela_juncao})"

        if consulta_sql.condicao:
            condicao_str = AlgebraRelacional._formatar_no(consulta_sql.condicao)
            expressao = f"σ_{{{condicao_str}}}({expressao})"

        if consulta_sql.colunas:
            colunas_formatadas = [AlgebraRelacional._formatar_no(col) for col in consulta_sql.colunas]
            colunas_str = ", ".join(colunas_formatadas)
            expressao = f"π_{{{colunas_str}}}({expressao})"

        return expressao


    #TODO IMPLEMENTAR O OTIMIZADOR