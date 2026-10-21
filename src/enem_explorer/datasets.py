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
    # Optional checksum listing inside the zip ("<md5> *<file name>" per line), verified while staging.
    md5_listing: str | None = None


ENEM_2024 = Dataset(
    name="enem_2024",
    url="https://download.inep.gov.br/microdados/microdados_enem_2024.zip",
    members={
        "results": "microdados_enem_2024/DADOS/RESULTADOS_2024.csv",
        "participants": "microdados_enem_2024/DADOS/PARTICIPANTES_2024.csv",
        "items": "microdados_enem_2024/DADOS/ITENS_PROVA_2024.csv",
    },
)

# School census: only used for school names and details (the ENEM results only carry a school code).
CENSO_2024 = Dataset(
    name="censo_escolar_2024",
    url="https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip",
    members={"schools": "microdados_censo_escolar_2024_defeso/dados/microdados_ed_basica_2024.csv"},
    md5_listing="microdados_censo_escolar_2024_defeso/dados/md5_microdados_ed_basica_2024.txt",
)

DATASETS = {d.name: d for d in (ENEM_2024, CENSO_2024)}
