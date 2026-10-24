# Processador de Consultas SQL

Projeto acadêmico que demonstra as etapas internas de processamento de uma consulta SQL. A versão
atual recebe uma consulta, executa análise léxica e sintática, resolve tabelas e colunas em um catálogo
estático e valida a compatibilidade dos tipos.

O projeto não acessa um banco de dados real nem executa consultas sobre registros.

## Requisitos

- Python 3.12
- PySide6 6.8 ou superior, na linha 6.x
- Graphviz

## Instalação


### 1. Instalar o Graphviz (Ferramenta do Sistema)

No PowerShell (como Administrador):
```powershell
# Instalação do binário do Graphviz via WinGet
winget install Graphviz
```

Linux (Ubuntu/Debian):
```bash
sudo apt update && sudo apt install -y graphviz
```

macOS
```powershell
brew install graphviz
```
### 2. Instalar dependências

No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Execução

```powershell
python main.py
```

Digite uma consulta SQL, incluindo o `;` final, e selecione **Analisar consulta**. A faixa inferior
informa se a consulta é válida ou apresenta separadamente o erro sintático ou semântico encontrado.

## Testes

Para executar toda a suíte sem abrir janelas:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
Remove-Item Env:QT_QPA_PLATFORM
```

Verificação adicional de sintaxe dos módulos:

```powershell
python -m compileall core ui tests main.py
```

## SQL suportado

- `SELECT` com uma ou mais colunas explícitas.
- `FROM` com uma tabela inicial.
- Zero ou vários `JOIN ... ON`.
- `WHERE` opcional.
- Condições combinadas com `AND` e parênteses.
- Operadores `=`, `>`, `<`, `<=`, `>=` e `<>`.
- Inteiros, decimais, números negativos, textos e datas ISO entre aspas simples.
- Referências qualificadas, como `Cliente.Nome`.
- Referências não qualificadas quando não houver ambiguidade.
- Palavras-chave e identificadores sem diferença entre maiúsculas e minúsculas.

O ponto e vírgula final é obrigatório.

## Otimização (HU4)

A consulta validada é otimizada por heurísticas em `core/otimizacao.py`, seguindo o passo a passo
visto em aula:

1. **Junção** – as tabelas são combinadas com `⨝` usando as condições do `ON`, nunca com produto
   cartesiano.
2. **Redução de tuplas** – cada condição do `WHERE` que envolve uma só tabela vira uma seleção `σ`
   logo acima dessa tabela.
3. **Redução de atributos** – acima de cada tabela entra uma projeção `π` com apenas as colunas usadas
   no `SELECT` e nas junções (omitida quando todas as colunas são necessárias).
4. **Mais restritivas primeiro** – as folhas são reordenadas pela restritividade da seleção
   (igualdade em chave primária > igualdade > intervalo > diferença > sem seleção), sempre juntando
   uma tabela ligada às anteriores por condição de junção. Empates mantêm a ordem da consulta.

A interface mostra cada passo na aba **Álgebra Otimizada** e a árvore final na aba
**Grafo Otimizado**.

## Fora do escopo atual

- `SELECT *`.
- `OR` e `NOT`.
- Aliases.
- Agregações e subconsultas.
- `ORDER BY`, `GROUP BY` e `HAVING`.
- Outros tipos de junção.
- Execução em banco de dados real.
- Álgebra relacional, grafos e plano de execução, que pertencem às próximas etapas.

## Estrutura

```text
core/   tokenização, parsing, catálogo, validação, álgebra, grafo e otimização
ui/     interface PySide6
tests/  testes automatizados
main.py ponto de entrada da aplicação
```
