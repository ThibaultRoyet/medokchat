import httpx
from google.adk.tools.tool_context import ToolContext

API_BASE = "https://medicaments-api.giygas.dev/v1"


def select_med(cis: str, tool_context: ToolContext) -> str:
    """Sélectionne définitivement le médicament identifié et transfère le contrôle à l'orchestrateur.

    Appelle ce tool dès que tu as identifié le bon médicament.
    Ne l'appelle qu'une seule fois, avec le CIS final.

    Args:
        cis: Le CIS du médicament sélectionné.

    Returns:
        Confirmation du CIS sélectionné.
    """
    cache: dict = tool_context.state.get("_med_search_results", {})
    med = cache.get(str(cis))

    if med:
        substances = [
            f"{s['denominationSubstance']} {s.get('dosage', '')}".strip()
            for s in (med.get("composition") or [])
            if s.get("natureComposant") == "SA"
        ]
        lines = [
            f"CIS : {med.get('cis', 'N/A')}",
            f"Nom : {med.get('elementPharmaceutique', 'N/A')}",
            f"Forme : {med.get('formePharmaceutique', 'N/A')}",
            f"Voies : {', '.join(med.get('voiesAdministration') or [])}",
            f"Statut : {med.get('etatComercialisation', 'N/A')}",
            f"Substances actives : {', '.join(substances) if substances else 'N/A'}",
        ]
        text = "\n".join(lines)
        tool_context.state["med_informations"] = med
        tool_context.state["current_med"] = text

    tool_context.actions.transfer_to_agent = "orchestrator"
    return cis


async def search_medicaments(name: str, tool_context: ToolContext) -> list[dict] | str:
    """Recherche des médicaments dans la base officielle française (ANSM).

    Args:
        name: Nom du médicament à rechercher.
              Utilise UNIQUEMENT le nom du médicament (nom commercial ou DCI).
              N'inclus pas de dosage, forme pharmaceutique ou autre information — juste le nom.
              Exemples corrects : "doliprane", "paracetamol", "amoxicilline"
              Exemples incorrects : "doliprane 1000mg comprimé adulte"

    Returns:
        Liste des médicaments trouvés avec leur CIS, ou un message d'erreur si la recherche échoue.
    """
    query = name.strip().replace(" ", "+")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE}/medicaments",
                params={"search": query},
            )
            response.raise_for_status()
            results = response.json()
    except httpx.HTTPStatusError as e:
        return (
            f"Erreur HTTP {e.response.status_code} lors de la recherche de '{name}'. "
            f"Essaie avec un autre nom ou une orthographe différente."
        )
    except httpx.TimeoutException:
        return (
            f"La recherche de '{name}' a expiré. "
            f"Réessaie avec un terme plus court ou différent."
        )
    except Exception as e:
        return (
            f"Erreur inattendue lors de la recherche de '{name}' : {e}. "
            f"Essaie avec un terme différent."
        )

    if not results:
        return f"Aucun médicament trouvé pour '{name}'. Essaie un autre nom ou une DCI."

    all_results: dict[str, dict] = {str(med["cis"]): med for med in results}
    tool_context.state["_med_search_results"] = all_results

    return [
        {
            "cis": med["cis"],
            "nom": med["elementPharmaceutique"],
            "forme": med["formePharmaceutique"],
            "voies": med.get("voiesAdministration", []),
            "statut": med.get("etatComercialisation", ""),
            "substances": [
                f"{s['denominationSubstance']} {s['dosage']}"
                for s in (med.get("composition") or [])
                if s.get("natureComposant") == "SA"
            ],
        }
        for med in all_results.values()
    ]
