from fastapi import (
    Request,
    Response,
    HTTPException,
    status
)

import httpx
from httpx import AsyncClient

from typing import Any


class GatewayService:
    http_client: AsyncClient
    services: dict[str, str]

    def __init__(
        self,
        http_client: AsyncClient,
        services: dict[str, str]
    ) -> None:
        self.http_client = http_client
        self.services = services

    async def forward_request(
        self,
        request: Request,
        service: str,
        path: str,
        query_params: dict[str, Any] | None = None
    ) -> Response:
        if service not in self.services:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Service "{service} not found"'
            )
        
        base_url = self.services[service]
        target_url = f'{base_url}/{path}'

        if query_params:
            target_url += '?'
            params_list = []
            for param in query_params:
                params_list.append(f'{param}={query_params[param]}')
            target_url += '&'.join(params_list)
        
        body = await request.body()
        headers = dict(request.headers)
        headers.pop('host', None)

        try:
            response = await self.http_client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                timeout=30.0,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail='Service timeout'
            )
        
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f'Service error: {str(e)}'
            )
