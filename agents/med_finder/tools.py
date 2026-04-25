import httpx
from google.adk.tools.tool_context import ToolContext

API_BASE = "https://medicaments-api.giygas.dev/v1"


def select_med(cis: str, tool_context: ToolContext) -> str:
    """Definitively selects the identified medication and transfers control back to the orchestrator.

    Call this tool as soon as you have identified the right medication.
    Call it only once, with the final CIS.

    Args:
        cis: The CIS of the selected medication.

    Returns:
        Confirmation of the selected CIS.
    """
    cache: dict = tool_context.state.get("_med_search_results", {})
    med = cache.get(str(cis))

    if med:
        substances_actives = [
            f"{s['denominationSubstance']} {s.get('dosage', '')}".strip()
            for s in (med.get("composition") or [])
            if s.get("natureComposant") == "SA"
        ]
        excipients = [
            s["denominationSubstance"]
            for s in (med.get("composition") or [])
            if s.get("natureComposant") == "FT"
        ]
        presentations = [
            f"{p.get('libellePresentation', '')} — {p.get('etatComercialisation', '')} (CIP: {p.get('cip13', 'N/A')})"
            for p in (med.get("presentations") or [])
        ]

        lines = [
            f"CIS: {med.get('cis', 'N/A')}",
            f"Name: {med.get('elementPharmaceutique', 'N/A')}",
            f"Form: {med.get('formePharmaceutique', 'N/A')}",
            f"Routes: {', '.join(med.get('voiesAdministration') or []) or 'N/A'}",
            f"Status: {med.get('etatComercialisation', 'N/A')}",
            f"Active substances: {', '.join(substances_actives) or 'N/A'}",
            f"Excipients: {', '.join(excipients) or 'N/A'}",
            f"Authorization type: {med.get('typeProcedureAMM', 'N/A')}",
            f"Authorization date: {med.get('dateAMM', 'N/A')}",
            f"Surveillance: {med.get('surveillanceRenforcee', 'N/A')}",
            f"Presentations: {' | '.join(presentations) or 'N/A'}",
        ]
        text = "\n".join(lines)
        tool_context.state["med_informations"] = med
        tool_context.state["current_med"] = text

    tool_context.actions.transfer_to_agent = "orchestrator"
    return cis


async def search_medicaments(name: str, tool_context: ToolContext) -> list[dict] | str:
    """Search for medications in the official French database (ANSM).

    Args:
        name: Name of the medication to search for.
              Use ONLY the medication name (brand name or INN).
              Do not include dosage, pharmaceutical form or any other information — name only.
              Correct examples: "doliprane", "paracetamol", "amoxicilline"
              Incorrect examples: "doliprane 1000mg comprimé adulte"

    Returns:
        List of matching medications with their CIS, or an error message if the search fails.
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
            f"HTTP error {e.response.status_code} while searching for '{name}'. "
            f"Try a different name or spelling."
        )
    except httpx.TimeoutException:
        return (
            f"Search for '{name}' timed out. "
            f"Try a shorter or different term."
        )
    except Exception as e:
        return (
            f"Unexpected error while searching for '{name}': {e}. "
            f"Try a different term."
        )

    if not results:
        return f"No medication found for '{name}'. Try another name or INN."

    all_results: dict[str, dict] = {str(med["cis"]): med for med in results}
    tool_context.state["_med_search_results"] = all_results

    return [
        {"cis": med["cis"], "nom": med["elementPharmaceutique"]}
        for med in list(all_results.values())[:30]
    ]
