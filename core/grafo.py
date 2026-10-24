import graphviz


class GrafoOperadores:
    @staticmethod
    def gerar_imagem_grafo(dicionario_ast: dict, caminho_saida: str = "grafo_operadores"):
        dot = graphviz.Digraph(comment='Grafo de Operadores Relacionais')
        
        # 'TB' = Top to Bottom (Raiz em cima, folhas embaixo - padrão natural de árvores)
        # Ajustamos o espaçamento (sep e ranksep) para respiro entre os nós
        dot.attr(rankdir='TB', splines='ortho', nodesep='0.6', ranksep='0.8')
        
        # Configuração global de estilo limpo e moderno
        dot.attr('node', 
            fontname='Consolas', 
            fontsize='11',
            shape='box', 
            style='filled,rounded', 
            margin='0.25,0.15'
        )
        dot.attr('edge', color='#294868', penwidth='1.5', arrowsize='0.8')

        # Paleta de cores alinhada ao tema escuro da sua aplicação
        cores = {
            "Projecao": {"fill": "#1b3a57", "font": "#d9f45d", "border": "#2457c5"}, # Destaque elegante
            "Filtro":   {"fill": "#2d2a1e", "font": "#f0b84b", "border": "#f0b84b"}, # Tom amarelado suave
            "Juncao":   {"fill": "#172d24", "font": "#5cd9b2", "border": "#2e7d60"}, # Tom esverdeado moderno
            "Produto":  {"fill": "#3a1d1a", "font": "#f08b7e", "border": "#bd4a3c"}, # Produto cartesiano em alerta
            "Tabela":   {"fill": "#0d2745", "font": "#fff8eb", "border": "#294868"}  # Azul base da UI
        }

        def percorrer_arvore(no):
            estilo = cores.get(no["tipo"], {"fill": "#ffffff", "font": "#000000", "border": "#000000"})

            # Adiciona quebras de linha manuais em textos muito longos (como a lista de colunas)
            label = no["label"]
            if len(label) > 60 and no["tipo"] == "Projecao":
                # Insere uma quebra a cada ~50 caracteres para a caixa não estourar a largura
                partes = [label[i:i+55] for i in range(0, len(label), 55)]
                label = "\n".join(partes)

            dot.node(
                no["id"], 
                label, 
                fillcolor=estilo["fill"],
                fontcolor=estilo["font"],
                color=estilo["border"]
            )

            for filho in no.get("filhos", []):
                percorrer_arvore(filho)
                # Seta apontando de cima para baixo (do operador para os dados)
                dot.edge(no["id"], filho["id"])

        percorrer_arvore(dicionario_ast)

        dot.render(caminho_saida, format="png", cleanup=True)
        return f"{caminho_saida}.png"