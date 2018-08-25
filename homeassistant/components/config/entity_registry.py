"""HTTP views to interact with the entity registry."""
import voluptuous as vol

from homeassistant.core import callback
from homeassistant.helpers.entity_registry import async_get_registry
from homeassistant.components import websocket_api
from homeassistant.helpers import config_validation as cv

DEPENDENCIES = ['websocket_api']

WS_TYPE_GET = 'config/entity_registry/get'
SCHEMA_WS_GET = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required('type'): WS_TYPE_GET,
    vol.Required('entity_id'): cv.entity_id
})

WS_TYPE_UPDATE = 'config/entity_registry/update'
SCHEMA_WS_UPDATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required('type'): WS_TYPE_UPDATE,
    vol.Required('entity_id'): cv.entity_id,
    # If passed in, we update value. Passing None will remove old value.
    vol.Optional('name'): vol.Any(str, None),
    vol.Optional('new_entity_id'): str,
})


async def async_setup(hass):
    """Enable the Entity Registry views."""
    hass.components.websocket_api.async_register_command(
        WS_TYPE_GET, websocket_get_entity,
        SCHEMA_WS_GET
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_UPDATE, websocket_update_entity,
        SCHEMA_WS_UPDATE
    )
    return True


@callback
def websocket_get_entity(hass, connection, msg):
    """Handle get entity registry entry command.

    Async friendly.
    """
    async def retrieve_entity():
        """Get entity from registry."""
        registry = await async_get_registry(hass)
        entry = registry.entities.get(msg['entity_id'])

        if entry is None:
            connection.send_message_outside(websocket_api.error_message(
                msg['id'], websocket_api.ERR_NOT_FOUND, 'Entity not found'))
            return

        connection.send_message_outside(websocket_api.result_message(
            msg['id'], _entry_dict(entry)
        ))

    hass.async_add_job(retrieve_entity())


@callback
def websocket_update_entity(hass, connection, msg):
    """Handle get camera thumbnail websocket command.

    Async friendly.
    """
    async def update_entity():
        """Get entity from registry."""
        registry = await async_get_registry(hass)

        if msg['entity_id'] not in registry.entities:
            connection.send_message_outside(websocket_api.error_message(
                msg['id'], websocket_api.ERR_NOT_FOUND, 'Entity not found'))
            return

        changes = {}

        if 'name' in msg:
            changes['name'] = msg['name']

        if 'new_entity_id' in msg:
            changes['new_entity_id'] = msg['new_entity_id']

        try:
            if changes:
                entry = registry.async_update_entity(
                    msg['entity_id'], **changes)
        except ValueError as err:
            connection.send_message_outside(websocket_api.error_message(
                msg['id'], 'invalid_info', str(err)
            ))
        else:
            connection.send_message_outside(websocket_api.result_message(
                msg['id'], _entry_dict(entry)
            ))

    hass.async_create_task(update_entity())


@callback
def _entry_dict(entry):
    """Convert entry to API format."""
    return {
        'entity_id': entry.entity_id,
        'name': entry.name
    }
