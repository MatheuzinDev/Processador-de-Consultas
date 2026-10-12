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

        colunas_formatadas = [AlgebraRelacional._formatar_no(col) for col in consulta_sql.colunas]
        colunas_str = ", ".join(colunas_formatadas)
        expressao = f"π_{{{colunas_str}}}({expressao})"
        return expressao


    @staticmethod
    def converter_dicionario(consulta_sql: 'ConsultaSQL') -> dict:
        """
        Converte a ConsultaSQL em um dicionário estruturado para o grafo.
        """
        contador_id = 0
        def proximo_id():
            nonlocal contador_id
            contador_id += 1
            return str(contador_id)

        def criar_no(label: str, tipo: str, filhos: list = None, ast_no=None) -> dict:
            return {
                "id": proximo_id(),
                "label": label,
                "tipo": tipo,
                "filhos": filhos or [],
                "ast_no": ast_no,
            }

        # Tabela de origem
        no_atual = criar_no(consulta_sql.tabela_origem, "Tabela", ast_no=consulta_sql.tabela_origem)

        # Junções
        if consulta_sql.juncoes:
            for juncao in consulta_sql.juncoes:
                condicao_juncao = AlgebraRelacional._formatar_no(juncao.condicao)
                tabela_juncao = getattr(juncao, 'tabela', str(juncao))
                
                no_tabela_alvo = criar_no(tabela_juncao, "Tabela", ast_no=tabela_juncao)
                
                no_juncao = criar_no(
                    f"⨝\n{condicao_juncao}", 
                    "Juncao", 
                    [no_atual, no_tabela_alvo],
                    ast_no=juncao.condicao
                )
                no_atual = no_juncao

        # Filtro (WHERE)
        if consulta_sql.condicao:
            condicao_str = AlgebraRelacional._formatar_no(consulta_sql.condicao)
            no_filtro = criar_no(
                f"σ\n{condicao_str}", 
                "Filtro", 
                [no_atual],
                ast_no=consulta_sql.condicao
            )
            no_atual = no_filtro

        # Projeção (SELECT) - Sem verificação de '*'
        colunas_formatadas = [AlgebraRelacional._formatar_no(col) for col in consulta_sql.colunas]
        colunas_str = ", ".join(colunas_formatadas)
            
        no_raiz = criar_no(
            f"π\n{colunas_str}", 
            "Projecao", 
            [no_atual],
            ast_no=consulta_sql.colunas
        )

        return no_raiz