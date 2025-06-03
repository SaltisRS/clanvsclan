import wom
import os
import asyncio
from loguru import logger
from dotenv import load_dotenv




wom_client = wom.Client(api_key=os.getenv("WOM_API"), user_agent="@saltis.")


async def get_wom_metrics():
    competition_id = 90513
    metrics = [wom.Metric.Overall, wom.Metric.Ehb, wom.Metric.Ehp]
    data = {}
    
    try:
        await wom_client.start()
    except RuntimeError as e:
        logger.info("Client was already started.", e)
        
    for metric in metrics:
        response: wom.Result = await wom_client.competitions.get_details_csv(id=competition_id, metric=metric.value)
        if response.is_ok:
            result = response.unwrap()
            logger.info(result)
        await asyncio.sleep(10)
        
if __name__ == "__main__":
    asyncio.run(get_wom_metrics())