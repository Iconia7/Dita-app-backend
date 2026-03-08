import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.users.models import User

from .models import GroupMessage, StudyGroup


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling real-time chat functionality within study groups, allowing users to connect, send messages, and receive updates in real time."""

    async def connect(self):
        """Handle WebSocket connection by extracting the group ID from the URL, adding the channel to the appropriate group for message broadcasting, and accepting the connection."""
        self.group_id = self.scope["url_route"]["kwargs"]["group_id"].strip("/")
        self.room_group_name = f"chat_{self.group_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection by removing the channel from the group to stop receiving messages."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages by parsing the JSON data, saving the message to the database, and broadcasting it to all connected clients in the group.
        The message data includes the content of the message and the username of the sender.
        """
        data = json.loads(text_data)
        message = data["message"]
        username = data["username"]
        await self.save_message(username, self.group_id, message)
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message, "username": username}
        )

    async def chat_message(self, event):
        """Handle the chat_message event by sending the message data to the WebSocket client in JSON format, allowing real-time updates of messages in the chat interface."""
        await self.send(text_data=json.dumps({"message": event["message"], "username": event["username"]}))

    @sync_to_async
    def save_message(self, username, group_id, message):
        """Synchronous helper method to save a chat message to the database, associating it with the correct user and study group based on the provided username and group ID."""
        user = User.objects.get(username=username)
        group = StudyGroup.objects.get(id=group_id)
        GroupMessage.objects.create(user=user, group=group, content=message)
