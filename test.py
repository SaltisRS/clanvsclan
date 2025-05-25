from upyloadthing import AsyncUTApi, UTApiOptions
import asyncio
UPLOADTHING_TOKEN='eyJhcGlLZXkiOiJza19saXZlX2UwZjI5YWIwYWMyMjZlZTQ2MzI4MjBlMjlkNzU2Y2Q4MmNkYTJlMTY1YjJjNjdmYTI2NDIzNDBkOGRmYmY2NTciLCJhcHBJZCI6Inc0ZzMxNzU5M3oiLCJyZWdpb25zIjpbInNlYTEiXX0='
api = AsyncUTApi(UTApiOptions(token=UPLOADTHING_TOKEN))

async def upload():
    with open("test.png", "rb") as f:
        result = await api.upload_files(f)
        print(f"file uploaded: {result.__repr__()}")
        
        
        
async def main():
    await upload()
    


if __name__ == "__main__":
    asyncio.run(main())