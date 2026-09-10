import argparse
import asyncio
import logging

import uvicorn

from bazaar.collector.service import Collector
from bazaar.config import Settings
from bazaar.database import make_engine, session_factory


def main() -> None:
    parser = argparse.ArgumentParser(description="Bazaar collector and market API")
    parser.add_argument("mode", choices=["serve", "collect"], nargs="?", default="serve")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings()
    if args.mode == "collect":
        engine = make_engine(settings.database_url)
        try:
            asyncio.run(Collector(session_factory(engine), settings).run())
        except KeyboardInterrupt:
            pass
        finally:
            engine.dispose()
    else:
        uvicorn.run("bazaar.api.app:create_app", factory=True, host=settings.host, port=settings.port)
