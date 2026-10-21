-- One row per question per booklet.
select
    CO_PROVA                    as booklet_id,
    SG_AREA                     as area,
    CO_POSICAO                  as position,
    CO_ITEM                     as item_id,
    TX_GABARITO                 as correct_answer,
    CO_HABILIDADE               as skill,
    IN_ITEM_ABAN = 1            as is_annulled,
    -- Only Languages positions 1-5 have a language: 0 English, 1 Spanish
    case TP_LINGUA when 0 then 'Inglês' when 1 then 'Espanhol' end as foreign_language,
    NU_PARAM_A                  as irt_discrimination,
    NU_PARAM_B                  as irt_difficulty,
    NU_PARAM_C                  as irt_guessing,
    TX_COR                      as booklet_color
from {{ source('inep', 'items') }}
