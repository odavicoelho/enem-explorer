"""The public datasets the pipeline reads, and where each file lives inside its zip."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    name: str
    url: str
    # logical name → path of the CSV inside the zip
    members: dict[str, str]
    encoding: str = "latin-1"
    delimiter: str = ";"


ENEM_2024 = Dataset(
    name="enem_2024",
    url="https://download.inep.gov.br/microdados/microdados_enem_2024.zip",
    members={
        "results": "microdados_enem_2024/DADOS/RESULTADOS_2024.csv",
        "participants": "microdados_enem_2024/DADOS/PARTICIPANTES_2024.csv",
        "items": "microdados_enem_2024/DADOS/ITENS_PROVA_2024.csv",
    },
)

DATASETS = {d.name: d for d in (ENEM_2024,)}
