{% docs students %}Students counted: those finishing high school in 2024, linked to a school, present at every exam and with an essay score. Never below 10 (privacy).{% enddocs %}
{% docs schools %}Distinct schools those students came from.{% enddocs %}
{% docs state %}State (UF) where the school is. In `school_type` and `skill_gaps`, `BR` means the whole country.{% enddocs %}
{% docs school_type %}Who runs the school: Federal, Estadual (state), Municipal or Privada (private).{% enddocs %}
{% docs avg_natural_sciences %}Average score in Ciências da Natureza (natural sciences), 0–1000.{% enddocs %}
{% docs avg_humanities %}Average score in Ciências Humanas (humanities), 0–1000.{% enddocs %}
{% docs avg_languages %}Average score in Linguagens e Códigos (languages), 0–1000.{% enddocs %}
{% docs avg_math %}Average score in Matemática (math), 0–1000.{% enddocs %}
{% docs avg_essay %}Average essay (redação) score, 0–1000.{% enddocs %}
{% docs avg_overall %}Average of the five scores above (the usual "média do ENEM").{% enddocs %}
{% docs city_id %}IBGE city code.{% enddocs %}
{% docs city %}City where the school is.{% enddocs %}
{% docs rank_in_state %}Position in its state by `avg_overall` (1 = best).{% enddocs %}
{% docs area %}Exam area: LC languages, CH humanities, CN natural sciences, MT math.{% enddocs %}
{% docs skill %}Skill number (habilidade H1–H30) within the area, from INEP's reference matrix.{% enddocs %}
{% docs skill_description %}The skill's text in INEP's reference matrix (Portuguese).{% enddocs %}
{% docs pct_correct %}Percent of answers that were correct for this skill, 0–100. Annulled questions excluded.{% enddocs %}
{% docs answers %}Number of answers behind `pct_correct`.{% enddocs %}
