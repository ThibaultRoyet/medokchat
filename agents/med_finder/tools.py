import httpx
from google.adk.tools.tool_context import ToolContext

API_BASE = "https://medicaments-api.giygas.dev/v1"


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
