''' Simple HTTP interface to int'''

import json
import asyncio
import logging

from aiohttp import web

from .constants import CLIENT_START_PORT

async def handle_default(logic, _request):
    ''' Handle a request to the main page '''

    entries = await logic.get_all()
    text = "<html><head>\n"
    text += "<title>MiniKV</title>\n"
    text += "</head><body>\n"

    if len(entries) == 0:
        text += "Found no entries in the database."
    else:
        text += "Found the following entries: <br />\n"
        text += "<ul>\n"
        for key, value in entries:
            text += f"<li>{key}: {value}</li>\n"
        text += "</ul>\n"
    text += "</html>"

    return web.Response(text=text, content_type="text/html")

async def handle_get(logic, request):
    ''' Fetches an entry from the database (if it exists) '''

    key = request.query["key"]
    value = await logic.get(key)
    return web.Response(text=json.dumps({"value": value}),
            content_type="application/json")

async def handle_put(logic, request):
    ''' Stores a new key/value-pair in the database '''

    key = request.query["key"]
    value = (await request.json())["value"]

    await logic.put(key, value)

    # Returns an empty OK
    return web.Response(text=json.dumps({}),
            content_type="application/json")

async def serve(logic, index: int):
    ''' Main function that runs the web server '''

    app = web.Application()
    app.add_routes([
        web.get('/', lambda r: handle_default(logic, r)),
        web.get('/get', lambda r: handle_get(logic, r)),
        web.post('/put', lambda r: handle_put(logic, r))])


    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', CLIENT_START_PORT+index)

    await site.start()
    print("Waiting for Ctrl+C")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Got Ctrl+C")

    await runner.cleanup()
