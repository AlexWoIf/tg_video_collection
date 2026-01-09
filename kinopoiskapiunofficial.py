import httpx


class KinopoiskApi():
    def __init__(self, api_key):
        self.headers = {'X-API-KEY': api_key,
                        'Content-Type': 'application/json', }

    async def get_by_id(self, kp_id):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://kinopoiskapiunofficial.tech/api/v2.2/films/{kp_id}',
                headers=self.headers
            )
        response.raise_for_status()
        return response.json()

    async def get_seasons_info(self, kp_id):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://kinopoiskapiunofficial.tech/api/v2.2/films/{kp_id}/seasons',  # noqa: E501
                headers=self.headers
            )
        response.raise_for_status()
        return response.json()

    async def get_similar_films(self, kp_id):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://kinopoiskapiunofficial.tech/api/v2.2/films/{kp_id}/similars',  # noqa: E501
                headers=self.headers
            )
        response.raise_for_status()
        return response.json()
