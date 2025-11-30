# fiches/services/evaluation_stats.py (par ex.)
def compute_stats_for(e):
    """
    e = instance d'Evaluation (non NULL). Retourne un dict de valeurs calculées.
    Gère les None, l'agent vs responsable, S1/S2…
    """
    def ok(*vals): return all(v is not None for v in vals)

    # M1
    m1 = ((e.connaissances + e.initiative + e.rendement + e.respect_objectifs) / 4
          if ok(e.connaissances, e.initiative, e.rendement, e.respect_objectifs) else None)
    # M2
    m2 = ((e.civisme + e.service_public + e.relations_humaines + e.discipline +
           e.ponctualite + e.assiduite + e.tenue) / 7
          if ok(e.civisme, e.service_public, e.relations_humaines, e.discipline,
                e.ponctualite, e.assiduite, e.tenue) else None)
    # M3 (si responsable)
    if e.type_personnel == 'responsable':
        m3 = ((e.leadership + e.planification + e.prise_decision +
               e.resolution_problemes + e.travail_equipe) / 5
              if ok(e.leadership, e.planification, e.prise_decision,
                    e.resolution_problemes, e.travail_equipe) else None)
    else:
        m3 = 0  # ou None si tu préfères

    # Pondérations
    mp1 = m1 * 2 if m1 is not None else None
    mp2 = m2 if m2 is not None else None
    mp3 = (m3 * 2 if (e.type_personnel == 'responsable' and m3 is not None) else (0 if e.type_personnel != 'responsable' else None))

    # Somme pondérée
    if e.type_personnel == 'responsable':
        somme = (mp1 + mp2 + mp3) if None not in (mp1, mp2, mp3) else None
    else:
        somme = (mp1 + mp2) if None not in (mp1, mp2) else None

    # Moyenne générale /5
    if e.type_personnel == 'responsable':
        mg = ((m1 * 2 + m2 + m3 * 2) / 5) if ok(m1, m2, m3) else None
    else:
        mg = ((m1 * 2 + m2) / 3) if ok(m1, m2) else None

    # Annuel (S2)
    mpa_s1 = mpa_s2 = total_mpa = mga = None
    if e.semestre == 2 and mg is not None:
        s1 = (e.__class__.objects
              .filter(agent=e.agent, annee=e.annee, semestre=1)
              .values_list('moyenne_generale', flat=True).first())
        # si pas stocké, re-calculer vite fait depuis la S1 (optionnel)
        if s1 is None:
            s1_eval = e.__class__.objects.filter(agent=e.agent, annee=e.annee, semestre=1).first()
            if s1_eval:
                from .evaluation_stats import compute_stats_for as _recompute
                s1_stats = _recompute(s1_eval)
                s1 = s1_stats['moyenne_generale']

        if s1 is not None:
            mpa_s1 = round(s1 * 1, 3)
            mpa_s2 = round(mg * 2, 3)
            total_mpa = round(mpa_s1 + mpa_s2, 3)
            mga = round(total_mpa / 3, 3)

    return {
        'moyenne_rendement': m1,
        'moyenne_comportement': m2,
        'moyenne_management': m3 if e.type_personnel == 'responsable' else None,
        'moyenne_generale': mg,

        'mp1': mp1, 'mp2': mp2, 'mp3': mp3,
        'somme_moyennes_ponderees': somme,

        'mpa_s1': mpa_s1, 'mpa_s2': mpa_s2,
        'total_mpa': total_mpa, 'moyenne_generale_annuelle': mga,
    }
