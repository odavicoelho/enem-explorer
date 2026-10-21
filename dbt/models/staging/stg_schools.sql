select
    CO_ENTIDADE                                         as school_id,
    NO_ENTIDADE                                         as school_name,
    {{ school_type_label('TP_DEPENDENCIA') }}           as school_type,
    case TP_LOCALIZACAO when 1 then 'Urbana' when 2 then 'Rural' end as school_location,
    CO_MUNICIPIO                                        as city_id,
    NO_MUNICIPIO                                        as city,
    SG_UF                                               as state,
    DS_ENDERECO                                         as address,
    NO_BAIRRO                                           as neighborhood,
    CO_CEP                                              as postal_code,
    -- 1 active, 2 paralyzed, 3 closed, 4 closed in a previous year
    TP_SITUACAO_FUNCIONAMENTO = 1                       as is_active,
    IN_INTERNET = 1                                     as has_internet,
    IN_BIBLIOTECA = 1                                   as has_library,
    IN_LABORATORIO_CIENCIAS = 1                         as has_science_lab,
    QT_MAT_MED                                          as high_school_enrollment
from {{ source('censo', 'schools') }}
