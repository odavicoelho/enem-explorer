"""Build tests/fixtures/enem_sample.zip: a small, fully synthetic copy of the INEP zip.

Same members, columns, encoding (Latin-1), delimiter and answer-string layout as the real
ENEM 2024 microdata, but every value is generated: no real person's row is ever in this repo.

    python tests/make_fixture.py
"""

import hashlib
import io
import random
import string
import zipfile
from pathlib import Path

OUT = Path(__file__).parent / "fixtures" / "enem_sample.zip"
CENSO_OUT = Path(__file__).parent / "fixtures" / "censo_sample.zip"
CENSO_ROOT = "microdados_censo_escolar_2024_defeso/dados"
ROOT = "microdados_enem_2024/DADOS"

RESULTS_COLUMNS = [
    "NU_SEQUENCIAL",
    "NU_ANO",
    "CO_ESCOLA",
    "CO_MUNICIPIO_ESC",
    "NO_MUNICIPIO_ESC",
    "CO_UF_ESC",
    "SG_UF_ESC",
    "TP_DEPENDENCIA_ADM_ESC",
    "TP_LOCALIZACAO_ESC",
    "TP_SIT_FUNC_ESC",
    "CO_MUNICIPIO_PROVA",
    "NO_MUNICIPIO_PROVA",
    "CO_UF_PROVA",
    "SG_UF_PROVA",
    "TP_PRESENCA_CN",
    "TP_PRESENCA_CH",
    "TP_PRESENCA_LC",
    "TP_PRESENCA_MT",
    "CO_PROVA_CN",
    "CO_PROVA_CH",
    "CO_PROVA_LC",
    "CO_PROVA_MT",
    "NU_NOTA_CN",
    "NU_NOTA_CH",
    "NU_NOTA_LC",
    "NU_NOTA_MT",
    "TX_RESPOSTAS_CN",
    "TX_RESPOSTAS_CH",
    "TX_RESPOSTAS_LC",
    "TX_RESPOSTAS_MT",
    "TP_LINGUA",
    "TX_GABARITO_CN",
    "TX_GABARITO_CH",
    "TX_GABARITO_LC",
    "TX_GABARITO_MT",
    "TP_STATUS_REDACAO",
    "NU_NOTA_COMP1",
    "NU_NOTA_COMP2",
    "NU_NOTA_COMP3",
    "NU_NOTA_COMP4",
    "NU_NOTA_COMP5",
    "NU_NOTA_REDACAO",
]
PARTICIPANTS_COLUMNS = (
    "NU_INSCRICAO;NU_ANO;TP_FAIXA_ETARIA;TP_SEXO;TP_ESTADO_CIVIL;TP_COR_RACA;TP_NACIONALIDADE;"
    "TP_ST_CONCLUSAO;TP_ANO_CONCLUIU;TP_ENSINO;IN_TREINEIRO;CO_MUNICIPIO_PROVA;NO_MUNICIPIO_PROVA;"
    "CO_UF_PROVA;SG_UF_PROVA;" + ";".join(f"Q{i:03d}" for i in range(1, 24))
).split(";")
ITEMS_COLUMNS = [
    "CO_POSICAO",
    "SG_AREA",
    "CO_ITEM",
    "TX_GABARITO",
    "CO_HABILIDADE",
    "IN_ITEM_ABAN",
    "TX_MOTIVO_ABAN",
    "NU_PARAM_A",
    "NU_PARAM_B",
    "NU_PARAM_C",
    "TX_COR",
    "CO_PROVA",
    "TP_LINGUA",
    "IN_ITEM_ADAPTADO",
]

# Position ranges of each area on the answer sheet, as in the real exam.
AREAS = {"LC": 1, "CH": 46, "CN": 91, "MT": 136}
# Two booklet versions per area (the real exam has 30), with made-up codes.
BOOKLETS = {"LC": [1395, 1396], "CH": [1383, 1384], "CN": [1420, 1422], "MT": [1408, 1410]}
# (city code, city name with an accent on purpose, state code, state)
CITIES = [
    (3304201, "Nova Friburgo", 33, "RJ"),
    (3550308, "São Paulo", 35, "SP"),
    (2304400, "Fortaleza", 23, "CE"),
]
# 12 schools: 4 per city, one of each type (1 federal, 2 state, 3 municipal, 4 private).
SCHOOLS = [(90000000 + 10 * c + t, CITIES[c], t) for c in range(len(CITIES)) for t in (1, 2, 3, 4)]


def build(rows: int = 600, seed: int = 2024) -> bytes:
    rng = random.Random(seed)
    items, keys = _items(rng)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{ROOT}/ITENS_PROVA_2024.csv", _csv(ITEMS_COLUMNS, items))
        archive.writestr(f"{ROOT}/RESULTADOS_2024.csv", _csv(RESULTS_COLUMNS, _results(rng, rows, keys)))
        archive.writestr(
            f"{ROOT}/PARTICIPANTES_2024.csv", _csv(PARTICIPANTS_COLUMNS, _participants(rng, rows))
        )
    return buffer.getvalue()


def _items(rng: random.Random) -> tuple[list[list[object]], dict[int, str]]:
    """Item rows, plus each booklet's answer key as it appears in the results file."""
    rows: list[list[object]] = []
    keys: dict[int, str] = {}
    for area, start in AREAS.items():
        for booklet in BOOKLETS[area]:
            key = ""
            # Languages: positions 1-5 exist twice (English, then Spanish); the key has 50 letters.
            slots = [(p, lang) for lang in (0, 1) for p in range(1, 6)] if area == "LC" else []
            slots += [(start + i, None) for i in range(5 if area == "LC" else 0, 45)]
            for position, language in slots:
                answer = rng.choice("ABCDE")
                key += answer
                rows.append(
                    [
                        position,
                        area,
                        rng.randint(10000, 200000),
                        answer,
                        rng.randint(1, 30),
                        0,
                        "",
                        round(rng.uniform(0.5, 4), 5),
                        round(rng.uniform(-2, 3), 5),
                        round(rng.uniform(0.05, 0.3), 5),
                        "AZUL",
                        booklet,
                        "" if language is None else language,
                        0,
                    ]
                )
            keys[booklet] = key
    return rows, keys


def _answers(rng: random.Random, key: str, skill: float) -> str:
    return "".join(k if rng.random() < skill else rng.choice("ABCDE*.") for k in key)


def _results(rng: random.Random, rows: int, keys: dict[int, str]) -> list[list[object]]:
    out: list[list[object]] = []
    for seq in range(1, rows + 1):
        school, (city, city_name, uf_code, uf), kind = rng.choice(SCHOOLS)
        has_school = rng.random() < 0.6
        present = rng.random() < 0.8
        skill = {1: 0.6, 2: 0.4, 3: 0.45, 4: 0.7}[kind] + rng.uniform(-0.15, 0.15)
        language = rng.randint(0, 1)
        booklets = {a: rng.choice(BOOKLETS[a]) for a in AREAS}
        lc_key = keys[booklets["LC"]]
        lc_for_language = lc_key[5 * language : 5 * language + 5] + lc_key[10:]

        def score(skill: float = skill) -> float:
            return round(300 + 600 * min(max(skill + rng.uniform(-0.1, 0.1), 0), 1), 1)

        essay = [rng.choice([40, 80, 120, 160, 200]) for _ in range(5)]
        out.append(
            [
                seq,
                2024,
                school if has_school else "",
                city if has_school else "",
                city_name if has_school else "",
                uf_code if has_school else "",
                uf if has_school else "",
                kind if has_school else "",
                1 if has_school else "",
                1 if has_school else "",
                city,
                city_name,
                uf_code,
                uf,
                *([1, 1, 1, 1] if present else [0, 0, 0, 0]),
                booklets["CN"],
                booklets["CH"],
                booklets["LC"],
                booklets["MT"],
                *([score(), score(), score(), score()] if present else ["", "", "", ""]),
                _answers(rng, keys[booklets["CN"]], skill) if present else "",
                _answers(rng, keys[booklets["CH"]], skill) if present else "",
                _answers(rng, lc_for_language, skill) if present else "",
                _answers(rng, keys[booklets["MT"]], skill) if present else "",
                language,
                keys[booklets["CN"]],
                keys[booklets["CH"]],
                lc_key,
                keys[booklets["MT"]],
                1 if present else "",
                *(essay if present else [""] * 5),
                sum(essay) if present else "",
            ]
        )
    return out


def _participants(rng: random.Random, rows: int) -> list[list[object]]:
    out: list[list[object]] = []
    for i in range(rows):
        city, city_name, uf_code, uf = rng.choice(CITIES)
        out.append(
            [
                210000000000 + i,
                2024,
                rng.randint(1, 20),
                rng.choice("MF"),
                1,
                rng.randint(0, 5),
                1,
                rng.randint(1, 4),
                rng.randint(0, 17),
                "",
                0,
                city,
                city_name,
                uf_code,
                uf,
                *(rng.choice(string.ascii_uppercase[:8]) for _ in range(23)),
            ]
        )
    return out


CENSO_COLUMNS = [
    "NU_ANO_CENSO",
    "SG_UF",
    "NO_MUNICIPIO",
    "CO_MUNICIPIO",
    "NO_ENTIDADE",
    "CO_ENTIDADE",
    "TP_DEPENDENCIA",
    "TP_LOCALIZACAO",
    "DS_ENDERECO",
    "NO_BAIRRO",
    "CO_CEP",
    "TP_SITUACAO_FUNCIONAMENTO",
    "IN_BIBLIOTECA",
    "IN_LABORATORIO_CIENCIAS",
    "IN_INTERNET",
    "QT_MAT_MED",
]


def build_censo(seed: int = 2024) -> bytes:
    """Every fixture school, plus a few that never appear in the results (as in the real census)."""
    rng = random.Random(seed)
    rows: list[list[object]] = []
    extra = [(80000000 + i, CITIES[i % len(CITIES)], 2) for i in range(3)]
    for school, (city, city_name, _, uf), kind in SCHOOLS + extra:
        rows.append(
            [
                2024,
                uf,
                city_name,
                city,
                f"ESCOLA TESTE {school}",
                school,
                kind,
                1,
                f"RUA {rng.randint(1, 999)}",
                "CENTRO",
                f"0{rng.randint(1000000, 9999999)}",
                1,
                rng.randint(0, 1),
                rng.randint(0, 1),
                1,
                rng.randint(20, 900),
            ]
        )
    data = _csv(CENSO_COLUMNS, rows)
    listing = (
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest().upper()} *microdados_ed_basica_2024.csv\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{CENSO_ROOT}/microdados_ed_basica_2024.csv", data)
        archive.writestr(f"{CENSO_ROOT}/md5_microdados_ed_basica_2024.txt", listing.encode("latin-1"))
    return buffer.getvalue()


def _csv(columns: list[str], rows: list[list[object]]) -> bytes:
    lines = [";".join(columns)] + [";".join(str(v) for v in row) for row in rows]
    return ("\n".join(lines) + "\n").encode("latin-1")


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for path, content in ((OUT, build()), (CENSO_OUT, build_censo())):
        path.write_bytes(content)
        print(f"wrote {path} ({path.stat().st_size:,} bytes)")
