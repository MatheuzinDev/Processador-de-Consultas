from core.modelos import ConsultaSQL
from core.parser import parsear
from core.validacao import validar_consulta


def processar_consulta(sql: str) -> ConsultaSQL:
    return validar_consulta(parsear(sql))
