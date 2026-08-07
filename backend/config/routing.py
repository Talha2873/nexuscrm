"""Aggregated WebSocket URL routing for the whole project.

Consumers are contributed by the apps that own them; each app exports a
``websocket_urlpatterns`` list which is spread into the aggregate below.
"""

websocket_urlpatterns: list = []
