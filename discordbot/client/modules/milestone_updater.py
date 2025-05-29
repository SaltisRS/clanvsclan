import wom
import os
import asyncio
import pandas as pd
import io
import httpx
from loguru import logger
from dotenv import load_dotenv
from typing import Dict, Any, List, Union, Literal

load_dotenv()

client = wom.Client(
    api_key=os.getenv("WOM_API"),
    user_agent="@saltis."
)

MILSTONES_DATA = {
    "cluescroll": [
        {"name": "Beginner"}, {"name": "Easy"}, {"name": "Medium"},
        {"name": "Hard"}, {"name": "Elite"}, {"name": "Master"}
    ],
    "experience": [
        {"name": "Attack"}, {"name": "Strength"}, {"name": "Defense"},
        {"name": "Ranged"}, {"name": "Prayer"}, {"name": "Magic"},
        {"name": "Runecrafting"}, {"name": "Construction"}, {"name": "Hitpoints"},
        {"name": "Agility"}, {"name": "Herblore"}, {"name": "Thieving"},
        {"name": "Crafting"}, {"name": "Fletching"}, {"name": "Slayer"},
        {"name": "Hunter"}, {"name": "Mining"}, {"name": "Smithing"},
        {"name": "Fishing"}, {"name": "Cooking"}, {"name": "Firemaking"},
        {"name": "Woodcutting"}, {"name": "Farming"}
    ],
    "killcount": [
        {"name": "Abyssal Sire"}, {"name": "Alchemical Hydra"}, {"name": "Amoxliatl"},
        {"name": "Araxxor"}, {"name": "Artio"}, {"name": "Barrows Chests"},
        {"name": "Bryophyta"}, {"name": "Callisto"}, {"name": "Calvar'ion"},
        {"name": "Cerberus"}, {"name": "Chambers of Xeric"}, {"name": "Chambers of Xeric (CM)"},
        {"name": "Chaos Elemental"}, {"name": "Chaos Fanatic"}, {"name": "Commander Zilyana"},
        {"name": "Corporeal Beast"}, {"name": "Corrupted Gauntlet"}, {"name": "Crazy Archaeologist"},
        {"name": "Dagannoth Prime"}, {"name": "Dagannoth Rex"}, {"name": "Dagannoth Supreme"},
        {"name": "Deranged Archaeologist"}, {"name": "Duke Sucellus"}, "Gauntlet",
        {"name": "General Graardor"}, {"name": "Giant Mole"}, {"name": "Grotesque Guardians"},
        {"name": "Hueycoatl"}, {"name": "K'ril Tsutsaroth"}, {"name": "Kalphite Queen"},
        {"name": "King Black Dragon"}, {"name": "Kraken"}, {"name": "Kree'arra"},
        {"name": "Leviathan"}, {"name": "Lunar Chests"}, {"name": "Mimic"},
        {"name": "Nex"}, {"name": "Nightmare"}, {"name": "Obor"}, "Phantom Muspah",
        {"name": "Phosani's Nightmare"}, "Royal Titans", "Sarachnis", "Scorpia",
        "Scurrius", "Skotizo", "Sol Heredit", "Spindel", "Tempoross",
        "Theatre of Blood", "Theatre of Blood (HM)", "Thermonuclear Smoke Devil",
        "Tombs of Amascut", "Tombs of Amascut (Expert Mode)", "Tzkal-Zuk", "TzTok-Jad",
        "Vardorvis", "Venenatis", "Vet'ion", "Vorkath", "Whisperer", "Wintertodt",
        "Yama", "Zalcano", "Zulrah"
    ]
}


# Map internal metric names to the corresponding WOM Metric enums
INTERNAL_NAME_TO_WOM_METRIC: Dict[str, wom.Metric] = {
    # Clue Scrolls
    "Beginner": wom.Metric.ClueScrollsBeginner,
    "Easy": wom.Metric.ClueScrollsEasy,
    "Medium": wom.Metric.ClueScrollsMedium,
    "Hard": wom.Metric.ClueScrollsHard,
    "Elite": wom.Metric.ClueScrollsElite,
    "Master": wom.Metric.ClueScrollsMaster,
    # Experience (Skills)
    "Attack": wom.Metric.Attack,
    "Strength": wom.Metric.Strength,
    "Defense": wom.Metric.Defence,
    "Ranged": wom.Metric.Ranged,
    "Prayer": wom.Metric.Prayer,
    "Magic": wom.Metric.Magic,
    "Runecrafting": wom.Metric.Runecrafting,
    "Construction": wom.Metric.Construction,
    "Hitpoints": wom.Metric.Hitpoints,
    "Agility": wom.Metric.Agility,
    "Herblore": wom.Metric.Herblore,
    "Thieving": wom.Metric.Thieving,
    "Crafting": wom.Metric.Crafting,
    "Fletching": wom.Metric.Fletching,
    "Slayer": wom.Metric.Slayer,
    "Hunter": wom.Metric.Hunter,
    "Mining": wom.Metric.Mining,
    "Smithing": wom.Metric.Smithing,
    "Fishing": wom.Metric.Fishing,
    "Cooking": wom.Metric.Cooking,
    "Firemaking": wom.Metric.Firemaking,
    "Woodcutting": wom.Metric.Woodcutting,
    "Farming": wom.Metric.Farming,
    # Killcounts (Bosses and some Activities)
    "Abyssal Sire": wom.Metric.AbyssalSire,
    "Alchemical Hydra": wom.Metric.AlchemicalHydra,
    "Amoxliatl": wom.Metric.Amoxliatl,
    "Araxxor": wom.Metric.Araxxor,
    "Artio": wom.Metric.Artio,
    "Barrows Chests": wom.Metric.BarrowsChests,
    "Bryophyta": wom.Metric.Bryophyta,
    "Callisto": wom.Metric.Callisto,
    "Calvar'ion": wom.Metric.Calvarion,
    "Cerberus": wom.Metric.Cerberus,
    "Chambers of Xeric": wom.Metric.ChambersOfXeric,
    "Chambers of Xeric (CM)": wom.Metric.ChambersOfXericChallenge,
    "Chaos Elemental": wom.Metric.ChaosElemental,
    "Chaos Fanatic": wom.Metric.ChaosFanatic,
    "Commander Zilyana": wom.Metric.CommanderZilyana,
    "Corporeal Beast": wom.Metric.CorporealBeast,
    "Corrupted Gauntlet": wom.Metric.TheCorruptedGauntlet,
    "Crazy Archaeologist": wom.Metric.CrazyArchaeologist,
    "Dagannoth Prime": wom.Metric.DagannothPrime,
    "Dagannoth Rex": wom.Metric.DagannothRex,
    "Dagannoth Supreme": wom.Metric.DagannothSupreme,
    "Deranged Archaeologist": wom.Metric.DerangedArchaeologist,
    "Duke Sucellus": wom.Metric.DukeSucellus,
    "Gauntlet": wom.Metric.TheGauntlet,
    "General Graardor": wom.Metric.GeneralGraardor,
    "Giant Mole": wom.Metric.GiantMole,
    "Grotesque Guardians": wom.Metric.GrotesqueGuardians,
    "Hueycoatl": wom.Metric.Hueycoatl,
    "K'ril Tsutsaroth": wom.Metric.KrilTsutsaroth,
    "Kalphite Queen": wom.Metric.KalphiteQueen,
    "King Black Dragon": wom.Metric.KingBlackDragon,
    "Kraken": wom.Metric.Kraken,
    "Kree'arra": wom.Metric.Kreearra,
    "Leviathan": wom.Metric.TheLeviathan,
    "Lunar Chests": wom.Metric.LunarChests,
    "Mimic": wom.Metric.Mimic,
    "Nex": wom.Metric.Nex,
    "Nightmare": wom.Metric.Nightmare,
    "Obor": wom.Metric.Obor,
    "Phantom Muspah": wom.Metric.PhantomMuspah,
    "Phosani's Nightmare": wom.Metric.PhosanisNightmare,
    "Royal Titans": wom.Metric.TheRoyalTitans,
    "Sarachnis": wom.Metric.Sarachnis,
    "Scorpia": wom.Metric.Scorpia,
    "Scurrius": wom.Metric.Scurrius,
    "Skotizo": wom.Metric.Skotizo,
    "Sol Heredit": wom.Metric.SolHeredit,
    "Spindel": wom.Metric.Spindel,
    "Tempoross": wom.Metric.Tempoross,
    "Theatre of Blood": wom.Metric.TheatreOfBlood,
    "Theatre of Blood (HM)": wom.Metric.TheatreOfBloodHard,
    "Thermonuclear Smoke Devil": wom.Metric.ThermonuclearSmokeDevil,
    "Tombs of Amascut": wom.Metric.TombsOfAmascut,
    "Tombs of Amascut (Expert Mode)": wom.Metric.TombsOfAmascutExpert,
    "Tzkal-Zuk": wom.Metric.TzKalZuk,
    "TzTok-Jad": wom.Metric.TzTokJad,
    "Vardorvis": wom.Metric.Vardorvis,
    "Venenatis": wom.Metric.Venenatis,
    "Vet'ion": wom.Metric.Vetion,
    "Vorkath": wom.Metric.Vorkath,
    "Whisperer": wom.Metric.TheWhisperer,
    "Wintertodt": wom.Metric.Wintertodt,
    "Yama": wom.Metric.Yama,
    "Zalcano": wom.Metric.Zalcano,
    "Zulrah": wom.Metric.Zulrah,
}

METRICS_TO_TRACK: List[wom.Metric] = list(INTERNAL_NAME_TO_WOM_METRIC.values())

# Inverse of INTERNAL_NAME_TO_WOM_METRIC
WOM_METRIC_NAME_TO_INTERNAL_NAME: Dict[str, str] = {
    metric.name: internal_name
    for internal_name, metric in INTERNAL_NAME_TO_WOM_METRIC.items()
}

# Define the actual header names found in the CSV
ACTUAL_HEADERS = ["Rank", "Username", "Team", "Start", "End", "Gained", "Last Updated"]

MILSTONES_ENDPOINT = "https://frenzy.ironfoundry.cc/milestones"

DELAY_BETWEEN_METRICS = 7

# Mapping for internal metric categories
METRIC_CATEGORIES: Dict[wom.Metric, Literal["cluescroll", "experience", "killcount"]] = {
    wom.Metric.ClueScrollsBeginner: "cluescroll",
    wom.Metric.ClueScrollsEasy: "cluescroll",
    wom.Metric.ClueScrollsMedium: "cluescroll",
    wom.Metric.ClueScrollsHard: "cluescroll",
    wom.Metric.ClueScrollsElite: "cluescroll",
    wom.Metric.ClueScrollsMaster: "cluescroll",
    # Skills (Experience)
    wom.Metric.Attack: "experience",
    wom.Metric.Strength: "experience",
    wom.Metric.Defence: "experience",
    wom.Metric.Ranged: "experience",
    wom.Metric.Prayer: "experience",
    wom.Metric.Magic: "experience",
    wom.Metric.Runecrafting: "experience",
    wom.Metric.Construction: "experience",
    wom.Metric.Hitpoints: "experience",
    wom.Metric.Agility: "experience",
    wom.Metric.Herblore: "experience",
    wom.Metric.Thieving: "experience",
    wom.Metric.Crafting: "experience",
    wom.Metric.Fletching: "experience",
    wom.Metric.Slayer: "experience",
    wom.Metric.Hunter: "experience",
    wom.Metric.Mining: "experience",
    wom.Metric.Smithing: "experience",
    wom.Metric.Fishing: "experience",
    wom.Metric.Cooking: "experience",
    wom.Metric.Firemaking: "experience",
    wom.Metric.Woodcutting: "experience",
    wom.Metric.Farming: "experience",
    # Killcounts (Bosses and some Activities)
    wom.Metric.AbyssalSire: "killcount",
    wom.Metric.AlchemicalHydra: "killcount",
    wom.Metric.Amoxliatl: "killcount",
    wom.Metric.Araxxor: "killcount",
    wom.Metric.Artio: "killcount",
    wom.Metric.BarrowsChests: "killcount",
    wom.Metric.Bryophyta: "killcount",
    wom.Metric.Callisto: "killcount",
    wom.Metric.Calvarion: "killcount",
    wom.Metric.Cerberus: "killcount",
    wom.Metric.ChambersOfXeric: "killcount",
    wom.Metric.ChambersOfXericChallenge: "killcount",
    wom.Metric.ChaosElemental: "killcount",
    wom.Metric.ChaosFanatic: "killcount",
    wom.Metric.CommanderZilyana: "killcount",
    wom.Metric.CorporealBeast: "killcount",
    wom.Metric.TheCorruptedGauntlet: "killcount",
    wom.Metric.CrazyArchaeologist: "killcount",
    wom.Metric.DagannothPrime: "killcount",
    wom.Metric.DagannothRex: "killcount",
    wom.Metric.DagannothSupreme: "killcount",
    wom.Metric.DerangedArchaeologist: "killcount",
    wom.Metric.DukeSucellus: "killcount",
    wom.Metric.TheGauntlet: "killcount",
    wom.Metric.GeneralGraardor: "killcount",
    wom.Metric.GiantMole: "killcount",
    wom.Metric.GrotesqueGuardians: "killcount",
    wom.Metric.Hueycoatl: "killcount",
    wom.Metric.KrilTsutsaroth: "killcount",
    wom.Metric.KalphiteQueen: "killcount",
    wom.Metric.KingBlackDragon: "killcount",
    wom.Metric.Kraken: "killcount",
    wom.Metric.Kreearra: "killcount",
    wom.Metric.TheLeviathan: "killcount",
    wom.Metric.LunarChests: "killcount",
    wom.Metric.Mimic: "killcount",
    wom.Metric.Nex: "killcount",
    wom.Metric.Nightmare: "killcount",
    wom.Metric.Obor: "killcount",
    wom.Metric.PhantomMuspah: "killcount",
    wom.Metric.PhosanisNightmare: "killcount",
    wom.Metric.TheRoyalTitans: "killcount",
    wom.Metric.Sarachnis: "killcount",
    wom.Metric.Scorpia: "killcount",
    wom.Metric.Scurrius: "killcount",
    wom.Metric.Skotizo: "killcount",
    wom.Metric.SolHeredit: "killcount",
    wom.Metric.Spindel: "killcount",
    wom.Metric.Tempoross: "killcount",
    wom.Metric.TheatreOfBlood: "killcount",
    wom.Metric.TheatreOfBloodHard: "killcount",
    wom.Metric.ThermonuclearSmokeDevil: "killcount",
    wom.Metric.TombsOfAmascut: "killcount",
    wom.Metric.TombsOfAmascutExpert: "killcount",
    wom.Metric.TzKalZuk: "killcount",
    wom.Metric.TzTokJad: "killcount",
    wom.Metric.Vardorvis: "killcount",
    wom.Metric.Venenatis: "killcount",
    wom.Metric.Vetion: "killcount",
    wom.Metric.Vorkath: "killcount",
    wom.Metric.TheWhisperer: "killcount",
    wom.Metric.Wintertodt: "killcount",
    wom.Metric.Yama: "killcount",
    wom.Metric.Zalcano: "killcount",
    wom.Metric.Zulrah: "killcount",
}


async def update_milestones_for_metric(metric: wom.Metric, http_client: httpx.AsyncClient):
    """Fetches data for a single metric and sends it to the milestones endpoint."""
    wom_metric_name = metric.name # Get the string name from WOM metric

    # Map the WOM metric name to internal database name
    internal_metric_name = WOM_METRIC_NAME_TO_INTERNAL_NAME.get(wom_metric_name)
    if internal_metric_name is None:
        logger.warning(f"Internal mapping missing for WOM metric name: {wom_metric_name}. Skipping.")
        return

    # Determine the category for this metric (cluescroll, experience, killcount)
    metric_category = METRIC_CATEGORIES.get(metric)
    if metric_category is None:
        logger.warning(f"Metric category missing for WOM metric: {wom_metric_name}. Skipping.")
        return


    logger.info(f"Fetching data for {wom_metric_name} (Category: {metric_category}, Mapped to: {internal_metric_name})...")

    data_for_milestones: Dict[str, Dict[str, Dict[str, int]]] = {
        "ironfoundry": {metric_category: {internal_metric_name: 0}},
        "ironclad": {metric_category: {internal_metric_name: 0}}
    }

    COMPETITION_ID = 90513

    try:
        csv_data = await client.competitions.get_details_csv(COMPETITION_ID, metric=metric.value) # type: ignore

        if not csv_data:
             logger.info(f"No data returned for {wom_metric_name}.")
             return data_for_milestones

        csv_file = io.StringIO(csv_data.unwrap())

        df = pd.read_csv(
            csv_file,
            header=0,
            names=ACTUAL_HEADERS,
            dtype={'Gained': int, 'Start': int, 'End': int}
        )

        if not df.empty:
             # Filter for players in the desired clans
             filtered_df = df[df['Team'].isin(['Iron Foundry', 'Ironclad'])]

             if not filtered_df.empty:
                # Aggregate the 'Gained' column by 'Team'
                clan_gains = filtered_df.groupby('Team')['Gained'].sum()

                # Update the data_for_milestones dictionary
                for clan_name_csv, total_gained in clan_gains.items():
                    # Map CSV clan names to dictionary keys
                    if clan_name_csv == "Iron Foundry":
                        data_for_milestones["ironfoundry"][metric_category][internal_metric_name] = int(total_gained)
                    elif clan_name_csv == "Ironclad":
                        data_for_milestones["ironclad"][metric_category][internal_metric_name] = int(total_gained)


        logger.info(f"Aggregated data for {internal_metric_name}: {data_for_milestones}")

        async with httpx.AsyncClient() as inner_http_client:
            try:
                logger.info(f"Sending data for {internal_metric_name} to {MILSTONES_ENDPOINT}")
                response = await inner_http_client.post(MILSTONES_ENDPOINT, json=data_for_milestones)
                response.raise_for_status()
                logger.info(f"Successfully sent data for {internal_metric_name}. Status: {response.status_code}")
            except httpx.RequestError as e:
                 logger.error(f"An error occurred while requesting {e.request.url} for {internal_metric_name}: {e}")
            except httpx.HTTPStatusError as e:
                 logger.error(f"HTTP error {e.response.status_code} when sending data for {internal_metric_name}: {e.response.text}")
            except Exception as e:
                 logger.error(f"An unexpected error occurred while sending data for {internal_metric_name}: {e}")


    except Exception as e:
        logger.error(f"Error fetching or processing data for {wom_metric_name}: {e}", exc_info=True)

    return data_for_milestones


async def milestone_update():
    """Periodically updates milestones for each metric with a delay."""
    try:
        await client.start()

        async with httpx.AsyncClient() as http_client:
            for metric in METRICS_TO_TRACK:
                await update_milestones_for_metric(metric, http_client)
                logger.info(f"Waiting {DELAY_BETWEEN_METRICS} seconds before fetching next metric.")
                await asyncio.sleep(DELAY_BETWEEN_METRICS)

            
                logger.info("Finished a full cycle of metric milestone updates. Starting next cycle.")
    finally:
        await client.close()

