from pathlib import Path

def build_bronze_path(source_key: str, window: str, market: str) -> str:
   year = window[0:4]
   filename = Path(source_key).name
   destination = Path("/data/bronze") / market / year / filename
   
   return str(destination)
   